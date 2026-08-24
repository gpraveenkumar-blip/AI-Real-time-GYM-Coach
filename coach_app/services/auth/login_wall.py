import streamlit as st

def render_login_wall() -> bool:
    """Coach app is opened from the frontend; no account server is required."""
    if st.session_state.get("coach_app_ready"):
        return True
    st.session_state["coach_app_ready"] = True
    st.session_state.setdefault("username", "coach-user")
    return True
