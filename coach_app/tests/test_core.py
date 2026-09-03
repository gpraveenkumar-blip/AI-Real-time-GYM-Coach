import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from types import SimpleNamespace

from core.base_exercise import BaseExercise


class DummyExercise(BaseExercise):
    def process(self, landmarks):
        return {}

    def reset(self):
        self.reps = 0
        self.stage = None
        self._hold_last_tick = None


def lm(x, y, visibility=1.0):
    return SimpleNamespace(x=x, y=y, visibility=visibility)


def test_angle_is_90_degrees():
    ex = DummyExercise()
    assert round(ex.calculate_angle((1, 0), (0, 0), (0, 1))) == 90


def test_zero_length_angle_is_safe():
    ex = DummyExercise()
    assert ex.calculate_angle((0, 0), (0, 0), (1, 1)) == 0.0


def test_get_point_returns_floats():
    ex = DummyExercise()
    points = [lm(0.2, 0.3)]
    assert ex.get_point(points, 0) == (0.2, 0.3)


def test_get_point_rejects_invalid_index():
    ex = DummyExercise()
    try:
        ex.get_point([], 0)
    except IndexError:
        pass
    else:
        raise AssertionError("Expected IndexError")
