"""Browser speech-to-text + LLM conversational coach."""
from __future__ import annotations
import time
from pathlib import Path
import streamlit as st
import streamlit.components.v1 as components

_COMPONENT = components.declare_component(
    "voice_conversation",
    path=str(Path(__file__).resolve().parents[2] / "components" / "voice_conversation"),
)

def render_voice_input(language="English", key="voice_conversation", auto_start=False):
    # Pass language through the iframe document body.
    lang = {"English":"English","Telugu":"Telugu","Hindi":"Hindi"}.get(language,"English")
    value = _COMPONENT(
        key=key, default=None, language=lang,
        auto_start=bool(auto_start), height=100
    )
    return value

def _language_instruction(language):
    return {
        "English":"Answer naturally in English.",
        "Telugu":"జవాబు సహజమైన మాట్లాడే తెలుగులో మాత్రమే ఇవ్వండి. అవసరమైతే సాధారణ fitness పదాలను మాత్రమే Englishలో ఉంచండి.",
        "Hindi":"जवाब स्वाभाविक बोलचाल की हिन्दी में दें। जरूरत हो तो सामान्य fitness शब्द English में रख सकते हैं।",
    }.get(language, "Answer naturally in English.")

def ask_coach(llm_coach, user_text, language="English", context=None):
    """Use the existing LLM coach for a conversational answer."""
    if not llm_coach or not user_text.strip():
        return ""
    context = context or {}
    prompt = f"""The user is speaking to you during an AI gym coaching session.

User said: {user_text.strip()}

Current workout context:
Exercise: {context.get('exercise','not started')}
Reps: {context.get('reps',0)}
Set: {context.get('set','not started')}
Form status: {context.get('form','unknown')}

{_language_instruction(language)}

Reply like a real personal trainer: warm, concise, useful, and conversational.
If the user asks a question, answer it. If they ask for motivation, motivate them.
If they ask what to do next, give a clear action. Do not pretend to see anything
that is not in the supplied workout context. Keep the spoken answer under 35 words."""
    try:
        return llm_coach.chat(user_text=prompt, language=language)
    except AttributeError:
        # Backward-compatible path for the existing LLMCoach.
        return llm_coach.give_feedback(
            f"Conversation with user: {user_text.strip()}",
            language=language,
        )
