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

        dot = ax * cx + ay * cy

        mag_a = math.sqrt(ax ** 2 + ay ** 2)
        mag_c = math.sqrt(cx ** 2 + cy ** 2)

        if mag_a * mag_c == 0:
            return 0.0

        cos_angle = max(-1.0, min(1.0, dot / (mag_a * mag_c)))

        return math.degrees(math.acos(cos_angle))

    def get_point(self, landmarks, idx):
        p = landmarks[idx]

        return (p.x, p.y)

    def accumulate_hold(self, is_holding: bool) -> None:
        """Shared timer for hold-based exercises (Plank, Wall Handstand Hold,
        Isometric Biceps Hold, etc). Each full second of *continuous* hold
        increments self.reps by 1 — this deliberately reuses the exact same
        reps -> sets_completed -> voice-coaching pipeline the rep-counted
        exercises use (see services/tracking/metrics.py), so '10 reps' for a
        held exercise means '10 seconds held'. Breaking form pauses the
        accumulator without losing reps already banked.
        """
        now = time.time()

        if not is_holding:
            self._hold_last_tick = None
            return

        if self._hold_last_tick is None:
            self._hold_last_tick = now
            return

        elapsed = now - self._hold_last_tick

        while elapsed >= 1.0:
            self.reps += 1
            elapsed -= 1.0
            self._hold_last_tick += 1.0

    @abstractmethod
    def process(self, landmarks):
        pass

    @abstractmethod
    def reset(self):
        pass
