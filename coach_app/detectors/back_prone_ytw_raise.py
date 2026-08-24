from core.base_exercise import BaseExercise


class ProneYTWRaiseDetector(BaseExercise):
    """Lying prone, lifting straight (or bent) arms off the floor into a Y,
    T, or W shape. Detection doesn't distinguish which letter shape is
    used — it just tracks whether the arm is raised off the floor, since
    that's what a single 2D camera can reliably see. Best with a side-on
    or slightly elevated camera angle.
    """
    RAISED_THRESHOLD = 0.05    # wrist meaningfully above the shoulder line
    LOWERED_THRESHOLD = 0.015
    MIN_VISIBILITY = 0.6

    LEFT_SHOULDER = 11
    LEFT_WRIST = 15
    RIGHT_SHOULDER = 12
    RIGHT_WRIST = 16

    def __init__(self):
        super().__init__()

    def reset(self) -> None:
        self.reps = 0
        self.stage = None

    def process(self, landmarks) -> dict:
        left_vis = landmarks[self.LEFT_WRIST].visibility
        right_vis = landmarks[self.RIGHT_WRIST].visibility

        if left_vis >= right_vis:
            shoulder_idx, wrist_idx = self.LEFT_SHOULDER, self.LEFT_WRIST
        else:
            shoulder_idx, wrist_idx = self.RIGHT_SHOULDER, self.RIGHT_WRIST

        # Smaller y = higher up the frame, so a positive value here means
        # the wrist is above (behind, off the floor from) the shoulder line.
        lift = landmarks[shoulder_idx].y - landmarks[wrist_idx].y

        key_landmarks_visible = (
            landmarks[shoulder_idx].visibility > self.MIN_VISIBILITY
            and landmarks[wrist_idx].visibility > self.MIN_VISIBILITY
        )

        if key_landmarks_visible:
            if lift < self.LOWERED_THRESHOLD:
                self.stage = "lowered"

            if lift > self.RAISED_THRESHOLD and self.stage == "lowered":
                self.stage = "raised"
                self.reps += 1

        raise_status = "RAISED" if self.stage == "raised" else "LOWERED"

        return {
            "reps": self.reps,
            "lift_amount": round(lift, 3),
            "raise_status": raise_status,
        }
