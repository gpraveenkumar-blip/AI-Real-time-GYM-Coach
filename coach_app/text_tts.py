from services.coaching.tts import TextToSpeech

tts = TextToSpeech()

audio = tts.speak("Hello Praveen")

print(type(audio))
print(len(audio))