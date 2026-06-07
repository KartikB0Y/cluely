"""Test: Import pyaudiowpatch AFTER Whisper loads."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

def log(msg):
    print(msg, flush=True)

log("1. Load Whisper (no pyaudiowpatch imported yet)...")
import numpy as np
from faster_whisper import WhisperModel
model = WhisperModel("base", device="cpu", compute_type="int8")
log("   Whisper OK")

log("2. Warm up...")
dummy = np.zeros(16000, dtype=np.float32)
segments, _ = model.transcribe(dummy, beam_size=1, language="en")
for _ in segments:
    pass
log("   Warmup OK")

log("3. NOW import pyaudiowpatch...")
import pyaudiowpatch
log("   Import OK")

log("4. Init PyAudio...")
p = pyaudiowpatch.PyAudio()
log("   PyAudio OK")

log("5. Create QApplication...")
from PyQt6.QtWidgets import QApplication
app = QApplication(sys.argv)
log("   Qt OK")

log("6. Test transcription still works...")
audio = np.random.randn(16000).astype(np.float32) * 0.01
segments2, _ = model.transcribe(audio, beam_size=1, language="en")
for _ in segments2:
    pass
log("   Still works!")

p.terminate()
log("\nALL PASSED!")
app.quit()
