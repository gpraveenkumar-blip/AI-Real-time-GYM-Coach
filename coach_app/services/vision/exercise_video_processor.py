"""Real-time MediaPipe video processor with defensive runtime handling."""
from __future__ import annotations

import os
import threading
import time
from pathlib import Path

import av
import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from streamlit_webrtc import VideoProcessorBase

from detectors.back_backpack_row import BackpackRowDetector
from detectors.back_prone_ytw_raise import ProneYTWRaiseDetector
from detectors.back_reverse_snow_angel import ReverseSnowAngelDetector
from detectors.back_superman import SupermanDetector
from detectors.biceps_curl import BicepsCurlDetector
from detectors.biceps_isometric_hold import IsometricBicepsHoldDetector
from detectors.core_bicycle_crunch import BicycleCrunchDetector
from detectors.core_leg_raise import LegRaiseDetector
from detectors.core_mountain_climber import MountainClimberDetector
from detectors.core_plank import PlankDetector
from detectors.legs_bulgarian_split_squat import BulgarianSplitSquatDetector
from detectors.legs_glute_bridge import GluteBridgeDetector
from detectors.lunges import LungesDetector
from detectors.pushup import PushUpDetector
from detectors.shoulder_press import ShoulderPressDetector
from detectors.shoulders_arm_circle import ArmCircleDetector
from detectors.shoulders_pike_pushup import PikePushUpDetector
from detectors.shoulders_shoulder_tap import ShoulderTapDetector
from detectors.shoulders_wall_handstand_hold import WallHandstandHoldDetector
from detectors.squat import SquatDetector
from detectors.triceps_chair_dip import ChairDipDetector
from detectors.triceps_overhead_extension import OverheadExtensionDetector
from services.config.workout_config import POSE_CONNECTIONS


