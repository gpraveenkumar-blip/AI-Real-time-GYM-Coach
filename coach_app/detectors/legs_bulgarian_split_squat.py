from core.base_exercise import BaseExercise


class BulgarianSplitSquatDetector(BaseExercise):
    """Single-leg squat with the rear foot elevated behind on a bench or
    chair. Tracks the front (standing) leg's knee angle the same way a
    regular squat does — the rear leg doesn't need to be clearly visible.
    """
    DOWN_THRESHOLD = 100
    UP_THRESHOLD = 160
    MIN_VISIBILITY = 0.6

    LEFT_HIP = 23
    LEFT_KNEE = 25
    LEFT_ANKLE = 27
    RIGHT_HIP = 24
    RIGHT_KNEE = 26
    RIGHT_ANKLE = 28

    def __init__(self):
        super().__init__()

    def reset(self) -> None:
        self.reps = 0
        self.stage = None

    def process(self, landmarks) -> dict:
        left_knee_angle = self.calculate_angle(
            self.get_point(landmarks, self.LEFT_HIP),
            self.get_point(landmarks, self.LEFT_KNEE),
            self.get_point(landmarks, self.LEFT_ANKLE),
        )
        right_knee_angle = self.calculate_angle(
            self.get_point(landmarks, self.RIGHT_HIP),
            self.get_point(landmarks, self.RIGHT_KNEE),
            self.get_point(landmarks, self.RIGHT_ANKLE),
        )

        # The front (working) leg is whichever is currently more visible —
        # in a split-stance the rear leg is often partially out of frame.
        if landmarks[self.LEFT_KNEE].visibility >= landmarks[self.RIGHT_KNEE].visibility:
            front_knee_angle = left_knee_angle
            hip_idx, knee_idx, ankle_idx = self.LEFT_HIP, self.LEFT_KNEE, self.LEFT_ANKLE
        else:
            front_knee_angle = right_knee_angle
            hip_idx, knee_idx, ankle_idx = self.RIGHT_HIP, self.RIGHT_KNEE, self.RIGHT_ANKLE

        key_landmarks_visible = (
            landmarks[hip_idx].visibility > self.MIN_VISIBILITY
            and landmarks[knee_idx].visibility > self.MIN_VISIBILITY
            and landmarks[ankle_idx].visibility > self.MIN_VISIBILITY
        )

        if key_landmarks_visible:
            if front_knee_angle < self.DOWN_THRESHOLD:
                self.stage = "down"

            if front_knee_angle > self.UP_THRESHOLD and self.stage == "down":
                self.stage = "up"
                self.reps += 1

        depth_status = "GOOD DEPTH" if self.stage == "down" else "STANDING"

        return {
            "reps": self.reps,
            "front_knee_angle": int(front_knee_angle),
            "depth_status": depth_status,
        }
