"""Narrow down segfault - flush after every step."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

def log(msg):
    print(msg, flush=True)

log("1. Import PyQt6...")
from PyQt6.QtWidgets import QApplication
log("   OK")

log("2. Import pyaudiowpatch...")
import pyaudiowpatch
log("   OK")

log("3. Import numpy...")
import numpy as np
log("   OK")

log("4. Import faster_whisper...")
from faster_whisper import WhisperModel
log("   OK")

log("5. Create QApplication...")
app = QApplication(sys.argv)
log("   OK")

log("6. Init PyAudio...")
p = pyaudiowpatch.PyAudio()
log("   OK")

log("7. Load Whisper model...")
model = WhisperModel("base", device="cpu", compute_type="int8")
log("   OK")

log("8. Terminate PyAudio...")
p.terminate()
log("   OK")

log("9. Dummy transcription...")
dummy = np.zeros(16000, dtype=np.float32)
segments, _ = model.transcribe(dummy, beam_size=1, language="en")
for _ in segments:
    pass
log("   OK")

log("\nALL PASSED!")
app.quit()