class VideoProcessorClass(VideoProcessorBase):
    def __init__(self):
        self._lock = threading.Lock()
        self._latest_metrics = None
        self._exercise_type = "Squats"
        self._last_timestamp_ms = 0
        self._landmarker = self._create_landmarker()
        self._detectors = self._build_detectors()

    @staticmethod
    def _model_path() -> Path:
        configured = os.getenv("AI_GYM_POSE_MODEL")
        if configured:
            return Path(configured).expanduser().resolve()
        # This file lives at coach_app/services/vision/, so parents[2] = coach_app.
        return Path(__file__).resolve().parents[2] / "ml_models" / "pose_landmarker_full.task"

    @classmethod
    def _create_landmarker(cls):
        model_path = cls._model_path()
        if not model_path.is_file():
            raise FileNotFoundError(
                f"MediaPipe pose model not found: {model_path}. "
                "Set AI_GYM_POSE_MODEL or place pose_landmarker_full.task in coach_app/ml_models/."
            )

        options = vision.PoseLandmarkerOptions(
            base_options=python.BaseOptions(model_asset_path=str(model_path)),
            running_mode=vision.RunningMode.VIDEO,
            min_pose_detection_confidence=0.7,
            min_pose_presence_confidence=0.7,
            min_tracking_confidence=0.7,
            output_segmentation_masks=False,
        )
        try:
            return vision.PoseLandmarker.create_from_options(options)
        except Exception as exc:
            raise RuntimeError(
                "MediaPipe PoseLandmarker failed to initialize. "
                "Verify the model asset and MediaPipe/runtime compatibility."
            ) from exc

    @staticmethod
    def _build_detectors():
        return {
            "Squats": SquatDetector(),
            "Push-ups": PushUpDetector(),
            "Biceps Curls (Dumbbell)": BicepsCurlDetector(),
            "Shoulder Press": ShoulderPressDetector(),
            "Lunges": LungesDetector(),
            "Standard Push-Ups": PushUpDetector(),
            "Wide Push-Ups": PushUpDetector(),
            "Incline Push-Ups": PushUpDetector(),
            "Decline Push-Ups": PushUpDetector(),
            "Superman": SupermanDetector(),
            "Reverse Snow Angels": ReverseSnowAngelDetector(),
            "Prone Y-T-W Raises": ProneYTWRaiseDetector(),
            "Backpack Rows": BackpackRowDetector(),
            "Pike Push-Ups": PikePushUpDetector(),
            "Shoulder Taps": ShoulderTapDetector(),
            "Wall Handstand Hold": WallHandstandHoldDetector(),
            "Arm Circles": ArmCircleDetector(),
            "Backpack Curls": BicepsCurlDetector(),
            "Towel Curls": BicepsCurlDetector(),
            "Isometric Biceps Hold": IsometricBicepsHoldDetector(),
            "Resistance-Band Curls": BicepsCurlDetector(),
            "Diamond Push-Ups": PushUpDetector(),
            "Chair Dips": ChairDipDetector(),
            "Close-Grip Push-Ups": PushUpDetector(),
            "Overhead Backpack Extension": OverheadExtensionDetector(),
            "Plank": PlankDetector(),
            "Bicycle Crunches": BicycleCrunchDetector(),
            "Leg Raises": LegRaiseDetector(),
            "Mountain Climbers": MountainClimberDetector(),
            "Bodyweight Squats": SquatDetector(),
            "Reverse Lunges": LungesDetector(),
            "Bulgarian Split Squats": BulgarianSplitSquatDetector(),
            "Glute Bridges": GluteBridgeDetector(),
        }

    def set_latest_metrics(self, metrics):
        with self._lock:
            self._latest_metrics = dict(metrics)

    def get_latest_metrics(self):
        with self._lock:
            return None if self._latest_metrics is None else dict(self._latest_metrics)

    def set_exercise(self, exercise_type):
        with self._lock:
            if exercise_type in self._detectors:
                self._exercise_type = exercise_type

    def get_exercise(self):
        with self._lock:
            return self._exercise_type

    @staticmethod
    def _draw_skeleton(img, landmarks):
        h, w = img.shape[:2]
        for start_idx, end_idx in POSE_CONNECTIONS:
            if start_idx >= len(landmarks) or end_idx >= len(landmarks):
                continue
            p1, p2 = landmarks[start_idx], landmarks[end_idx]
            if p1.visibility > 0.7 and p2.visibility > 0.7:
                cv2.line(
                    img,
                    (int(p1.x * w), int(p1.y * h)),
                    (int(p2.x * w), int(p2.y * h)),
                    (0, 255, 0),
                    3,
                )
        for lm in landmarks:
            if lm.visibility > 0.7:
                cv2.circle(img, (int(lm.x * w), int(lm.y * h)), 4, (255, 0, 0), -1)

    @staticmethod
    def _draw_no_pose_warnings(img):
        cv2.putText(img, "NO POSE DETECTED", (30, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2, cv2.LINE_AA)
        cv2.putText(img, "PLEASE FACE THE CAMERA", (30, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2, cv2.LINE_AA)

    @staticmethod
    def _draw_status(img, text):
        h, _ = img.shape[:2]
        cv2.putText(img, str(text)[:120], (20, h - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

    def _draw_overlays(self, img, metrics, ex_type):
        if ex_type == "Squats":
            self._draw_status(img, f"DEPTH: {metrics.get('depth_status', 'N/A')}")
        elif ex_type == "Push-ups":
            self._draw_status(img, f"BODY: {metrics.get('body_alignment', 'N/A')} | HIP: {metrics.get('hip_status', 'N/A')}")
        elif ex_type == "Biceps Curls (Dumbbell)":
            self._draw_status(img, f"SWING: {metrics.get('swing_status', 'N/A')}")
        elif ex_type == "Shoulder Press":
            self._draw_status(img, f"EXT: {metrics.get('extension_status', 'N/A')} | BACK: {metrics.get('back_arch_status', 'N/A')}")
        elif ex_type == "Lunges":
            self._draw_status(img, f"BALANCE: {metrics.get('balance_status', 'N/A')}")
        else:
            for key, value in metrics.items():
                if key not in {"reps", "pose_detected"} and isinstance(value, str):
                    self._draw_status(img, value)
                    break

    def _next_timestamp_ms(self):
        # MediaPipe VIDEO mode requires monotonically increasing timestamps.
        now = int(time.monotonic() * 1000)
        with self._lock:
            self._last_timestamp_ms = max(now, self._last_timestamp_ms + 1)
            return self._last_timestamp_ms

    def recv(self, frame):
        image = cv2.flip(frame.to_ndarray(format="bgr24"), 1)

        try:
            rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_image)
            result = self._landmarker.detect_for_video(mp_image, self._next_timestamp_ms())

            if result.pose_landmarks:
                landmarks = result.pose_landmarks[0]
                self._draw_skeleton(image, landmarks)
                ex_type = self.get_exercise()
                detector = self._detectors.get(ex_type)

                if detector:
                    metrics = detector.process(landmarks)
                    metrics = dict(metrics or {})
                    metrics["pose_detected"] = True
                    self._draw_overlays(image, metrics, ex_type)
                    self.set_latest_metrics(metrics)
            else:
                self._draw_no_pose_warnings(image)
                self.set_latest_metrics({"pose_detected": False, "reps": self.get_latest_metrics().get("reps", 0) if self.get_latest_metrics() else 0})
        except Exception:
            # Never terminate the WebRTC worker because a single frame failed.
            # Do not expose native/provider exception details to the browser.
            self._draw_status(image, "CAMERA PROCESSING TEMPORARILY UNAVAILABLE")

        return av.VideoFrame.from_ndarray(np.asarray(image, dtype=np.uint8), format="bgr24")
