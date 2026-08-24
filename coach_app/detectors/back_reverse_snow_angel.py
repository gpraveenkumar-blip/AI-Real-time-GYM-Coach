from core.base_exercise import BaseExercise


class ReverseSnowAngelDetector(BaseExercise):
    """Lying prone, sweeping straight arms from the hips up overhead (like
    making a snow angel face-down). Tracks the arm's angle relative to the
    torso line at the shoulder. Best seen from a side-on camera angle.
    """
    ARMS_DOWN_THRESHOLD = 40    # arms near the hips
    ARMS_UP_THRESHOLD = 150     # arms swept overhead
    MIN_VISIBILITY = 0.6

    LEFT_SHOULDER = 11
    LEFT_WRIST = 15
    LEFT_HIP = 23
    RIGHT_SHOULDER = 12
    RIGHT_WRIST = 16
    RIGHT_HIP = 24

    def __init__(self):
        super().__init__()

    def reset(self) -> None:
        self.reps = 0
        self.stage = None

    def process(self, landmarks) -> dict:
        left_vis = landmarks[self.LEFT_WRIST].visibility
        right_vis = landmarks[self.RIGHT_WRIST].visibility

        if left_vis >= right_vis:
            shoulder_idx, wrist_idx, hip_idx = self.LEFT_SHOULDER, self.LEFT_WRIST, self.LEFT_HIP
        else:
            shoulder_idx, wrist_idx, hip_idx = self.RIGHT_SHOULDER, self.RIGHT_WRIST, self.RIGHT_HIP

        sweep_angle = self.calculate_angle(
            self.get_point(landmarks, hip_idx),
            self.get_point(landmarks, shoulder_idx),
            self.get_point(landmarks, wrist_idx),
        )

        key_landmarks_visible = (
            landmarks[shoulder_idx].visibility > self.MIN_VISIBILITY
            and landmarks[wrist_idx].visibility > self.MIN_VISIBILITY
            and landmarks[hip_idx].visibility > self.MIN_VISIBILITY
        )

        if key_landmarks_visible:
            if sweep_angle < self.ARMS_DOWN_THRESHOLD:
                self.stage = "down"

            if sweep_angle > self.ARMS_UP_THRESHOLD and self.stage == "down":
                self.stage = "up"
                self.reps += 1

        sweep_status = "ARMS OVERHEAD" if self.stage == "up" else "ARMS AT SIDES"

        return {
            "reps": self.reps,
            "sweep_angle": int(sweep_angle),
            "sweep_status": sweep_status,
        }
