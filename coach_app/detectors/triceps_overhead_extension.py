from core.base_exercise import BaseExercise


class OverheadExtensionDetector(BaseExercise):
    """Standing, holding a loaded backpack overhead and lowering it behind
    the head by bending the elbow, then extending back up. Tracks elbow
    flexion plus a check that the arm stays overhead throughout.
    """
    FLEXED_THRESHOLD = 80    # backpack lowered behind head
    EXTENDED_THRESHOLD = 160  # arm fully extended overhead
    MIN_VISIBILITY = 0.6

    LEFT_SHOULDER = 11
    LEFT_ELBOW = 13
    LEFT_WRIST = 15
    RIGHT_SHOULDER = 12
    RIGHT_ELBOW = 14
    RIGHT_WRIST = 16

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
        else:
            shoulder_idx, elbow_idx, wrist_idx = self.RIGHT_SHOULDER, self.RIGHT_ELBOW, self.RIGHT_WRIST

        elbow_angle = self.calculate_angle(
            self.get_point(landmarks, shoulder_idx),
            self.get_point(landmarks, elbow_idx),
            self.get_point(landmarks, wrist_idx),
        )

        key_landmarks_visible = (
            landmarks[shoulder_idx].visibility > self.MIN_VISIBILITY
            and landmarks[elbow_idx].visibility > self.MIN_VISIBILITY
            and landmarks[wrist_idx].visibility > self.MIN_VISIBILITY
        )

        if key_landmarks_visible:
            if elbow_angle < self.FLEXED_THRESHOLD:
                self.stage = "flexed"

            if elbow_angle > self.EXTENDED_THRESHOLD and self.stage == "flexed":
                self.stage = "extended"
                self.reps += 1

        overhead_ok = landmarks[wrist_idx].y < landmarks[shoulder_idx].y
        elbow_status = "ARM OVERHEAD" if overhead_ok else "KEEP ARM OVERHEAD"

        return {
            "reps": self.reps,
            "elbow_angle": int(elbow_angle),
            "elbow_status": elbow_status,
        }
