import os
from typing import Optional

from services.config.workout_config import PROMPT


LANGUAGE_INSTRUCTIONS = {
    "English": (
        "Respond in natural spoken English. "
        "Be concise, friendly, and conversational like a personal trainer."
    ),
    "Telugu": (
        "Respond in natural spoken Telugu (తెలుగు). "
        "Use simple conversational Telugu suitable for a gym user. "
        "Keep fitness terms in English only when natural."
    ),
    "Hindi": (
        "Respond in natural spoken Hindi (हिन्दी). "
        "Use simple conversational Hindi suitable for a gym user. "
        "Keep fitness terms in English only when natural."
    ),
}


DEFAULT_MODEL = "openai/gpt-oss-20b"


class LLMCoach:

    def __init__(self, groq_client):
        self.client = groq_client
        self.history = []
        self.system_prompt = PROMPT

        self.model = os.getenv(
            "GROQ_MODEL",
            DEFAULT_MODEL
        )

        print(f"[LLM] Groq model: {self.model}")

    # ---------------------------------------------------------
    # Build messages
    # ---------------------------------------------------------

    def _messages(self, prompt: str, language: str):

        language_instruction = LANGUAGE_INSTRUCTIONS.get(
            language,
            LANGUAGE_INSTRUCTIONS["English"]
        )

        system_prompt = (
            f"{self.system_prompt}\n\n"
            f"{language_instruction}\n\n"
            "Important: Keep responses short because they will be spoken aloud."
        )

        return [
            {
                "role": "system",
                "content": system_prompt
            },
            *self.history[-8:],
            {
                "role": "user",
                "content": prompt
            }
        ]

    # ---------------------------------------------------------
    # Groq completion
    # ---------------------------------------------------------

    def _complete(
        self,
        prompt: str,
        language="English",
        max_tokens=120
    ):

        messages = self._messages(
            prompt,
            language
        )

        try:

            response = self.client.chat.completions.create(

                model=self.model,

                messages=messages,

                # GPT-OSS reasoning control
                reasoning_effort="low",

                temperature=0.5,

                # Current Groq parameter
                max_completion_tokens=max_tokens,

                stream=False,
            )

            # -------------------------------------------------
            # Debug information
            # -------------------------------------------------

            if not response.choices:

                print("[LLM] Groq returned ZERO choices.")
                print(response)

                raise RuntimeError(
                    "Groq returned zero choices."
                )

            message = response.choices[0].message

            content = getattr(
                message,
                "content",
                None
            )

            reasoning = getattr(
                message,
                "reasoning",
                None
            )

            print(
                f"[LLM] content length: "
                f"{len(content or '')}"
            )

            if reasoning:
                print(
                    f"[LLM] reasoning received: "
                    f"{len(reasoning)} chars"
                )

            # -------------------------------------------------
            # Final answer
            # -------------------------------------------------

            text = (content or "").strip()

            if not text:

                print(
                    "[LLM] EMPTY CONTENT FROM GROQ"
                )

                print(
                    "[LLM] Full message:"
                )

                print(message)

                raise RuntimeError(
                    "Groq returned empty content."
                )

            # -------------------------------------------------
            # Save conversation
            # -------------------------------------------------

            self.history.append(
                {
                    "role": "user",
                    "content": prompt
                }
            )

            self.history.append(
                {
                    "role": "assistant",
                    "content": text
                }
            )

            self.history = self.history[-20:]

            return text

        except Exception as e:

            print(
                f"[LLM] Groq API Error: {type(e).__name__}: {e}"
            )

            raise

    # ---------------------------------------------------------
    # Workout coaching
    # ---------------------------------------------------------

    def give_feedback(
        self,
        event,
        issue=None,
        language="English",
        context: Optional[dict] = None
    ):

        prompt = f"""
Workout event: {event}
"""

        if issue:

            prompt += f"""
Form issue: {issue}
"""

        if context:

            prompt += f"""
Exercise: {context.get("exercise", "unknown")}
Reps: {context.get("reps", 0)}
Set: {context.get("set", "unknown")}
Form: {context.get("form", "unknown")}
"""

        prompt += """
Give ONE short coaching sentence.

The response will be spoken aloud.

Do not explain your reasoning.
Do not give a long explanation.
Do not mention being an AI.
"""

        try:

            return self._complete(
                prompt,
                language=language,
                max_tokens=80
            )

        except Exception as e:

            print(
                f"[LLM] Feedback failed: {e}"
            )

            return self._fallback(
                language
            )

    # ---------------------------------------------------------
    # Conversational coach
    # ---------------------------------------------------------

    def chat(
        self,
        user_text,
        language="English",
        context=None
    ):

        user_text = (
            user_text or ""
        ).strip()

        if not user_text:

            return ""

        prompt = f"""
The user is speaking during a live AI gym coaching session.

User said:
{user_text}
"""

        if context:

            prompt += f"""

Current workout:
Exercise: {context.get("exercise", "not started")}
Reps: {context.get("reps", 0)}
Set: {context.get("set", "not started")}
Form: {context.get("form", "unknown")}
"""

        prompt += """

Respond like a real personal trainer.

Be warm.
Be natural.
Be concise.
Answer the user's question directly.
If they want motivation, motivate them.
If they ask what to do next, give one clear action.

Maximum 35 spoken words.
"""

        try:

            return self._complete(
                prompt,
                language=language,
                max_tokens=100
            )

        except Exception as e:

            print(
                f"[LLM] Chat failed: {e}"
            )

            return self._fallback(
                language
            )

    # ---------------------------------------------------------
    # Fallback
    # ---------------------------------------------------------

    @staticmethod
    def _fallback(language):

        return {
            "English":
                "Keep going. Stay controlled and focus on your form.",

            "Telugu":
                "కొనసాగించండి. కంట్రోల్‌గా చేసి ఫారమ్‌పై దృష్టి పెట్టండి.",

            "Hindi":
                "जारी रखो। कंट्रोल में रहो और अपने फॉर्म पर ध्यान दो।",

        }.get(
            language,
            "Keep going and focus on your form."
        )

    # ---------------------------------------------------------
    # Reset conversation
    # ---------------------------------------------------------

    def clear_history(self):

        self.history.clear()