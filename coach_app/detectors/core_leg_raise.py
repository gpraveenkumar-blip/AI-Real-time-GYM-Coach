from core.base_exercise import BaseExercise


class LegRaiseDetector(BaseExercise):
    """Lying on the back, raising straight legs from the floor up toward
    vertical. Tracks hip flexion (shoulder-hip-ankle angle): legs down =
    angle near straight, legs raised = angle shrinks as the hip flexes.
    """
    RAISED_THRESHOLD = 100
    LOWERED_THRESHOLD = 155
    MIN_VISIBILITY = 0.6

    LEFT_SHOULDER = 11
    LEFT_HIP = 23
    LEFT_ANKLE = 27
    RIGHT_SHOULDER = 12
    RIGHT_HIP = 24
    RIGHT_ANKLE = 28

    def __init__(self):
        super().__init__()

    def reset(self) -> None:
        self.reps = 0
        self.stage = None

    def process(self, landmarks) -> dict:
        left_vis = landmarks[self.LEFT_HIP].visibility
        right_vis = landmarks[self.RIGHT_HIP].visibility

        if left_vis >= right_vis:
            shoulder_idx, hip_idx, ankle_idx = self.LEFT_SHOULDER, self.LEFT_HIP, self.LEFT_ANKLE
        else:
            shoulder_idx, hip_idx, ankle_idx = self.RIGHT_SHOULDER, self.RIGHT_HIP, self.RIGHT_ANKLE

        hip_angle = self.calculate_angle(
            self.get_point(landmarks, shoulder_idx),
            self.get_point(landmarks, hip_idx),
            self.get_point(landmarks, ankle_idx),
        )

        key_landmarks_visible = (
            landmarks[shoulder_idx].visibility > self.MIN_VISIBILITY
            and landmarks[hip_idx].visibility > self.MIN_VISIBILITY
            and landmarks[ankle_idx].visibility > self.MIN_VISIBILITY
        )

        if key_landmarks_visible:
            if hip_angle < self.RAISED_THRESHOLD:
                self.stage = "raised"

            if hip_angle > self.LOWERED_THRESHOLD and self.stage == "raised":
                self.stage = "lowered"
                self.reps += 1

        leg_status = "LEGS RAISED" if self.stage == "raised" else "LOWERING"

        return {
            "reps": self.reps,
            "hip_angle": int(hip_angle),
            "leg_status": leg_status,
        }
