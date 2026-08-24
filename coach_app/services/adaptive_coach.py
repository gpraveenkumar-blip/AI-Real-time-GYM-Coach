class AdaptiveCoach:
    def __init__(self):
        self.last_issue = ""
        self.motivation_index = 0

    def start(self, exercise, target):
        return f"Let's go. {exercise}, {target} reps. Controlled movement and steady breathing."

    def rep(self, exercise, rep, target, form_score=100, form_issue=""):
        if form_issue and form_issue != self.last_issue:
            self.last_issue = form_issue
            return form_issue
        if rep >= target:
            return f"Excellent! {rep} reps. Set complete."
        if target - rep == 1:
            return f"{rep}. One more! Finish strong!"
        if rep == max(1, target // 2):
            return f"{rep}. Halfway there. Keep that form!"
        phrases = [
            "Good rep. Keep going.",
            "Strong work. Stay controlled.",
            "Nice. Keep your breathing steady.",
            "That's it. Stay focused.",
            "Good control. You've got this."
        ]
        msg = phrases[self.motivation_index % len(phrases)]
        self.motivation_index += 1
        return f"{rep}. {msg}"

    def rest(self, seconds, next_exercise=None):
        if next_exercise:
            return f"Great set. Recover for {seconds} seconds. Next up: {next_exercise}."
        return f"Great set. Recover for {seconds} seconds, then get ready for the next set."

    def complete(self):
        return "Workout complete! You showed up, stayed consistent, and finished strong. Great work!"
