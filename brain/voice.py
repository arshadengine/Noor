"""
brain/voice.py
─────────────────────────────────────────────────────
Noor's Voice Engine.

Handles Text-to-Speech (TTS) using edge-tts (Premium neural)
with pyttsx3 (SAPI5) as a local offline fallback.
Handles Speech-to-Text (STT) using SpeechRecognition.
"""

from __future__ import annotations

import os
import asyncio
import re
import uuid
from pathlib import Path
import speech_recognition as sr
import pyttsx3

# Neural voice identifiers for edge-tts
# Neerja (Indian English female) handles Hinglish words beautifully
VOICE_EN = "en-IN-NeerjaNeural"
# Madhur (Hindi male) is perfect for Devanagari text
VOICE_HI = "hi-IN-MadhurNeural"


def is_hindi(text: str) -> bool:
    """Check if the text contains Devanagari characters."""
    return bool(re.search(r'[\u0900-\u097F]', text))


async def _speak_edge_tts(text: str, output_path: str, voice: str) -> None:
    import edge_tts
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_path)


def speak_text(text: str, output_path: str = None) -> str:
    """
    Synthesize text to speech (MP3).
    Saves to a temporary file and returns the file path.
    """
    if not output_path:
        temp_dir = Path("D:/Noor/data/temp_audio")
        temp_dir.mkdir(parents=True, exist_ok=True)
        output_path = str(temp_dir / f"response_{uuid.uuid4().hex}.mp3")

    # Clean text: remove emojis, markdown symbols, and code block indicators for cleaner speech
    clean_text = re.sub(r'[*#_`~\[\]()]', ' ', text)
    clean_text = re.sub(r'https?://\S+', 'link', clean_text)
    # Remove large code blocks entirely as speaking code out loud is verbose
    clean_text = re.sub(r'```.*?```', '[code block omitted]', clean_text, flags=re.DOTALL)
    clean_text = clean_text.strip()

    if not clean_text:
        return ""

    # Select appropriate voice
    voice = VOICE_HI if is_hindi(clean_text) else VOICE_EN

    try:
        # Execute edge-tts in a new event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(_speak_edge_tts(clean_text, output_path, voice))
            print(f"[Noor Voice] TTS generated via edge-tts ({voice}): {output_path}")
            return output_path
        finally:
            loop.close()
    except Exception as e:
        print(f"[Noor Voice] edge-tts failed: {e}. Falling back to offline pyttsx3...")
        
        # Offline fallback using pyttsx3 (native Windows SAPI5)
        try:
            engine = pyttsx3.init()
            voices = engine.getProperty('voices')
            
            # Select Indian voice if available on system
            selected_voice = None
            for v in voices:
                if "india" in v.name.lower() or "hindi" in v.name.lower():
                    selected_voice = v.id
                    break
            
            if selected_voice:
                engine.setProperty('voice', selected_voice)
                
            wav_path = str(Path(output_path).with_suffix(".wav"))
            engine.save_to_file(clean_text, wav_path)
            engine.runAndWait()
            print(f"[Noor Voice] TTS generated via pyttsx3 (SAPI5): {wav_path}")
            return wav_path
        except Exception as fallback_err:
            print(f"[Noor Voice] Offline TTS fallback failed: {fallback_err}")
            return ""


def transcribe_audio(audio_path: str) -> str:
    """
    Transcribe a recorded WAV file into text using SpeechRecognition.
    """
    r = sr.Recognizer()
    try:
        with sr.AudioFile(audio_path) as source:
            # Adjust for ambient noise to improve accuracy
            r.adjust_for_ambient_noise(source, duration=0.5)
            audio_data = r.record(source)
            
        try:
            # Use Google Speech Recognition with Indian English locale for Hinglish support
            text = r.recognize_google(audio_data, language="en-IN")
            print(f"[Noor Voice] Transcribed: '{text}'")
            return text
        except sr.UnknownValueError:
            print("[Noor Voice] Google Speech Recognition could not understand the audio.")
            return ""
        except sr.RequestError as e:
            print(f"[Noor Voice] Google Speech service error: {e}")
            return ""
    except Exception as e:
        print(f"[Noor Voice] Transcription process failed: {e}")
        return ""
