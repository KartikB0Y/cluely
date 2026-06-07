"""Test the exact startup sequence of the fixed main.py."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

def log(msg):
    print(msg, flush=True)

log("1. Import all modules (same as main.py top)...")
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
from core.audio_capture import AudioCapture
from core.transcriber_base import create_transcriber
from core.ai_engine import AIEngine
from core.screen_capture import ScreenCapture
from core.session import Session
log("   All imports OK")

log("2. Load Whisper FIRST...")
transcriber = create_transcriber()
transcriber.warmup()
log("   Whisper loaded and warmed up")

log("3. Create AudioCapture (imports pyaudiowpatch internally)...")
ac = AudioCapture()
log("   AudioCapture created OK")

log("4. Create QApplication...")
app = QApplication(sys.argv)
log("   Qt OK")

log("5. Test transcription still works after PyAudio import...")
import numpy as np
audio = np.random.randn(16000).astype(np.float32) * 0.01
text = transcriber.transcribe(audio)
log(f"   Transcription OK: '{text}'")

log("\nFULL STARTUP SEQUENCE WORKS!")
app.quit()
