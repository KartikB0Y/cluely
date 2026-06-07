"""Fix: Load Whisper FIRST before all other imports."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
def log(msg):
    print(msg, flush=True)

log("1. Load Whisper FIRST (before anything else)...")
from core.transcriber_base import create_transcriber
t = create_transcriber()
t.warmup()
log("   Whisper loaded and warm!")

log("2. Now import everything else...")
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
from config import HOTKEYS, AUTO_SAVE_TRANSCRIPT, AUTO_RESPONSE, AUTO_RESPONSE_INTERVAL, EMAIL_DRAFT_ENABLED
from core.audio_capture import AudioCapture
from core.ai_engine import AIEngine
from core.screen_capture import ScreenCapture
from core.session import Session
from ui.overlay import OverlayWindow
from ui.system_tray import SystemTray
from utils.hotkeys import HotkeyManager
log("   All imports OK!")

log("3. Create QApplication...")
app = QApplication(sys.argv)
log("   Qt OK")

log("4. Create overlay...")
overlay = OverlayWindow()
log("   Overlay OK")

log("5. Test transcription still works...")
import numpy as np
text = t.transcribe(np.random.randn(16000).astype(np.float32) * 0.01)
log(f"   Transcription OK: '{text}'")

log("\nFULL APP STARTUP SEQUENCE WORKS!")
app.quit()
