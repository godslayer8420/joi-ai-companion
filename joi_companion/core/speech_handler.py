import vosk
import json
import pyaudio
import pyttsx3
import os
import re


def _find_preferred_voice(voices):
    """
    Select Aurion's preferred voice from the installed SAPI voices.
    Priority:
      1. AURION_TTS_VOICE env var (partial name match, case-insensitive)
      2. Aria (Natural / Online) — installed via MSIX
      3. Jenny (Natural / Online) — installed via MSIX
      4. Any English feminine voice
      5. First available voice (fallback)
    """
    env_pref = str(os.getenv("AURION_TTS_VOICE", "")).strip().lower()
    names = [str(getattr(v, "name", "")).lower() for v in voices]

    # 1. Honour explicit env preference
    if env_pref:
        for i, name in enumerate(names):
            if env_pref in name:
                return voices[i].id

    # 2. Aria (preferred — warm, feminine, natural)
    for i, name in enumerate(names):
        if "aria" in name:
            return voices[i].id

    # 3. Jenny
    for i, name in enumerate(names):
        if "jenny" in name:
            return voices[i].id

    # 4. Any English feminine voice
    feminine_keywords = ("zira", "helen", "female", "hazel", "cortana", "eva", "susan", "linda", "jessica")
    for i, name in enumerate(names):
        if any(k in name for k in feminine_keywords):
            return voices[i].id

    # 5. fallback
    return voices[0].id if voices else None


class SpeechHandler:
    def __init__(self, model_path):
        self.model = vosk.Model(model_path)
        self.recognizer = vosk.KaldiRecognizer(self.model, 16000)
        
        self.audio_interface = pyaudio.PyAudio()
        self.stream = self.audio_interface.open(format=pyaudio.paInt16,
                                                 channels=1,
                                                 rate=16000,
                                                 input=True,
                                                 frames_per_buffer=8192)
        
        self.tts_engine = pyttsx3.init()
        voices = self.tts_engine.getProperty('voices')
        preferred_id = _find_preferred_voice(voices) if voices else None
        if preferred_id:
            self.tts_engine.setProperty('voice', preferred_id)
        self.tts_engine.setProperty('rate', 145)  # slightly slower = more warmth


    def speak(self, text):
        self.tts_engine.say(text)
        self.tts_engine.runAndWait()

    def listen(self):
        while True:
            data = self.stream.read(4096, exception_on_overflow=False)
            if self.recognizer.AcceptWaveform(data):
                result = self.recognizer.Result()
                result_dict = json.loads(result)
                return result_dict.get("text", "")
            
                if len(text.split()) > 1:
                    return text
                else:
                    self.recognizer.Reset()

    def stop(self):
        self.stream.stop_stream()
        self.stream.close()
        self.audio_interface.terminate()