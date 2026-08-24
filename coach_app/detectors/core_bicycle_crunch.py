from core.base_exercise import BaseExercise


class BicycleCrunchDetector(BaseExercise):
    """Lying on the back, alternating elbow-to-opposite-knee crunches.
    Counts a rep each time either elbow gets close to the opposite knee
    and then pulls back — so left-touch + right-touch = 2 reps.
    """
    TOUCH_THRESHOLD = 0.12
    RELEASE_THRESHOLD = 0.22
    MIN_VISIBILITY = 0.5

    LEFT_ELBOW = 13
    RIGHT_ELBOW = 14
    LEFT_KNEE = 25
    RIGHT_KNEE = 26

    def __init__(self):
        super().__init__()
        self._armed = True

    def reset(self) -> None:
        self.reps = 0
        self.stage = None
        self._armed = True

    @staticmethod
    def _distance(p1, p2):
        return ((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2) ** 0.5

    def process(self, landmarks) -> dict:
        key_landmarks_visible = all(
            landmarks[i].visibility > self.MIN_VISIBILITY
            for i in (self.LEFT_ELBOW, self.RIGHT_ELBOW, self.LEFT_KNEE, self.RIGHT_KNEE)
        )

        left_elbow_to_right_knee = self._distance(
            self.get_point(landmarks, self.LEFT_ELBOW), self.get_point(landmarks, self.RIGHT_KNEE)
        )
        right_elbow_to_left_knee = self._distance(
            self.get_point(landmarks, self.RIGHT_ELBOW), self.get_point(landmarks, self.LEFT_KNEE)
        )

        min_distance = min(left_elbow_to_right_knee, right_elbow_to_left_knee)

        if key_landmarks_visible:
            if min_distance < self.TOUCH_THRESHOLD and self._armed:
                self.reps += 1
                self._armed = False
                self.stage = "touched"

            if min_distance > self.RELEASE_THRESHOLD:
                self._armed = True
                self.stage = "extended"

        crunch_status = "TOUCH!" if self.stage == "touched" else "EXTENDED"

        return {
            "reps": self.reps,
            "touch_distance": round(min_distance, 3),
            "crunch_status": crunch_status,
        }
