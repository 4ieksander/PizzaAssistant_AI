import speech_recognition as sr

def recognize_speech():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        print("Powiedz coś...")
        audio = recognizer.listen(source)

    try:
        text = recognizer.recognize_google(audio, language="pl-PL")
        return text
    except sr.UnknownValueError:
        return "Nie rozpoznano mowy."
    except sr.RequestError as e:
        return f"Błąd usługi Google: {e}"
