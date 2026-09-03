
"""Authentication gate for the standalone Streamlit coach.

The coach accepts either:
1. a trusted identity already established in Streamlit session state, or
2. a short-lived HMAC-signed SSO handoff from the AI-GYM account portal.

Arbitrary URL parameters are never accepted as identity. For local
development only, AI_GYM_DEMO_AUTH=1 can enable the demo account.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import re
import time
from pathlib import Path

from dotenv import load_dotenv
import streamlit as st

from services.persistence.exercise_repository import get_or_create_user_from_saas


_SSO_MAX_TTL = 300  # five minutes
_USER_ID_RE = r"^[1-9][0-9]{0,18}$"

# Resolve configuration from the repository root, independent of the launch directory.
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(_PROJECT_ROOT / ".env", override=False)


def _query_params():
    """Return Streamlit query parameters across supported Streamlit versions."""
    try:
        return st.query_params
    except AttributeError:
        try:
            return st.experimental_get_query_params()
        except AttributeError:
            return {}


def _first_param(params, key: str) -> str:
    value = params.get(key, "")
    if isinstance(value, list):
        value = value[0] if value else ""
    return str(value or "").strip()


def _consume_sso_handoff() -> tuple[int, str] | None:
    """Validate the portal's signed, short-lived coach handoff.

    Required parameters:
        coach_user_id, coach_username, coach_exp, coach_sig

    Signature payload:
        coach_user_id:coach_username:coach_exp

    The signing secret must be shared only between the account portal
    backend and the coach backend. No secret is accepted from the URL.
    """
    secret = os.getenv("AI_GYM_SSO_SECRET", "").strip()
    if not secret:
        return None

    params = _query_params()
    raw_user_id = _first_param(params, "coach_user_id")
    username = _first_param(params, "coach_username")
    raw_exp = _first_param(params, "coach_exp")
    signature = _first_param(params, "coach_sig")

    if not (raw_user_id and username and raw_exp and signature):
        return None
    if not re.fullmatch(_USER_ID_RE, raw_user_id):
        return None
    if len(username) > 80 or any(ord(c) < 32 for c in username):
        return None

    try:
        user_id = int(raw_user_id)
        expires_at = int(raw_exp)
    except ValueError:
        return None

    now = int(time.time())
    if expires_at < now or expires_at > now + _SSO_MAX_TTL:
        return None

    payload = f"{user_id}:{username}:{expires_at}".encode("utf-8")
    expected = hmac.new(
        secret.encode("utf-8"),
        payload,
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(signature, expected):
        return None

    # Establish the authenticated Streamlit session and remove the
    # one-time credentials from the visible URL after validation.
    user = get_or_create_user_from_saas(user_id, username)
    st.session_state["saas_user_id"] = user_id
    st.session_state["user_id"] = int(user["id"])
    st.session_state["username"] = str(user["username"])
    st.session_state["coach_authenticated_at"] = now

    try:
        st.query_params.clear()
    except Exception:
        try:
            st.experimental_set_query_params()
        except Exception:
            pass

    return user_id, str(user["username"])


def _render_portal_link():
    portal_url = os.getenv("AI_GYM_ACCOUNT_PORTAL_URL", "").strip()
    if portal_url.startswith(("https://", "http://localhost", "http://127.0.0.1")):
        st.link_button("Sign in / Create AI-GYM account", portal_url, use_container_width=True)
    else:
        st.info(
            "Sign in through the AI-GYM account portal, then open Coach from your dashboard."
        )


def render_login_wall() -> bool:
    # First, accept a server-generated, signed SSO handoff.
    try:
        handoff = _consume_sso_handoff()
    except (ValueError, PermissionError, RuntimeError):
        handoff = None
    if handoff:
        return True

    # Preferred: identity established by the authenticated SaaS integration.
    saas_user_id = st.session_state.get("saas_user_id")
    username = str(st.session_state.get("username") or "").strip()
    if isinstance(saas_user_id, int) and saas_user_id > 0 and username:
        try:
            user = get_or_create_user_from_saas(saas_user_id, username)
            st.session_state["user_id"] = int(user["id"])
            st.session_state["username"] = str(user["username"])
            return True
        except (ValueError, PermissionError, RuntimeError):
            st.error("We could not establish your secure coach session.")
            return False

    # Existing local session from a prior authenticated handoff.
    user_id = st.session_state.get("user_id")
    if isinstance(user_id, int) and user_id > 0 and username:
        return True

    # Local development only. Production should never enable this.
    if os.getenv("AI_GYM_DEMO_AUTH", "").strip().lower() in {"1", "true", "yes"}:
        st.session_state["user_id"] = 1
        st.session_state["username"] = "demo-user"
        try:
            get_or_create_user_from_saas(1, "demo-user")
        except Exception:
            st.error("Demo authentication could not initialize.")
            return False
        return True

    st.error("Please sign in through the AI-GYM Coach account portal before opening the coach.")
    _render_portal_link()
    st.caption(
        "If you are developing locally, set AI_GYM_DEMO_AUTH=1. "
        "Do not enable demo authentication in production."
    )
    return False
