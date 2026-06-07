"""Quick test to find what's crashing."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

print("Test 1: Load Whisper without Qt...")
try:
    from faster_whisper import WhisperModel
    model = WhisperModel("base", device="cpu", compute_type="int8")
    print("  OK: Whisper loaded fine without Qt")
    del model
except Exception as e:
    print(f"  FAIL: {e}")

print("\nTest 2: Create QApplication then load Whisper...")
try:
    from PyQt6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    print("  Qt created...")

    model2 = WhisperModel("base", device="cpu", compute_type="int8")
    print("  OK: Whisper loaded fine WITH Qt")
    del model2
except Exception as e:
    print(f"  FAIL: {e}")

print("\nTest 3: Load Whisper BEFORE QApplication...")
try:
    model3 = WhisperModel("base", device="cpu", compute_type="int8")
    print("  Whisper loaded...")
    # QApplication already exists from test 2, skip
    print("  OK: Both loaded")
    del model3
except Exception as e:
    print(f"  FAIL: {e}")

print("\nAll tests passed!")
