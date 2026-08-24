from core.base_exercise import BaseExercise


class IsometricBicepsHoldDetector(BaseExercise):
    """Hold-based: sustains an elbow curl position (roughly 90° of flexion)
    without moving. 1 rep = 1 second held with the elbow angle inside the
    target range. See BaseExercise.accumulate_hold for the reps-as-seconds
    mapping.
    """
    TARGET_MIN_ANGLE = 60
    TARGET_MAX_ANGLE = 110
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
        self._hold_last_tick = None

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

        in_target_range = key_landmarks_visible and self.TARGET_MIN_ANGLE <= elbow_angle <= self.TARGET_MAX_ANGLE

        self.accumulate_hold(in_target_range)
        self.stage = "holding" if in_target_range else "out_of_range"

        hold_status = "HOLDING" if in_target_range else "ADJUST ELBOW ANGLE"

        return {
            "reps": self.reps,
            "elbow_angle": int(elbow_angle),
            "hold_status": hold_status,
        }
