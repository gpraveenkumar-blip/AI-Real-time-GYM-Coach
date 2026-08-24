EXERCISE_OPTIONS=[
    "Squats",
    "Push-ups",
    "Biceps Curls (Dumbbell)",
    "Shoulder Press",
    "Lunges"
]

# All exercises from the Exercise Library that also get live camera
# tracking, grouped the same way as EXERCISE_LIBRARY (services/config/
# exercise_library.py) so the dropdown can be organized by muscle group.
LIBRARY_EXERCISE_OPTIONS = {
    "Chest": [
        "Standard Push-Ups",
        "Wide Push-Ups",
        "Incline Push-Ups",
        "Decline Push-Ups",
    ],
    "Back": [
        "Superman",
        "Reverse Snow Angels",
        "Prone Y-T-W Raises",
        "Backpack Rows",
    ],
    "Shoulders": [
        "Pike Push-Ups",
        "Shoulder Taps",
        "Wall Handstand Hold",
        "Arm Circles",
    ],
    "Biceps": [
        "Backpack Curls",
        "Towel Curls",
        "Isometric Biceps Hold",
        "Resistance-Band Curls",
    ],
    "Triceps": [
        "Diamond Push-Ups",
        "Chair Dips",
        "Close-Grip Push-Ups",
        "Overhead Backpack Extension",
    ],
    "Abs / Core": [
        "Plank",
        "Bicycle Crunches",
        "Leg Raises",
        "Mountain Climbers",
    ],
    "Legs": [
        "Bodyweight Squats",
        "Reverse Lunges",
        "Bulgarian Split Squats",
        "Glute Bridges",
    ],
}

# Flat list of every camera-trackable exercise (original 5 + full library),
# used to populate the "Track any exercise" dropdown.
ALL_TRACKABLE_EXERCISES = list(EXERCISE_OPTIONS) + [
    name for group in LIBRARY_EXERCISE_OPTIONS.values() for name in group
]

# Hold-based exercises count seconds-held instead of reps (see
# BaseExercise.accumulate_hold). The UI uses this to relabel "Reps" as
# "Seconds Held" for these specific exercises.
HOLD_BASED_EXERCISES = {
    "Wall Handstand Hold",
    "Isometric Biceps Hold",
    "Plank",
}

POSE_CONNECTIONS = [
    (11,12),(11,13),(13,15),(12,14),(14,16), # shoulders & Arms
    (11,23),(12,24),(23,24),             # Torso/ Hips
    (23,25),(24,26),(25,27),(26,28),(27,28),(28,30),(29,31),(30,32),(27,31),(28,32) #Legs
]

