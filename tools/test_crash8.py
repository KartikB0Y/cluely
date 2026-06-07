"""Find which import before Whisper causes crash."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
def log(msg):
    print(msg, flush=True)

log("1. Import PyQt6...")
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
log("   OK")

log("2. Import config...")
from config import HOTKEYS, AUTO_SAVE_TRANSCRIPT, AUTO_RESPONSE, AUTO_RESPONSE_INTERVAL, EMAIL_DRAFT_ENABLED
log("   OK")

log("3. Import session...")
from core.session import Session
log("   OK")

log("4. Import screen_capture...")
from core.screen_capture import ScreenCapture
log("   OK")

log("5. Import ai_engine...")
from core.ai_engine import AIEngine
log("   OK")

log("6. Import overlay...")
from ui.overlay import OverlayWindow
log("   OK")

log("7. Import system_tray...")
from ui.system_tray import SystemTray
log("   OK")

log("8. Import hotkeys...")
from utils.hotkeys import HotkeyManager
log("   OK")

log("9. NOW load Whisper...")
from core.transcriber_base import create_transcriber
t = create_transcriber()
t.warmup()
log("   Whisper OK")

log("10. NOW import AudioCapture...")
from core.audio_capture import AudioCapture
log("   OK")

log("\nALL PASSED!")
