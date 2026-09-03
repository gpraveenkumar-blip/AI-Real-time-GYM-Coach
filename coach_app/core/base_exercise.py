import math
import time
from abc import ABC, abstractmethod


class BaseExercise(ABC):
    def __init__(self):
        self.reps = 0
        self.stage = None
        self._hold_last_tick = None

    def calculate_angle(self, a, b, c):
        ax, ay = a[0] - b[0], a[1] - b[1]
        cx, cy = c[0] - b[0], c[1] - b[1]
        mag_a = math.hypot(ax, ay)
        mag_c = math.hypot(cx, cy)
        if mag_a < 1e-9 or mag_c < 1e-9:
            return 0.0
        cos_angle = max(-1.0, min(1.0, (ax * cx + ay * cy) / (mag_a * mag_c)))
        return math.degrees(math.acos(cos_angle))

    def get_point(self, landmarks, idx):
        if landmarks is None or idx < 0 or idx >= len(landmarks):
            raise IndexError(f"Landmark index out of range: {idx}")
        p = landmarks[idx]
        return float(p.x), float(p.y)

    def accumulate_hold(self, is_holding: bool) -> None:
        now = time.monotonic()
        if not is_holding:
            self._hold_last_tick = None
            return
        if self._hold_last_tick is None:
            self._hold_last_tick = now
            return
        elapsed = max(0.0, now - self._hold_last_tick)
        whole_seconds = int(elapsed)
        if whole_seconds:
            self.reps += whole_seconds
            self._hold_last_tick += whole_seconds

    @abstractmethod
    def process(self, landmarks):
        raise NotImplementedError

    @abstractmethod
    def reset(self):
        raise NotImplementedError
