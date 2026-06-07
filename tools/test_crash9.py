"""Binary search: which import kills Whisper?"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
def log(msg):
    print(msg, flush=True)

# Test each import individually before Whisper

log("TEST A: keyboard + Whisper")
import keyboard
from faster_whisper import WhisperModel
m = WhisperModel("base", device="cpu", compute_type="int8")
log("  A OK")
del m

log("TEST B: anthropic + Whisper")
import anthropic
m = WhisperModel("base", device="cpu", compute_type="int8")
log("  B OK")
del m

log("TEST C: PyQt6 + Whisper")
from PyQt6.QtWidgets import QApplication
m = WhisperModel("base", device="cpu", compute_type="int8")
log("  C OK")
del m

log("TEST D: mss + Whisper")
import mss
m = WhisperModel("base", device="cpu", compute_type="int8")
log("  D OK")
del m

log("\nAll individual tests passed!")
