import streamlit as st
import os
import time
import pandas as pd
from dotenv import load_dotenv
from groq import Groq

from services.auth.login_wall import render_login_wall
from services.state.session_defaults import initial_session_defaults
from services.config.workout_config import EXERCISE_OPTIONS, LIBRARY_EXERCISE_OPTIONS, ALL_TRACKABLE_EXERCISES, METRICS_FIELDS, HOLD_BASED_EXERCISES
from services.config.exercise_library import EXERCISE_LIBRARY, DIFFICULTY_LEVELS
from services.ui.style_loader import load_css, inject_local_font, inject_webrtc_styles
from services.persistence.exercise_repository import init_db, get_users_exercises
from services.vision.exercise_video_processor import VideoProcessorClass
from services.tracking.metrics import sync_metrics_update
from services.coaching.llm import LLMCoach
from services.coaching.tts import TextToSpeech
from services.coaching.voice_pipeline import VoicePipeline, autoplay_audio
from streamlit_webrtc import webrtc_streamer, WebRtcMode


def _apply_recommended_volume():
    """on_click callback for the sidebar 'Use Recommended' button — sets
    plan_sets/plan_reps in session_state *before* the widgets are
    instantiated on the rerun, so they pick up the new values."""
    level = st.session_state.get("experience_level", "Intermediate")
    rec = DIFFICULTY_LEVELS[level]
    st.session_state.plan_sets = rec["recommended_sets"]
    st.session_state.plan_reps = rec["recommended_reps"]


def _select_exercise_for_tracking(group_name, exercise_name):
    """on_click callback for a library card's 'Track This' button — pre-
    selects the exercise in the sidebar's Workout Plan so the person can
    scroll up and hit Start Workout immediately."""
    st.session_state.plan_muscle_group = group_name
    st.session_state.plan_exercise = exercise_name


