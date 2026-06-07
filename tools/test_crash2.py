"""Test what combination of imports causes the crash."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

print("Step 1: Import everything the app imports...")
try:
    from PyQt6.QtWidgets import QApplication
    print("  PyQt6 OK")
    import pyaudiowpatch
    print("  PyAudioWPatch OK")
    import anthropic
    print("  Anthropic OK")
    import keyboard
    print("  Keyboard OK")
    import numpy as np
    print("  Numpy OK")
    from faster_whisper import WhisperModel
    print("  faster-whisper OK")
except Exception as e:
    print(f"  FAIL at import: {e}")
    sys.exit(1)

print("\nStep 2: Create QApplication...")
app = QApplication(sys.argv)
print("  OK")

print("\nStep 3: Initialize AudioCapture (PyAudioWPatch)...")
try:
    from core.audio_capture import AudioCapture
    ac = AudioCapture()
    print("  OK")
except Exception as e:
    print(f"  FAIL: {e}")

print("\nStep 4: Load Whisper model...")
try:
    model = WhisperModel("base", device="cpu", compute_type="int8")
    print("  Model loaded OK")
except Exception as e:
    print(f"  FAIL: {e}")

print("\nStep 5: Warm up with dummy transcription...")
try:
    dummy = np.zeros(16000, dtype=np.float32)
    segments, _ = model.transcribe(dummy, beam_size=1, language="en")
    for _ in segments:
        pass
    print("  Warmup OK")
except Exception as e:
    print(f"  FAIL: {e}")

print("\nStep 6: Create overlay window...")
try:
    from ui.overlay import OverlayWindow
    overlay = OverlayWindow()
    overlay.show()
    print("  Overlay OK")
except Exception as e:
    print(f"  FAIL: {e}")

print("\nALL STEPS PASSED - no crash!")
app.quit()