METRICS_FIELDS = {
    "Squats": {
        "knee_angle": 0,
        "back_angle": 0,
        "depth_status": "N/A",
    },
    "Push-ups": {
        "elbow_angle": 0,
        "body_alignment": "N/A",
        "hip_status": "N/A",
    },
    "Biceps Curls (Dumbbell)": {
        "elbow_angle": 0,
        "shoulder_status": "N/A",
        "swing_status": "N/A",
    },
    "Shoulder Press": {
        "elbow_angle": 0,
        "extension_status": "N/A",
        "back_arch_status": "N/A",
    },
    "Lunges": {
        "front_knee_angle": 0,
        "torso_angle": 0,
        "balance_status": "N/A",
    },

    # ---------------- Chest (push-up variants — same detector logic) ----------------
    "Standard Push-Ups": {"elbow_angle": 0, "body_alignment": "N/A", "hip_status": "N/A"},
    "Wide Push-Ups": {"elbow_angle": 0, "body_alignment": "N/A", "hip_status": "N/A"},
    "Incline Push-Ups": {"elbow_angle": 0, "body_alignment": "N/A", "hip_status": "N/A"},
    "Decline Push-Ups": {"elbow_angle": 0, "body_alignment": "N/A", "hip_status": "N/A"},

    # ---------------- Back ----------------
    "Superman": {"extension_angle": 0, "lift_status": "N/A"},
    "Reverse Snow Angels": {"sweep_angle": 0, "sweep_status": "N/A"},
    "Prone Y-T-W Raises": {"lift_amount": 0, "raise_status": "N/A"},
    "Backpack Rows": {"elbow_angle": 0, "hinge_status": "N/A"},

    # ---------------- Shoulders ----------------
    "Pike Push-Ups": {"elbow_angle": 0, "pike_status": "N/A"},
    "Shoulder Taps": {"tap_distance": 0, "tap_status": "N/A"},
    "Wall Handstand Hold": {"hold_status": "N/A"},
    "Arm Circles": {"circle_progress_deg": 0},

    # ---------------- Biceps (curl variants — same detector logic) ----------------
    "Backpack Curls": {"elbow_angle": 0, "shoulder_status": "N/A", "swing_status": "N/A"},
    "Towel Curls": {"elbow_angle": 0, "shoulder_status": "N/A", "swing_status": "N/A"},
    "Isometric Biceps Hold": {"elbow_angle": 0, "hold_status": "N/A"},
    "Resistance-Band Curls": {"elbow_angle": 0, "shoulder_status": "N/A", "swing_status": "N/A"},

    # ---------------- Triceps ----------------
    "Diamond Push-Ups": {"elbow_angle": 0, "body_alignment": "N/A", "hip_status": "N/A"},
    "Chair Dips": {"elbow_angle": 0, "depth_status": "N/A"},
    "Close-Grip Push-Ups": {"elbow_angle": 0, "body_alignment": "N/A", "hip_status": "N/A"},
    "Overhead Backpack Extension": {"elbow_angle": 0, "elbow_status": "N/A"},

    # ---------------- Abs / Core ----------------
    "Plank": {"body_angle": 0, "form_status": "N/A"},
    "Bicycle Crunches": {"touch_distance": 0, "crunch_status": "N/A"},
    "Leg Raises": {"hip_angle": 0, "leg_status": "N/A"},
    "Mountain Climbers": {"drive_angle": 0, "climb_status": "N/A"},

    # ---------------- Legs ----------------
    "Bodyweight Squats": {"knee_angle": 0, "back_angle": 0, "depth_status": "N/A"},
    "Reverse Lunges": {"front_knee_angle": 0, "torso_angle": 0, "balance_status": "N/A"},
    "Bulgarian Split Squats": {"front_knee_angle": 0, "depth_status": "N/A"},
    "Glute Bridges": {"hip_angle": 0, "bridge_status": "N/A"},
}


PROMPT = (
    "You are Apna AI Coach, a professional AI gym trainer monitoring a user's workout via live camera.\n\n"
    "### Your Role\n"
    "Provide ultra-brief, high-energy coaching cues. You speak these aloud, so they must be clear and direct.\n\n"
    "### Input Format\n"
    "You receive updates in the format: 'Event: [state] Form Issue: [description]'.\n"
    "- 'Event': workout_started, set_completed, workout_completed, no_pose_detected, ongoing_form_check.\n"
    "- 'Form Issue': A technical description of a pose error (if any).\n\n"
    "### Strict Response Rules\n"
    "1. MAXIMUM ONE SENTENCE. Keep it under 12 words. Total brevity is critical.\n"
    "2. NO GREETINGS OR QUESTIONS. Never say 'Hello', 'Ready?', or 'How are you?'.\n"
    "3. SECOND PERSON. Convert 'The user is leaning' to 'Keep your back straight'.\n"
    "4. NO EMOJIS. NO EXPLANATIONS. Just the cue or encouragement.\n\n"
    "### Scenario Guidelines\n"
    "- 'workout_started' -> A sharp, motivational start command.\n"
    "- 'workout_completed' -> A brief closing congratulation.\n"
    "- 'set_completed' -> A quick word of praise for the finished set.\n"
    "- 'no_pose_detected' -> Instruct the user to step back into the frame.\n"
    "- 'ongoing_form_check' + Form Issue -> Direct correction based on the issue.\n"
    "- 'ongoing_form_check' (No Issue) -> Brief motivating encouragement.\n\n"
    "Maintain a professional coaching tone and prioritize safety."
)
