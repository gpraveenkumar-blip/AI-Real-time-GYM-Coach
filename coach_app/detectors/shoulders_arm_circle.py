import math
from core.base_exercise import BaseExercise


class ArmCircleDetector(BaseExercise):
    """Standing, circling a straight arm around the shoulder. Tracks the
    wrist's angular position around the shoulder frame-to-frame and
    accumulates rotation; a full 360° sweep counts as 1 rep.
    """
    MIN_VISIBILITY = 0.6

    LEFT_SHOULDER = 11
    LEFT_WRIST = 15
    RIGHT_SHOULDER = 12
    RIGHT_WRIST = 16

    def __init__(self):
        super().__init__()
        self._last_angle = None
        self._accumulated_degrees = 0.0

    def reset(self) -> None:
        self.reps = 0
        self.stage = None
        self._last_angle = None
        self._accumulated_degrees = 0.0

    def process(self, landmarks) -> dict:
        left_vis = landmarks[self.LEFT_WRIST].visibility
        right_vis = landmarks[self.RIGHT_WRIST].visibility

        if left_vis >= right_vis:
            shoulder_idx, wrist_idx = self.LEFT_SHOULDER, self.LEFT_WRIST
        else:
            shoulder_idx, wrist_idx = self.RIGHT_SHOULDER, self.RIGHT_WRIST

        key_landmarks_visible = (
            landmarks[shoulder_idx].visibility > self.MIN_VISIBILITY
            and landmarks[wrist_idx].visibility > self.MIN_VISIBILITY
        )

        shoulder = self.get_point(landmarks, shoulder_idx)
        wrist = self.get_point(landmarks, wrist_idx)

        angle = math.degrees(math.atan2(wrist[1] - shoulder[1], wrist[0] - shoulder[0]))

        if key_landmarks_visible:
            if self._last_angle is not None:
                delta = angle - self._last_angle

                # Normalize the jump to [-180, 180] so crossing the +/-180
                # boundary doesn't register as a huge fake jump.
                while delta > 180:
                    delta -= 360
                while delta < -180:
                    delta += 360

                self._accumulated_degrees += abs(delta)

                if self._accumulated_degrees >= 360:
                    self.reps += 1
                    self._accumulated_degrees -= 360

            self._last_angle = angle
            self.stage = "circling"
        else:
            self.stage = None

        return {
            "reps": self.reps,
            "circle_progress_deg": int(self._accumulated_degrees),
        }
