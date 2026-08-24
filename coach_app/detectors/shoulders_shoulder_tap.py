from core.base_exercise import BaseExercise


class ShoulderTapDetector(BaseExercise):
    """Plank position, alternately tapping the opposite shoulder with each
    hand. Counts a rep each time either wrist gets close to the opposite
    shoulder and then pulls back — so left-tap + right-tap = 2 reps.
    """
    TOUCH_THRESHOLD = 0.10     # normalized 2D distance, wrist close to shoulder
    RELEASE_THRESHOLD = 0.20
    MIN_VISIBILITY = 0.6

    LEFT_WRIST = 15
    RIGHT_WRIST = 16
    LEFT_SHOULDER = 11
    RIGHT_SHOULDER = 12

    def __init__(self):
        super().__init__()
        self._armed = True   # prevents double-counting while still in contact

    def reset(self) -> None:
        self.reps = 0
        self.stage = None
        self._armed = True

    @staticmethod
    def _distance(p1, p2):
        return ((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2) ** 0.5

    def process(self, landmarks) -> dict:
        key_landmarks_visible = (
            landmarks[self.LEFT_WRIST].visibility > self.MIN_VISIBILITY
            and landmarks[self.RIGHT_WRIST].visibility > self.MIN_VISIBILITY
            and landmarks[self.LEFT_SHOULDER].visibility > self.MIN_VISIBILITY
            and landmarks[self.RIGHT_SHOULDER].visibility > self.MIN_VISIBILITY
        )

        left_wrist_to_right_shoulder = self._distance(
            self.get_point(landmarks, self.LEFT_WRIST), self.get_point(landmarks, self.RIGHT_SHOULDER)
        )
        right_wrist_to_left_shoulder = self._distance(
            self.get_point(landmarks, self.RIGHT_WRIST), self.get_point(landmarks, self.LEFT_SHOULDER)
        )

        min_distance = min(left_wrist_to_right_shoulder, right_wrist_to_left_shoulder)

        if key_landmarks_visible:
            if min_distance < self.TOUCH_THRESHOLD and self._armed:
                self.reps += 1
                self._armed = False
                self.stage = "tapped"

            if min_distance > self.RELEASE_THRESHOLD:
                self._armed = True
                self.stage = "plank"

        tap_status = "TAP!" if self.stage == "tapped" else "PLANK"

        return {
            "reps": self.reps,
            "tap_distance": round(min_distance, 3),
            "tap_status": tap_status,
        }
