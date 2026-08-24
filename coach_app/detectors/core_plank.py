from core.base_exercise import BaseExercise


class PlankDetector(BaseExercise):
    """Hold-based: checks the body stays in a straight line from shoulder
    to hip to ankle, and accumulates hold time while form is good — 1 rep
    = 1 second held with good alignment. See BaseExercise.accumulate_hold.
    """
    STRAIGHT_MIN_ANGLE = 160
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
        self._hold_last_tick = None

    def process(self, landmarks) -> dict:
        left_vis = landmarks[self.LEFT_HIP].visibility
        right_vis = landmarks[self.RIGHT_HIP].visibility

        if left_vis >= right_vis:
            shoulder_idx, hip_idx, ankle_idx = self.LEFT_SHOULDER, self.LEFT_HIP, self.LEFT_ANKLE
        else:
            shoulder_idx, hip_idx, ankle_idx = self.RIGHT_SHOULDER, self.RIGHT_HIP, self.RIGHT_ANKLE

        body_angle = self.calculate_angle(
            self.get_point(landmarks, shoulder_idx),
            self.get_point(landmarks, hip_idx),
            self.get_point(landmarks, ankle_idx),
        )

        key_landmarks_visible = (
            landmarks[shoulder_idx].visibility > self.MIN_VISIBILITY
            and landmarks[hip_idx].visibility > self.MIN_VISIBILITY
            and landmarks[ankle_idx].visibility > self.MIN_VISIBILITY
        )

        good_form = key_landmarks_visible and body_angle >= self.STRAIGHT_MIN_ANGLE

        self.accumulate_hold(good_form)

        if not key_landmarks_visible:
            form_status = "N/A"
        elif good_form:
            form_status = "GOOD FORM — HOLD"
        elif body_angle < self.STRAIGHT_MIN_ANGLE - 15:
            form_status = "HIPS SAGGING OR PIKED"
        else:
            form_status = "ALMOST STRAIGHT"

        return {
            "reps": self.reps,
            "body_angle": int(body_angle),
            "form_status": form_status,
        }
