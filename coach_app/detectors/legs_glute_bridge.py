from core.base_exercise import BaseExercise


class GluteBridgeDetector(BaseExercise):
    """Lying on the back with knees bent, driving the hips up into a
    bridge. Tracks hip extension (shoulder-hip-knee angle): hips down =
    angle stays bent, hips lifted = the line straightens out.
    """
    RESTING_THRESHOLD = 140
    BRIDGED_THRESHOLD = 165
    MIN_VISIBILITY = 0.6

    LEFT_SHOULDER = 11
    LEFT_HIP = 23
    LEFT_KNEE = 25
    RIGHT_SHOULDER = 12
    RIGHT_HIP = 24
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

        hip_angle = self.calculate_angle(
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
            if hip_angle < self.RESTING_THRESHOLD:
                self.stage = "resting"

            if hip_angle > self.BRIDGED_THRESHOLD and self.stage == "resting":
                self.stage = "bridged"
                self.reps += 1

        bridge_status = "BRIDGED — SQUEEZE" if self.stage == "bridged" else "HIPS DOWN"

        return {
            "reps": self.reps,
            "hip_angle": int(hip_angle),
            "bridge_status": bridge_status,
        }
