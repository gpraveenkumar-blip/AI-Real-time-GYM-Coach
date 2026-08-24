from core.base_exercise import BaseExercise


class SupermanDetector(BaseExercise):
    """Lying prone, lifting chest and legs off the floor.
    NOTE: floor exercises are hard to see with a laptop-style front-facing
    webcam. This works best with the camera positioned to the side, roughly
    level with the floor, so the torso's extension angle stays visible.
    """
    LIFTED_THRESHOLD = 155   # torso curls upward -> shoulder-hip-knee angle shrinks
    RESTING_THRESHOLD = 170  # flat on the floor -> angle opens back up
    MIN_VISIBILITY = 0.6

    LEFT_SHOULDER = 11
    RIGHT_SHOULDER = 12
    LEFT_HIP = 23
    RIGHT_HIP = 24
    LEFT_KNEE = 25
    RIGHT_KNEE = 26

    def __init__(self):
        super().__init__()

    def reset(self) -> None:
        self.reps = 0
        self.stage = None

    def process(self, landmarks) -> dict:
        left_vis = landmarks[self.LEFT_HIP].visibility
        right_vis = landmarks[self.RIGHT_HIP].visibility

        if left_vis >= right_vis:
            shoulder_idx, hip_idx, knee_idx = self.LEFT_SHOULDER, self.LEFT_HIP, self.LEFT_KNEE
        else:
            shoulder_idx, hip_idx, knee_idx = self.RIGHT_SHOULDER, self.RIGHT_HIP, self.RIGHT_KNEE

        extension_angle = self.calculate_angle(
            self.get_point(landmarks, shoulder_idx),
            self.get_point(landmarks, hip_idx),
            self.get_point(landmarks, knee_idx),
        )

        key_landmarks_visible = (
            landmarks[shoulder_idx].visibility > self.MIN_VISIBILITY
            and landmarks[hip_idx].visibility > self.MIN_VISIBILITY
            and landmarks[knee_idx].visibility > self.MIN_VISIBILITY
        )

        if key_landmarks_visible:
            if extension_angle < self.LIFTED_THRESHOLD:
                self.stage = "lifted"

            if extension_angle > self.RESTING_THRESHOLD and self.stage == "lifted":
                self.stage = "resting"
                self.reps += 1

        lift_status = "LIFTED — HOLD" if self.stage == "lifted" else "RESTING"

        return {
            "reps": self.reps,
            "extension_angle": int(extension_angle),
            "lift_status": lift_status,
        }
