from io import BytesIO
from gtts import gTTS

# gTTS language codes for the three supported coaching languages.
LANGUAGE_CODES = {
    "English": "en",
    "Telugu": "te",
    "Hindi": "hi",
}


class TextToSpeech:
    def speak(self, text, lang="en"):
        cleaned = (text or "").strip()

        if not cleaned:
            return None

        buffer = BytesIO()

        gTTS(
            text=cleaned,
            lang=lang,
            slow=False,
        ).write_to_fp(buffer)

        buffer.seek(0)

        return buffer.read()

    def speak_in_language(self, text, language="English"):
        """Convenience wrapper: pass a human-readable language name
        ('English' | 'Telugu' | 'Hindi') instead of a raw gTTS code."""
        lang_code = LANGUAGE_CODES.get(language, "en")
        return self.speak(text, lang=lang_code)