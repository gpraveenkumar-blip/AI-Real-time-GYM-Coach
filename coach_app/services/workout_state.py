from dataclasses import dataclass, field
from time import monotonic

@dataclass
class WorkoutState:
    exercise: str = ""
    target_reps: int = 10
    reps: int = 0
    set_number: int = 1
    total_sets: int = 1
    form_score: float = 100.0
    last_form_issue: str = ""
    phase: str = "ready"
    started_at: float = field(default_factory=monotonic)

    def reset(self, exercise, target_reps=10, set_number=1, total_sets=1):
        self.exercise = exercise
        self.target_reps = max(1, int(target_reps))
        self.reps = 0
        self.set_number = max(1, int(set_number))
        self.total_sets = max(1, int(total_sets))
        self.form_score = 100.0
        self.last_form_issue = ""
        self.phase = "ready"
        self.started_at = monotonic()

    def register_rep(self, form_score=None, form_issue=""):
        self.reps += 1
        if form_score is not None:
            self.form_score = max(0.0, min(100.0, float(form_score)))
        if form_issue:
            self.last_form_issue = form_issue
        self.phase = "complete" if self.reps >= self.target_reps else "working"

    @property
    def progress(self):
        return min(1.0, self.reps / max(1, self.target_reps))
