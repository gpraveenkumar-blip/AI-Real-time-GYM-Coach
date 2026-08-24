# Reference exercise library, organized by muscle group. These are shown as
# a browsable guide in the dashboard. Live AI pose-tracking currently only
# covers the 5 exercises in EXERCISE_OPTIONS (workout_config.py) — everything
# here is reference content for supplementing a tracked workout, not
# camera-tracked itself.

EXERCISE_LIBRARY = {
    "Chest": {
        "emoji": "🫀",
        "exercises": [
            "Standard Push-Ups",
            "Wide Push-Ups",
            "Incline Push-Ups",
            "Decline Push-Ups",
        ],
    },
    "Back": {
        "emoji": "🦅",
        "exercises": [
            "Superman",
            "Reverse Snow Angels",
            "Prone Y-T-W Raises",
            "Backpack Rows",
        ],
    },
    "Shoulders": {
        "emoji": "🏋️",
        "exercises": [
            "Pike Push-Ups",
            "Shoulder Taps",
            "Wall Handstand Hold",
            "Arm Circles",
        ],
    },
    "Biceps": {
        "emoji": "💪",
        "exercises": [
            "Backpack Curls",
            "Towel Curls",
            "Isometric Biceps Hold",
            "Resistance-Band Curls",
        ],
    },
    "Triceps": {
        "emoji": "🔥",
        "exercises": [
            "Diamond Push-Ups",
            "Chair Dips",
            "Close-Grip Push-Ups",
            "Overhead Backpack Extension",
        ],
    },
    "Abs / Core": {
        "emoji": "🧱",
        "exercises": [
            "Plank",
            "Bicycle Crunches",
            "Leg Raises",
            "Mountain Climbers",
        ],
    },
    "Legs": {
        "emoji": "🦵",
        "exercises": [
            "Bodyweight Squats",
            "Reverse Lunges",
            "Bulgarian Split Squats",
            "Glute Bridges",
        ],
    },
}

# Sets/reps guidance by experience level, plus a single recommended
# (int) sets/reps pair used to auto-fill the workout plan inputs.
DIFFICULTY_LEVELS = {
    "Beginner": {
        "sets_range": "2–3 sets",
        "reps_range": "8–12 reps",
        "recommended_sets": 3,
        "recommended_reps": 10,
        "badge_class": "beginner",
    },
    "Intermediate": {
        "sets_range": "3–4 sets",
        "reps_range": "10–15 reps",
        "recommended_sets": 4,
        "recommended_reps": 12,
        "badge_class": "intermediate",
    },
    "Advanced": {
        "sets_range": "4 sets",
        "reps_range": "15–20 reps",
        "recommended_sets": 4,
        "recommended_reps": 18,
        "badge_class": "advanced",
    },
}
