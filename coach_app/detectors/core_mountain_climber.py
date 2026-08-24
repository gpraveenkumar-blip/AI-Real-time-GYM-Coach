from core.base_exercise import BaseExercise


class MountainClimberDetector(BaseExercise):
    """Plank position, alternately driving each knee toward the chest.
    Tracks hip flexion (shoulder-hip-knee angle) on whichever leg is
    more flexed at the moment — counts a rep each time a knee drives in
    and back out.
    """
    DRIVEN_IN_THRESHOLD = 100
    EXTENDED_THRESHOLD = 155
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
        left_hip_angle = self.calculate_angle(
            self.get_point(landmarks, self.LEFT_SHOULDER),
            self.get_point(landmarks, self.LEFT_HIP),
            self.get_point(landmarks, self.LEFT_KNEE),
        )
        right_hip_angle = self.calculate_angle(
            self.get_point(landmarks, self.RIGHT_SHOULDER),
            self.get_point(landmarks, self.RIGHT_HIP),
            self.get_point(landmarks, self.RIGHT_KNEE),
        )

        # Whichever leg is more flexed right now is the "driving" leg.
        driving_angle = min(left_hip_angle, right_hip_angle)

        key_landmarks_visible = (
            landmarks[self.LEFT_HIP].visibility > self.MIN_VISIBILITY
            and landmarks[self.RIGHT_HIP].visibility > self.MIN_VISIBILITY
            and landmarks[self.LEFT_KNEE].visibility > self.MIN_VISIBILITY
            and landmarks[self.RIGHT_KNEE].visibility > self.MIN_VISIBILITY
        )

        if key_landmarks_visible:
            if driving_angle < self.DRIVEN_IN_THRESHOLD:
                self.stage = "driven_in"

            if driving_angle > self.EXTENDED_THRESHOLD and self.stage == "driven_in":
                self.stage = "extended"
                self.reps += 1

        climb_status = "KNEE DRIVEN IN" if self.stage == "driven_in" else "PLANK"

        return {
            "reps": self.reps,
            "drive_angle": int(driving_angle),
            "climb_status": climb_status,
        }
