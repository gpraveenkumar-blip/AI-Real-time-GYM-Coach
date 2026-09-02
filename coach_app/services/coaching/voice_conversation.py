"""Browser speech-to-text input + LLM conversational gym coach."""

from __future__ import annotations

from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components


_COMPONENT = components.declare_component(
    "voice_conversation",
    path=str(Path(__file__).resolve().parents[2] / "components" / "voice_conversation"),
)


def render_voice_input(language="English", key="voice_conversation", auto_start=False):
    lang = {
        "English": "English",
        "Telugu": "Telugu",
        "Hindi": "Hindi",
    }.get(language, "English")

    value = _COMPONENT(
        key=key,
        default=None,
        language=lang,
        auto_start=bool(auto_start),
        height=100,
    )
    return value


def _language_instruction(language):
    return {
        "English": "Answer naturally in English.",
        "Telugu": (
            "జవాబు సహజమైన మాట్లాడే తెలుగులో మాత్రమే ఇవ్వండి. "
            "అవసరమైతే సాధారణ fitness పదాలను మాత్రమే Englishలో ఉంచండి."
        ),
        "Hindi": (
            "जवाब स्वाभाविक बोलचाल की हिन्दी में दें। "
            "जरूरत हो तो सामान्य fitness शब्द English में रख सकते हैं."
        ),
    }.get(language, "Answer naturally in English.")


def ask_coach(llm_coach, user_text, language="English", context=None):
    """Generate a short spoken answer from the user's voice transcript."""
    user_text = (user_text or "").strip()

    if not llm_coach or not user_text:
        return ""

    context = context or {}

    # Preferred API: LLMCoach.chat()
    try:
        return llm_coach.chat(
            user_text=user_text,
            language=language,
            context=context,
        )
    except AttributeError:
        pass
    except Exception as e:
        print(f"Conversation LLM error: {e}")
        return ""

    # Backward compatibility for older LLMCoach implementations.
    prompt = f"""The user is speaking during an AI gym coaching session.

User said: {user_text}

Current workout context:
Exercise: {context.get('exercise', 'not started')}
Reps: {context.get('reps', 0)}
Set: {context.get('set', 'not started')}
Form status: {context.get('form', 'unknown')}

{_language_instruction(language)}

Reply like a real personal trainer: warm, concise, useful, and conversational.
Keep the spoken answer under 35 words."""

    try:
        return llm_coach.give_feedback(
            event=f"Conversation with user: {user_text}",
            language=language,
            context=context,
        )
    except Exception as e:
        print(f"Conversation fallback error: {e}")
        return ""
