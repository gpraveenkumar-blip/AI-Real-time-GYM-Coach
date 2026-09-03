"""Synchronize vision metrics with the Streamlit workout session."""
from __future__ import annotations

import math
import time

import streamlit as st

from services.config.workout_config import METRICS_FIELDS
from services.persistence.exercise_repository import add_exercise


def _safe_int(value, default=0, minimum=0, maximum=100000):
    try:
        number = int(value)
    except (TypeError, ValueError):
        return default
    return max(minimum, min(number, maximum))


def sync_metrics_update(context):
    if not context or not getattr(getattr(context, "state", None), "playing", False):
        return

    processor = getattr(context, "video_processor", None)
    if processor is None:
        return

    exercise = st.session_state.get("exercise_type")
    if not exercise:
        return

    processor.set_exercise(exercise)
    latest_metrics = processor.get_latest_metrics()
    if not latest_metrics:
        return

    reps = _safe_int(latest_metrics.get("reps"), 0, 0, 10000)
    st.session_state.reps = reps

    fields = METRICS_FIELDS.get(exercise, {})
    for key, default in fields.items():
        value = latest_metrics.get(key, default)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            value = max(-100000.0, min(100000.0, float(value)))
        st.session_state[key] = value

    reps_per_set = _safe_int(st.session_state.get("reps_per_set"), 0, 1, 1000)
    target_sets = _safe_int(st.session_state.get("target_sets"), 0, 1, 100)

    if reps_per_set and target_sets:
        sets_completed = min(reps // reps_per_set, target_sets)
        current_set_reps = min(reps % reps_per_set, reps_per_set - 1)
        workout_completed = reps >= reps_per_set * target_sets
    else:
        sets_completed = current_set_reps = 0
        workout_completed = False

    st.session_state.sets_completed = sets_completed
    st.session_state.current_set_reps = current_set_reps
    st.session_state.workout_completed = workout_completed

    last_saved_sets = _safe_int(
        st.session_state.get("last_saved_sets_completed"), 0, 0, target_sets or 100
    )

    if target_sets and reps_per_set and sets_completed > last_saved_sets:
        newly_completed = sets_completed - last_saved_sets
        now_ts = time.time()
        started_at = float(st.session_state.get("set_cycle_started_at") or now_ts)
        time_taken = max(0.0, min(now_ts - started_at, 24 * 60 * 60))
        user_id = st.session_state.get("user_id")

        if isinstance(user_id, int) and user_id > 0:
            add_exercise(
                user_id,
                exercise,
                newly_completed * reps_per_set,
                newly_completed,
                time_taken,
            )

        if st.session_state.get("voice_pipeline"):
            result = st.session_state.voice_pipeline.process_event(
                event="set_completed",
                exercise=exercise,
                metrics=latest_metrics,
                language=st.session_state.get("coach_language", "English"),
            )
            if result:
                st.session_state.audio_to_play, st.session_state.coach_feedback = result

        st.session_state.set_cycle_started_at = now_ts
        st.session_state.last_saved_sets_completed = sets_completed

    if workout_completed and st.session_state.get("workout_started"):
        st.session_state.workout_started = False
        if st.session_state.get("voice_pipeline"):
            result = st.session_state.voice_pipeline.process_event(
                event="workout_completed",
                exercise=exercise,
                metrics=latest_metrics,
                language=st.session_state.get("coach_language", "English"),
            )
            if result:
                st.session_state.audio_to_play, st.session_state.coach_feedback = result

    pose_detected = bool(latest_metrics.get("pose_detected", True))
    pipeline = st.session_state.get("voice_pipeline")
    if pipeline and not workout_completed:
        if not pose_detected:
            result = pipeline.process_event(
                event="no_pose_detected",
                exercise=exercise,
                metrics={"issue": "No pose detected. Please step into the camera frame."},
                language=st.session_state.get("coach_language", "English"),
            )
        else:
            result = pipeline.process_event(
                event="ongoing_form_check",
                exercise=exercise,
                metrics=latest_metrics,
                language=st.session_state.get("coach_language", "English"),
            )
        if result:
            st.session_state.audio_to_play, st.session_state.coach_feedback = result
