from services.config.workout_config import PROMPT

LANGUAGE_INSTRUCTIONS = {
    "English": "Respond in English.",
    "Telugu": "Respond entirely in Telugu (తెలుగు), using natural spoken Telugu a gym-goer would understand. Do not mix in English sentences.",
    "Hindi": "Respond entirely in Hindi (हिन्दी), using natural spoken Hindi a gym-goer would understand. Do not mix in English sentences.",
}


class LLMCoach:
    def __init__(self, groq_client):
        self.client = groq_client
        self.history = []
        self.system_prompt = PROMPT

    def give_feedback(self, event, issue=None, language="English"):
        prompt = f"Event: {event}"

        if issue:
            prompt += f"\nForm Issue: {issue}"

        language_instruction = LANGUAGE_INSTRUCTIONS.get(language, LANGUAGE_INSTRUCTIONS["English"])
        system_prompt = f"{self.system_prompt}\n\n{language_instruction}"

        messages = [
            {"role": "system", "content": system_prompt},
            *self.history[-10:],
            {"role": "user", "content": prompt},
        ]

        try:
            response = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=messages,
                temperature=0.4,
                max_tokens=150,
            )

            text = response.choices[0].message.content.strip()

            # Save conversation history
            self.history.append({"role": "user", "content": prompt})
            self.history.append({"role": "assistant", "content": text})

            return text

        except Exception as e:
            print(f"Groq API Error: {e}")
            fallback = {
                "English": "Sorry, I'm unable to generate feedback right now.",
                "Telugu": "క్షమించండి, ప్రస్తుతం నేను ఫీడ్‌బ్యాక్ ఇవ్వలేకపోతున్నాను.",
                "Hindi": "क्षमा करें, अभी मैं फीडबैक नहीं दे पा रहा हूँ।",
            }
            return fallback.get(language, fallback["English"])