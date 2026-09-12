"""
voice_assistant.py
─────────────────────────────────────────────────────
Noor Desktop Voice Assistant Daemon.

This script runs in the background and continuously listens for the wake word "Hey Noor".
Once triggered, it records your question, sends it to the Noor REST API, and plays
back the response using high-quality neural Text-to-Speech (TTS).

Usage:
    python voice_assistant.py
"""

from __future__ import annotations

import os
import sys
import time
import uuid
import ctypes
import requests
from pathlib import Path

# Force UTF-8 output on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Allow importing from project root
sys.path.insert(0, str(Path(__file__).parent))

import speech_recognition as sr
from brain.voice import speak_text

API_URL = "http://127.0.0.1:8000/chat"
SESSION_ID = str(uuid.uuid4())

# Wake word list (all lowercase)
WAKE_WORDS = ["hey noor", "okay noor", "ok noor", "hello noor", "hi noor", "noor"]


def play_audio(filename: str) -> None:
    """Play a WAV or MP3 audio file using Windows Multimedia API (MCI)."""
    if not filename or not os.path.exists(filename):
        return
    filename_abs = os.path.abspath(filename)
    try:
        # MCI requires double quotes for paths with spaces
        ctypes.windll.winmm.mciSendStringW(f'open "{filename_abs}" type mpegvideo alias noor_play', None, 0, 0)
        ctypes.windll.winmm.mciSendStringW('play noor_play wait', None, 0, 0)
        ctypes.windll.winmm.mciSendStringW('close noor_play', None, 0, 0)
    except Exception as e:
        print(f"[Voice Daemon] Error playing audio: {e}")


def main():
    print("+======================================================+")
    print("|   * N O O R  -- Desktop Voice Assistant              |")
    print("|     Wake Word: 'Hey Noor'                            |")
    print("+======================================================+")
    
    # Initialize recognizer and microphone
    r = sr.Recognizer()
    mic = sr.Microphone()
    
    print("\n[Voice Daemon] Calibrating microphone for ambient noise...")
    try:
        with mic as source:
            r.adjust_for_ambient_noise(source, duration=1.5)
        print(f"[Voice Daemon] Calibration complete. Energy threshold set to: {r.energy_threshold:.2f}")
    except Exception as e:
        print(f"[Voice Daemon] Calibration failed: {e}. Check your microphone connection.")
        sys.exit(1)
        
    # Enable dynamic adjustment to keep voice detection robust
    r.dynamic_energy_threshold = True
    
    print("[Voice Daemon] Daemon is running. Speak 'Hey Noor' to wake me up!\n")
    
    while True:
        try:
            # Phase 1: Wait for Wake Word
            print("[Voice Daemon] Listening for wake word...", end="\r")
            with mic as source:
                # Listen with a short phrase limit to process wake words quickly
                audio = r.listen(source, timeout=None, phrase_time_limit=3)
                
            try:
                # Transcribe with Indian English locale for best Hinglish recognition
                text = r.recognize_google(audio, language="en-IN").strip().lower()
                
                # Check if any of the wake words are in the recognized text
                is_woken = False
                for w in WAKE_WORDS:
                    if w in text:
                        is_woken = True
                        break
                        
                if is_woken:
                    print(f"\n[Voice Daemon] Wake Word Detected: '{text}'")
                    
                    # Play acknowledgment chime/speech
                    ack_path = speak_text("Yes, I'm listening.")
                    play_audio(ack_path)
                    
                    # Phase 2: Capture subsequent query
                    print("[Voice Daemon] Listening for your question...")
                    with mic as source:
                        # Allow up to 8s pause, 10s max speaking duration
                        audio_query = r.listen(source, timeout=8, phrase_time_limit=12)
                        
                    print("[Voice Daemon] Transcribing...")
                    query_text = r.recognize_google(audio_query, language="en-IN").strip()
                    print(f"[Voice Daemon] Question: '{query_text}'")
                    
                    if query_text:
                        # Phase 3: Query FastAPI Backend
                        print("[Voice Daemon] Querying Noor API...")
                        try:
                            res = requests.post(
                                API_URL,
                                json={"message": query_text, "session_id": SESSION_ID, "stream": False},
                                timeout=20.0
                            )
                            if res.status_code == 200:
                                data = res.json()
                                reply = data["response"]
                                mode = data["mode"]
                                print(f"[Voice Daemon] Noor ({mode}): {reply}")
                                
                                # Phase 4: Speak response
                                print("[Voice Daemon] Synthesizing speech...")
                                reply_audio = speak_text(reply)
                                print("[Voice Daemon] Speaking response...")
                                play_audio(reply_audio)
                            else:
                                print(f"[Voice Daemon] API Error: {res.status_code} - {res.text}")
                                err_audio = speak_text("I encountered an error connecting to my database.")
                                play_audio(err_audio)
                        except requests.RequestException as re_err:
                            print(f"[Voice Daemon] API Connection failed: {re_err}")
                            err_audio = speak_text("I cannot connect to the backend server. Please make sure the main server is running.")
                            play_audio(err_audio)
                    else:
                        print("[Voice Daemon] Empty query, returning to sleep.")
                        
            except sr.UnknownValueError:
                # Normal, didn't recognize anything meaningful
                pass
            except sr.RequestError as re:
                print(f"\n[Voice Daemon] Speech API unavailable: {re}")
                time.sleep(2)
                
        except KeyboardInterrupt:
            print("\n[Voice Daemon] Stopping Voice Assistant. Goodbye!")
            break
        except Exception as e:
            print(f"\n[Voice Daemon] Unexpected error in loop: {e}")
            time.sleep(2)


if __name__ == "__main__":
    main()
