"""Test: Load Whisper BEFORE PyAudio init."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

def log(msg):
    print(msg, flush=True)

log("1. Import everything...")
from PyQt6.QtWidgets import QApplication
import pyaudiowpatch
import numpy as np
from faster_whisper import WhisperModel
log("   OK")

log("2. Load Whisper FIRST (before PyAudio init)...")
model = WhisperModel("base", device="cpu", compute_type="int8")
log("   Whisper OK")

log("3. Warm up Whisper...")
dummy = np.zeros(16000, dtype=np.float32)
segments, _ = model.transcribe(dummy, beam_size=1, language="en")
for _ in segments:
    pass
log("   Warmup OK")

log("4. NOW init PyAudio...")
p = pyaudiowpatch.PyAudio()
log("   PyAudio OK")

log("5. Create QApplication...")
app = QApplication(sys.argv)
log("   Qt OK")

log("6. Terminate PyAudio...")
p.terminate()
log("   OK")

log("\nFIX CONFIRMED: Load Whisper BEFORE PyAudio!")
app.quit()