@st.cache_data
def _load_exercise_image_data_uri(exercise_name: str):
    """Loads the high-resolution exercise-library photo as a base64 data URI."""
    import base64

    slug = exercise_name.lower().replace(" ", "_").replace("/", "").replace("-", "_").replace("__", "_")
    path = os.path.join(os.getcwd(), "static", "exercise_library", f"{slug}.webp")

    try:
        with open(path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode("utf-8")
        return f"data:image/webp;base64,{encoded}"
    except FileNotFoundError:
        return None


def main():
    st.set_page_config(
        page_icon="🏋️‍♀️",
        page_title="AI Real-time GYM Coach",
        initial_sidebar_state="expanded",
        layout="centered"
    )

    load_css(os.path.join(os.getcwd(), "static", "style.css"))
    inject_local_font(os.path.join(os.getcwd(), "static", "AdobeClean.otf"), "AdobeClean")

    init_db()
    # Require a valid account session before opening the coach.
    if not render_login_wall():
        return

    initial_session_defaults()

    if "voice_pipeline" not in st.session_state:
        try:
            load_dotenv()
            api_key = os.environ.get("GROQ_API_KEY", "")

            if not api_key and hasattr(st, "secrets") and "GROQ_API_KEY" in st.secrets:
                api_key = st.secrets["GROQ_API_KEY"]

            groq_client = Groq(api_key=api_key)
            llm_coach = LLMCoach(groq_client)
            tts = TextToSpeech()
            st.session_state.voice_pipeline = VoicePipeline(llm_coach, tts)
        except Exception:
            st.session_state.voice_pipeline = None

    workout_started = st.session_state.get("workout_started", False)

    with st.sidebar:
        st.title("🏋️‍♂️ Apna AI Coach")

        if st.session_state.username:
            st.caption(f"👤 Logged in as {st.session_state.username}")

        st.divider()

        st.subheader("Coach Language")
        st.session_state.coach_language = st.selectbox(
            "Voice & feedback language",
            options=["English", "Telugu", "Hindi"],
            index=["English", "Telugu", "Hindi"].index(st.session_state.get("coach_language", "English")),
            label_visibility="collapsed",
        )

        st.divider()

        st.subheader("Experience Level")
        level_options = list(DIFFICULTY_LEVELS.keys())
        st.session_state.experience_level = st.selectbox(
            "Experience level",
            options=level_options,
            index=level_options.index(st.session_state.get("experience_level", "Intermediate")),
            label_visibility="collapsed",
        )
        _level_info = DIFFICULTY_LEVELS[st.session_state.experience_level]
        st.markdown(
            f"""<div class="volume-banner">
                <span class="volume-text">{_level_info['sets_range']} × {_level_info['reps_range']}</span>
                <span class="level-badge {_level_info['badge_class']}">{st.session_state.experience_level}</span>
            </div>""",
            unsafe_allow_html=True,
        )

        st.divider()

        st.subheader("Workout Plan")

        if not workout_started:
            _muscle_group = st.selectbox(
                "Muscle group",
                options=["⭐ Original 5"] + list(LIBRARY_EXERCISE_OPTIONS.keys()),
                key="plan_muscle_group",
            )
            _group_options = (
                EXERCISE_OPTIONS if _muscle_group == "⭐ Original 5"
                else LIBRARY_EXERCISE_OPTIONS[_muscle_group]
            )
            plan_exercise = st.selectbox("Exercise", options=_group_options, key="plan_exercise")
            plan_sets = st.number_input("Sets", min_value=0, max_value=50, key="plan_sets", step=1)
            plan_reps = st.number_input("Reps per Set", min_value=0, max_value=50, key="plan_reps", step=1)

            if plan_exercise in HOLD_BASED_EXERCISES:
                st.caption("⏱️ Hold-based exercise — 'Reps' here means seconds held.")

            st.button(
                f"Use Recommended ({_level_info['recommended_sets']} × {_level_info['recommended_reps']})",
                width="stretch", key="apply_recommended_button",
                on_click=_apply_recommended_volume,
            )

            st.markdown("")

            start_session_button = st.button("Start Workout", width="stretch", key="start_session_button")

            if start_session_button:
                st.session_state.exercise_type = plan_exercise
                st.session_state.target_sets = int(plan_sets)
                st.session_state.reps_per_set = int(plan_reps)
                st.session_state.reps = 0
                st.session_state.workout_started = True
                st.session_state.set_cycle_started_at = time.time()
                st.session_state.last_saved_sets_completed = 0

                if st.session_state.voice_pipeline:
                    result = st.session_state.voice_pipeline.process_event(
                        event="workout_started",
                        exercise=plan_exercise,
                        metrics={},
                        language=st.session_state.get("coach_language", "English"),
                    )
                    if result:
                        st.session_state.audio_to_play, st.session_state.coach_feedback = result

                st.session_state.last_notified_sets_completed = 0
                st.session_state.last_notified_workout_complete = False
                st.rerun()
        else:
            exercise = st.session_state.get("exercise_type")
            sets = st.session_state.get("target_sets")
            reps = st.session_state.get("reps_per_set")

            st.info(f"**{exercise}** -- {sets} Sets / {reps} Reps")

            end_session_button = st.button("End Workout", key="end_session_button", width="stretch")

            if end_session_button:
                st.session_state.workout_started = False

                if st.session_state.voice_pipeline:
                    result = st.session_state.voice_pipeline.process_event(
                        event="workout_completed",
                        exercise=exercise,
                        metrics={},
                        language=st.session_state.get("coach_language", "English"),
                    )
                    if result:
                        st.session_state.audio_to_play, st.session_state.coach_feedback = result

                st.rerun()

        if workout_started:
            st.divider()

            exercise = st.session_state.get("exercise_type")
            total_reps = st.session_state.get("reps")
            current_set_reps = st.session_state.get("current_set_reps")
            reps_per_set = st.session_state.get("reps_per_set")
            sets_completed = st.session_state.get("sets_completed")
            target_sets = st.session_state.get("target_sets")

            is_hold_exercise = exercise in HOLD_BASED_EXERCISES
            reps_label = "Total Seconds Held" if is_hold_exercise else "Total Reps"
            current_label = "Seconds This Set" if is_hold_exercise else "Current Set Reps"

            st.subheader("Progress")

            st.metric(reps_label, f"{total_reps}")
            st.metric(current_label, f"{current_set_reps} / {reps_per_set}")
            st.metric("Sets Completed", f"{sets_completed} / {target_sets}")

            st.divider()

            st.subheader(f"{exercise} Metrics")
            fields = METRICS_FIELDS.get(exercise, {})
            for field_key, default in fields.items():
                value = st.session_state.get(field_key, default)
                label = field_key.replace("_", " ").title()
                if isinstance(value, (int, float)) and "angle" in field_key:
                    st.metric(label, f"{value}°")
                else:
                    st.metric(label, value)

    _status_class = "live" if workout_started else ""
    _status_text = "LIVE SESSION" if workout_started else "IDLE"
    st.markdown(
        f"""<div class="hud-topbar">
            <div>
                <div class="hud-title">AI Real-time GYM Coach</div>
                <div class="hud-sub">Real-time pose detection with proactive AI voice coaching</div>
            </div>
            <span class="hud-status-pill {_status_class}"><span class="hud-dot"></span>{_status_text}</span>
        </div>""",
        unsafe_allow_html=True,
    )

    if st.session_state.get("audio_to_play"):
        autoplay_audio(st.session_state.audio_to_play)

    if st.session_state.get("coach_feedback"):
        st.markdown("")
        st.success(f"🤖 **Coach:** {st.session_state.coach_feedback}")

    if not workout_started:
        st.markdown(
            """
            <div class="hud-ready">
                <h2>👈 Set your workout plan</h2>
                <p>
                    Choose your exercise, sets and reps in the sidebar —<br>
                    or tap <strong>Use Recommended</strong> for your experience level —<br>
                    then click <strong>Start Workout</strong> to activate the camera and AI coach.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        context = webrtc_streamer(
            key="exercise-analysis",
            mode=WebRtcMode.SENDRECV,
            video_processor_factory=VideoProcessorClass,
            rtc_configuration={"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]},
            media_stream_constraints={
                "video": True,
                "audio": False
            },
            async_processing=True
        )

        sync_metrics_update(context)

        if context.state.playing:
            time.sleep(0.25)
            st.rerun()

        inject_webrtc_styles()

    st.divider()
    st.markdown("#### Workout History")

    user_id = st.session_state.get("user_id", 0)

    if isinstance(user_id, int):
        history_rows = get_users_exercises(user_id)

        arr = [
            {
                "Exercise": row['exercise_name'],
                "Reps": row['reps'],
                "Sets": row['sets'],
                "Time (sec)": row['time'],
                "Date": row['created_at']
            }
            for row in history_rows
        ]

        df = pd.DataFrame(arr)

        if not df.empty:
            df["Date"] = pd.to_datetime(df["Date"]).dt.date
            agg_df = df.groupby(["Exercise", "Date"]).agg({
                "Reps": 'sum',
                "Sets": "sum",
                "Time (sec)": "sum"
            }).reset_index()
            agg_df.index += 1
            st.table(agg_df, border="horizontal")
        else:
            st.info("No workout history found.")

    st.divider()

    _level = st.session_state.get("experience_level", "Intermediate")
    _level_info = DIFFICULTY_LEVELS[_level]

    st.markdown('<div class="exlib-section-title">📚 Exercise Library</div>', unsafe_allow_html=True)
    st.markdown(
        f"""<div class="exlib-section-note">
            📸 High-quality home-workout photos for all 28 exercises —
            pick one and tap <strong>Track This</strong> to load it into
            Workout Plan above. Sets/reps shown for your current experience
            level: <span class="level-badge {_level_info['badge_class']}">{_level}</span>
            ({_level_info['sets_range']} × {_level_info['reps_range']}).
            These images are visual exercise references; live AI tracking
            availability is determined by the current workout processor.
        </div>""",
        unsafe_allow_html=True,
    )

    for group_name, group_data in EXERCISE_LIBRARY.items():
        with st.expander(f"{group_data['emoji']}  {group_name}"):
            st.markdown(
                f"""<div class="volume-banner">
                    <span class="volume-text">{_level_info['sets_range']} × {_level_info['reps_range']}</span>
                    <span class="level-badge {_level_info['badge_class']}">{_level}</span>
                </div>""",
                unsafe_allow_html=True,
            )

            cols = st.columns(4)
            for i, exercise_name in enumerate(group_data["exercises"]):
                with cols[i % 4]:
                    data_uri = _load_exercise_image_data_uri(exercise_name)
                    if data_uri:
                        st.markdown(
                            f'<div class="exlib-image-wrap">'
                            f'<img src="{data_uri}" class="exlib-exercise-image" '
                            f'alt="{exercise_name} exercise demonstration"/>'
                            f'</div>',
                            unsafe_allow_html=True,
                        )
                    st.caption(exercise_name)
                    st.button(
                        "Track This", key=f"track_{group_name}_{exercise_name}",
                        width="stretch",
                        on_click=_select_exercise_for_tracking,
                        args=(group_name, exercise_name),
                    )


if __name__ == "__main__":
    main()
