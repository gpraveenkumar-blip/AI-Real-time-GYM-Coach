
import hashlib
import hmac
import os
import time

import services.auth.login_wall as login_wall


class FakeParams(dict):
    pass


def _sig(user_id, username, exp, secret):
    payload = f"{user_id}:{username}:{exp}".encode()
    return hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()


def test_signed_handoff_is_accepted(monkeypatch):
    secret = "test-secret"
    exp = int(time.time()) + 60
    monkeypatch.setenv("AI_GYM_SSO_SECRET", secret)
    monkeypatch.setattr(
        login_wall.st,
        "query_params",
        FakeParams(
            coach_user_id=str(7),
            coach_username="alice",
            coach_exp=str(exp),
            coach_sig=_sig(7, "alice", exp, secret),
        ),
        raising=False,
    )
    class FakeState(dict):
        pass
    monkeypatch.setattr(login_wall.st, "session_state", FakeState(), raising=False)
    monkeypatch.setattr(
        login_wall,
        "get_or_create_user_from_saas",
        lambda uid, name: {"id": 11, "username": name},
    )
    result = login_wall._consume_sso_handoff()
    assert result == (7, "alice")
    assert login_wall.st.session_state["user_id"] == 11


def test_unsigned_handoff_is_rejected(monkeypatch):
    monkeypatch.setenv("AI_GYM_SSO_SECRET", "test-secret")
    monkeypatch.setattr(
        login_wall.st,
        "query_params",
        FakeParams(
            coach_user_id="7",
            coach_username="alice",
            coach_exp=str(int(time.time()) + 60),
            coach_sig="bad",
        ),
        raising=False,
    )
    assert login_wall._consume_sso_handoff() is None


def test_expired_handoff_is_rejected(monkeypatch):
    secret = "test-secret"
    exp = int(time.time()) - 1
    monkeypatch.setenv("AI_GYM_SSO_SECRET", secret)
    monkeypatch.setattr(
        login_wall.st,
        "query_params",
        FakeParams(
            coach_user_id="7",
            coach_username="alice",
            coach_exp=str(exp),
            coach_sig=_sig(7, "alice", exp, secret),
        ),
        raising=False,
    )
    assert login_wall._consume_sso_handoff() is None
