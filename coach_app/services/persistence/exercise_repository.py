import sqlite3
import streamlit as st
from pathlib import Path

_DB_PATH = str(Path(__file__).parent.parent.parent / "data.db")


@st.cache_resource
def _get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(_DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = _get_connection()

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
                user_id       INTEGER NOT NULL REFERENCES users(id),
                exercise_name TEXT    NOT NULL,
                reps          INTEGER NOT NULL DEFAULT 0,
                sets          INTEGER NOT NULL DEFAULT 0,
                time          INTEGER NOT NULL DEFAULT 0,
                created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )


def get_user_by_saas_id(saas_user_id: int) -> sqlite3.Row:
    conn = _get_connection()
    return conn.execute(
        "SELECT * FROM users WHERE saas_user_id = ?", (saas_user_id,)
    ).fetchone()


def create_user_from_saas(saas_user_id: int, username: str) -> sqlite3.Row:
    conn = _get_connection()
    with conn:
        conn.execute(
            "INSERT INTO users (saas_user_id, username) VALUES (?, ?)",
            (saas_user_id, username),
        )
    return get_user_by_saas_id(saas_user_id)


def get_or_create_user_from_saas(saas_user_id: int, username: str) -> sqlite3.Row:
    """Maps a user authenticated via the SaaS backend to a local row in this
    app's own database, so workout history can be tied to a stable local id
    even if the central SaaS DB lives elsewhere."""
    user = get_user_by_saas_id(saas_user_id)
    if user is None:
        user = create_user_from_saas(saas_user_id, username)
    return user


def add_exercise(user_id, exercise_name, reps, sets, time):
    conn = _get_connection()

    with conn:
        existing = conn.execute("""
            SELECT * FROM exercises
            WHERE user_id = ? AND exercise_name = ? AND Date(created_at) = Date('now')
        """, (user_id, exercise_name)).fetchone()

        if existing:
            conn.execute("""
                UPDATE exercises
                SET reps = reps + ?, sets = sets + ?, time = time + ?
                WHERE id = ?
            """, (reps, sets, time, existing['id']))
        else:
            conn.execute("""
                INSERT INTO exercises (user_id, exercise_name, sets, reps, time)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, exercise_name, sets, reps, time))


def get_users_exercises(user_id):
    conn = _get_connection()

    return conn.execute("""
        SELECT * FROM exercises
        WHERE user_id = ?
    """, (user_id,)).fetchall()
