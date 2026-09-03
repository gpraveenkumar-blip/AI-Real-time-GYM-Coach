import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import os
from pathlib import Path

os.environ["AI_GYM_DB_PATH"] = str(Path(__file__).with_name("test-data.db"))

from services.persistence.exercise_repository import (
    init_db,
    get_or_create_user_from_saas,
    add_exercise,
    get_users_exercises,
)


def test_repository_is_user_scoped():
    init_db()
    user_a = get_or_create_user_from_saas(101, "alice")
    user_b = get_or_create_user_from_saas(102, "bob")

    add_exercise(user_a["id"], "Squats", 10, 1, 30)
    add_exercise(user_b["id"], "Push-ups", 5, 1, 20)

    a_rows = get_users_exercises(user_a["id"])
    b_rows = get_users_exercises(user_b["id"])

    assert len(a_rows) == 1
    assert a_rows[0]["exercise_name"] == "Squats"
    assert len(b_rows) == 1
    assert b_rows[0]["exercise_name"] == "Push-ups"
