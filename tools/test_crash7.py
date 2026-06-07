"""Isolate: which import causes the conflict?"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

def log(msg):
    print(msg, flush=True)

# Test A: Just transcriber, no audio_capture
log("A1. Import transcriber only...")
from core.transcriber_base import create_transcriber
log("A2. Load Whisper...")
t = create_transcriber()
t.warmup()
log("A3. Whisper OK without AudioCapture import!")

# Test B: Now import AudioCapture
log("B1. Import AudioCapture...")
from core.audio_capture import AudioCapture
log("B2. AudioCapture import OK after Whisper loaded")

# Test C: Test transcription still works
log("C1. Test transcription...")
import numpy as np
text = t.transcribe(np.zeros(16000, dtype=np.float32))
log(f"C2. Still works: '{text}'")

log("\nDONE!")
