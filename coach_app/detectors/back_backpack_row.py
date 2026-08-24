from core.base_exercise import BaseExercise


class BackpackRowDetector(BaseExercise):
    """Bent-over row using a loaded backpack (or any household weight) as
    resistance. Tracks elbow flexion (arm extended -> pulled back) the same
    way a dumbbell row would be tracked, plus a torso-hinge check so the
    back doesn't round or stand up mid-set.
    """
    EXTENDED_THRESHOLD = 160
    ROWED_THRESHOLD = 80
    MIN_VISIBILITY = 0.6
    HINGE_MIN_ANGLE = 45   # torso should stay hinged forward, not upright

    LEFT_SHOULDER = 11
    LEFT_ELBOW = 13
    LEFT_WRIST = 15
    LEFT_HIP = 23
    LEFT_KNEE = 25
    RIGHT_SHOULDER = 12
    RIGHT_ELBOW = 14
    RIGHT_WRIST = 16
    RIGHT_HIP = 24
    RIGHT_KNEE = 26

    def __init__(self):
        super().__init__()

    def reset(self) -> None:
        self.reps = 0
        self.stage = None

    def process(self, landmarks) -> dict:
        left_vis = landmarks[self.LEFT_ELBOW].visibility
        right_vis = landmarks[self.RIGHT_ELBOW].visibility

        if left_vis >= right_vis:
            shoulder_idx, elbow_idx, wrist_idx = self.LEFT_SHOULDER, self.LEFT_ELBOW, self.LEFT_WRIST
            hip_idx, knee_idx = self.LEFT_HIP, self.LEFT_KNEE
        else:
            shoulder_idx, elbow_idx, wrist_idx = self.RIGHT_SHOULDER, self.RIGHT_ELBOW, self.RIGHT_WRIST
            hip_idx, knee_idx = self.RIGHT_HIP, self.RIGHT_KNEE

        elbow_angle = self.calculate_angle(
            self.get_point(landmarks, shoulder_idx),
            self.get_point(landmarks, elbow_idx),
            self.get_point(landmarks, wrist_idx),
        )

        hinge_angle = self.calculate_angle(
            self.get_point(landmarks, shoulder_idx),
            self.get_point(landmarks, hip_idx),
            self.get_point(landmarks, knee_idx),
        )

        key_landmarks_visible = (
            landmarks[shoulder_idx].visibility > self.MIN_VISIBILITY
            and landmarks[elbow_idx].visibility > self.MIN_VISIBILITY
            and landmarks[wrist_idx].visibility > self.MIN_VISIBILITY
        )

        if key_landmarks_visible:
            if elbow_angle > self.EXTENDED_THRESHOLD:
                self.stage = "extended"

            if elbow_angle < self.ROWED_THRESHOLD and self.stage == "extended":
                self.stage = "rowed"
                self.reps += 1

        hinge_status = "HINGE OK" if hinge_angle < 160 else "STAND UP LESS — HINGE FORWARD"

        return {
            "reps": self.reps,
            "elbow_angle": int(elbow_angle),
            "hinge_status": hinge_status,
        }
