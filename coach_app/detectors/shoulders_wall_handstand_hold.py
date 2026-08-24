from core.base_exercise import BaseExercise


class WallHandstandHoldDetector(BaseExercise):
    """Hold-based: checks the body is inverted (ankles above hips above
    shoulders in the frame) and accumulates hold time — 1 rep = 1 second
    held. See BaseExercise.accumulate_hold for how that mapping works.
    Requires the full body to be visible, camera positioned to see the
    whole wall/handstand setup.
    """
    MIN_VISIBILITY = 0.5
    INVERSION_MARGIN = 0.03   # ankles must be clearly above hips, hips above shoulders

    LEFT_SHOULDER = 11
    RIGHT_SHOULDER = 12
    LEFT_HIP = 23
    RIGHT_HIP = 24
    LEFT_ANKLE = 27
    RIGHT_ANKLE = 28

    def __init__(self):
        super().__init__()

    def reset(self) -> None:
        self.reps = 0
        self.stage = None
        self._hold_last_tick = None

    def process(self, landmarks) -> dict:
        key_landmarks_visible = all(
            landmarks[i].visibility > self.MIN_VISIBILITY
            for i in (self.LEFT_SHOULDER, self.RIGHT_SHOULDER, self.LEFT_HIP,
                      self.RIGHT_HIP, self.LEFT_ANKLE, self.RIGHT_ANKLE)
        )

        shoulder_y = (landmarks[self.LEFT_SHOULDER].y + landmarks[self.RIGHT_SHOULDER].y) / 2
        hip_y = (landmarks[self.LEFT_HIP].y + landmarks[self.RIGHT_HIP].y) / 2
        ankle_y = (landmarks[self.LEFT_ANKLE].y + landmarks[self.RIGHT_ANKLE].y) / 2

        # Smaller y = higher in frame. Inverted: ankles highest, then hips, then shoulders.
        is_inverted = (
            key_landmarks_visible
            and ankle_y < hip_y - self.INVERSION_MARGIN
            and hip_y < shoulder_y - self.INVERSION_MARGIN
        )

        self.accumulate_hold(is_inverted)
        self.stage = "inverted" if is_inverted else "not_inverted"

        hold_status = "HOLDING HANDSTAND" if is_inverted else "NOT INVERTED"

        return {
            "reps": self.reps,
            "hold_status": hold_status,
        }
