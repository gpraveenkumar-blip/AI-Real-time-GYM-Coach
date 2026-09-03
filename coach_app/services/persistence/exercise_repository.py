"""Small, defensive SQLite persistence layer for workout history."""
from __future__ import annotations

import os
import sqlite3
import threading
from pathlib import Path
from typing import Optional

_DEFAULT_DB_PATH = Path(__file__).resolve().parents[2] / "data.db"
_DB_PATH = Path(os.getenv("AI_GYM_DB_PATH", str(_DEFAULT_DB_PATH))).expanduser().resolve()
_CONNECTIONS = threading.local()


def _connect() -> sqlite3.Connection:
    conn = getattr(_CONNECTIONS, "connection", None)
    if conn is not None:
        try:
            conn.execute("SELECT 1")
            return conn
        except sqlite3.Error:
            try:
                conn.close()
            except sqlite3.Error:
                pass

    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(
        str(_DB_PATH),
        timeout=10,
        check_same_thread=True,
    )
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 10000")
    _CONNECTIONS.connection = conn
    try:
        os.chmod(_DB_PATH, 0o600)
    except OSError:
        pass
    return conn


def _validate_user_id(user_id: int) -> int:
    if isinstance(user_id, bool):
        raise ValueError("Invalid user id")
    try:
        value = int(user_id)
    except (TypeError, ValueError):
        raise ValueError("Invalid user id") from None
    if value <= 0:
        raise ValueError("Invalid user id")
    return value


def _validate_workout(exercise_name: str, reps: int, sets: int, duration: float) -> tuple[str, int, int, int]:
    name = str(exercise_name or "").strip()
    if not name or len(name) > 120:
        raise ValueError("Invalid exercise name")

    reps_i = int(reps)
    sets_i = int(sets)
    duration_i = max(0, round(float(duration)))

    if not 0 <= reps_i <= 10000:
        raise ValueError("Invalid reps")
    if not 0 <= sets_i <= 1000:
        raise ValueError("Invalid sets")
    if duration_i > 24 * 60 * 60:
        raise ValueError("Invalid workout duration")

    return name, reps_i, sets_i, duration_i


def init_db() -> None:
    conn = _connect()
    with conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                saas_user_id INTEGER UNIQUE NOT NULL,
                username     TEXT NOT NULL,
                created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS exercises (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id       INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                exercise_name TEXT    NOT NULL,
                reps          INTEGER NOT NULL DEFAULT 0 CHECK(reps >= 0),
                sets          INTEGER NOT NULL DEFAULT 0 CHECK(sets >= 0),
                time          INTEGER NOT NULL DEFAULT 0 CHECK(time >= 0),
                created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_exercises_user_date ON exercises(user_id, created_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_users_saas_id ON users(saas_user_id)")


def get_user_by_saas_id(saas_user_id: int) -> Optional[sqlite3.Row]:
    value = _validate_user_id(saas_user_id)
    return _connect().execute(
        "SELECT id, saas_user_id, username, created_at FROM users WHERE saas_user_id = ?",
        (value,),
    ).fetchone()


def create_user_from_saas(saas_user_id: int, username: str) -> sqlite3.Row:
    value = _validate_user_id(saas_user_id)
    clean_name = str(username or "").strip()[:80]
    if not clean_name:
        raise ValueError("Invalid username")
    conn = _connect()
    with conn:
        conn.execute(
            "INSERT OR IGNORE INTO users (saas_user_id, username) VALUES (?, ?)",
            (value, clean_name),
        )
    user = get_user_by_saas_id(value)
    if user is None:
        raise RuntimeError("Unable to create user")
    return user


def get_or_create_user_from_saas(saas_user_id: int, username: str) -> sqlite3.Row:
    value = _validate_user_id(saas_user_id)
    user = get_user_by_saas_id(value)
    if user is None:
        return create_user_from_saas(value, username)
    return user


def add_exercise(user_id: int, exercise_name: str, reps: int, sets: int, time: float) -> None:
    """Persist only data belonging to the supplied authenticated local user."""
    uid = _validate_user_id(user_id)
    name, reps_i, sets_i, duration_i = _validate_workout(exercise_name, reps, sets, time)
    conn = _connect()

    # Do not create or mutate history for an unknown identity.
    if conn.execute("SELECT 1 FROM users WHERE id = ?", (uid,)).fetchone() is None:
        raise PermissionError("Unknown user")

    with conn:
        existing = conn.execute(
            """
            SELECT id FROM exercises
            WHERE user_id = ? AND exercise_name = ? AND date(created_at, 'localtime') = date('now', 'localtime')
            """,
            (uid, name),
        ).fetchone()

        if existing:
            conn.execute(
                """
                UPDATE exercises
                SET reps = reps + ?, sets = sets + ?, time = time + ?
                WHERE id = ? AND user_id = ?
                """,
                (reps_i, sets_i, duration_i, existing["id"], uid),
            )
        else:
            conn.execute(
                """
                INSERT INTO exercises (user_id, exercise_name, sets, reps, time)
                VALUES (?, ?, ?, ?, ?)
                """,
                (uid, name, sets_i, reps_i, duration_i),
            )


def get_users_exercises(user_id: int):
    uid = _validate_user_id(user_id)
    return _connect().execute(
        """
        SELECT id, exercise_name, reps, sets, time, created_at
        FROM exercises
        WHERE user_id = ?
        ORDER BY created_at DESC, id DESC
        """,
        (uid,),
    ).fetchall()
