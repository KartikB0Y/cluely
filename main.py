"""
Cluely - Screenshot-Based AI Interview Assistant
================================================
Single-purpose flow:
  INSERT  →  capture screen → ask Sonnet → stream answer into the overlay
  HOME    →  reset conversation memory (start a fresh question chain)

Audio / Whisper / transcripts are DISABLED in this build. The overlay is
two horizontal panes: code on the left, explanation on the right.
"""

import sys
import threading
import traceback
import ctypes

# ----------------------------------------------------------------------
# STEALTH: rename the process so Task Manager shows a generic name instead
# of "python.exe". Do this FIRST before any other imports.
# ----------------------------------------------------------------------
try:
    ctypes.windll.kernel32.SetConsoleTitleW("System Service Host")
    import multiprocessing
    multiprocessing.current_process().name = "svchost"
except Exception:
    pass

print("\n" + "=" * 50)
print("  LOADING CLUELY (screenshot mode)...")
print("=" * 50)

# Heavy imports are fine here — no CTranslate2 / Whisper in this build,
# so there's no ordering hazard.
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer

from config import STEALTH_MODE
from core.ai_engine import AIEngine
from core.screen_capture import ScreenCapture
from ui.overlay import OverlayWindow
from ui.system_tray import SystemTray
from utils.hotkeys import HotkeyManager


class ClueyApp:
    """Tight, single-flow app controller. Two hotkeys, one purpose."""

    def __init__(self):
        # Lazy-init Claude so the app still boots if the API key is missing —
        # the error surfaces in the overlay on first Insert press.
        self.ai_engine = None
        self.screen_capture = ScreenCapture()

        # Prevent overlapping Insert presses from racing the streaming UI.
        self._answer_lock = threading.Lock()

        # Will be set in run() after Qt is up.
        self.overlay = None
        self.tray = None
        self.hotkeys = None

    # ----- Startup --------------------------------------------------------

    def preload(self):
        """Connect to Claude. Cheap and fast — no Whisper anymore."""
        print("[startup] 1/2 Connecting to Claude API...")
        try:
            self.ai_engine = AIEngine()
            print(f"[startup] AI ready: {self.ai_engine.model}")
        except Exception as e:
            print(f"[startup] AI warning (will retry on first use): {e}")
            self.ai_engine = None

        print("[startup] 2/2 Screen capture ready")
        print("\n" + "=" * 50)
        print("  CLUELY READY  —  press INSERT to capture & ask")
        print("=" * 50 + "\n")

    # ----- INSERT key: capture + ask in one action -----------------------

    def capture_and_ask(self):
        """
        Handler for the INSERT hotkey.
        1. Grab the screen as a base64 PNG.
        2. Send it to Sonnet (with full prior history this session).
        3. Stream tokens into the overlay's explanation pane.
        4. On stream completion, the overlay splits the response into the
           code pane (left) and explanation pane (right).
        """
        # Background thread so the UI stays responsive.
        threading.Thread(target=self._do_capture_and_ask, daemon=True).start()

    def _do_capture_and_ask(self):
        # Drop overlapping presses — if a stream is already in flight, ignore.
        if not self._answer_lock.acquire(blocking=False):
            print("[main] Insert ignored — previous answer still streaming")
            return

        try:
            # If the user hid the panel and pressed Insert, auto-unhide so they
            # can see the answer streaming in. Qt requires this on the main thread,
            # but show()/hide() are signal-safe via the overlay's own queueing.
            if not self.overlay.isVisible():
                self.overlay.show_panel()

            # Lazy-init Claude in case the constructor failed at boot.
            if self.ai_engine is None:
                try:
                    self.ai_engine = AIEngine()
                except Exception as e:
                    self.overlay.set_status(f"Claude not available: {e}", False)
                    self.overlay.finalize_response(f"```\nClaude API failed to initialize.\n```\n\n{e}")
                    return

            self.overlay.clear()
            self.overlay.set_status("Capturing screen...", True)
            screenshot_b64 = self.screen_capture.capture_as_base64()

            self.overlay.set_status("Asking Sonnet...", True)

            # Stream tokens into the overlay AND collect them locally so we
            # can hand the full response to finalize_response() at the end.
            full_response_parts = []
            try:
                for chunk in self.ai_engine.answer_screenshot(screenshot_b64):
                    full_response_parts.append(chunk)
                    self.overlay.append_stream_chunk(chunk)
            except Exception as e:
                # Stream error mid-response — show what we got plus the error.
                err = f"\n\n[stream error: {e}]"
                full_response_parts.append(err)
                self.overlay.append_stream_chunk(err)
                print(f"[main] Stream error: {e}")

            full_response = "".join(full_response_parts)

            # Finalize: parse the full response, split code vs explanation,
            # snap both panes to the top so the user reads the answer first.
            self.overlay.finalize_response(full_response)
            self.overlay.set_status("Ready — press Insert to capture", False)

        except Exception as e:
            print(f"[main] Insert handler error: {e}")
            traceback.print_exc()
            self.overlay.set_status(f"Error: {e}", False)
        finally:
            self._answer_lock.release()

    # ----- HOME key: reset session memory --------------------------------

    def reset_session(self):
        """
        Handler for the HOME hotkey. Wipes Sonnet's conversation history so
        the next Insert starts a clean slate (different question, different
        problem). Also clears the overlay panes.
        """
        if self.ai_engine is not None:
            self.ai_engine.reset_conversation()
        self.overlay.clear()
        self.overlay.set_status("Session reset — fresh start", False)
        print("[main] Session reset — conversation history cleared")

    # ----- END key: hide/show the overlay --------------------------------

    def toggle_overlay(self):
        """
        Handler for the END hotkey.
        Toggles overlay visibility so the user can fully see the screen when
        the panel isn't needed. The next INSERT press will auto-unhide it.
        """
        if self.overlay.isVisible():
            self.overlay.hide_panel()
            print("[main] Overlay hidden — press End again to show, or Insert to capture")
        else:
            self.overlay.show_panel()
            print("[main] Overlay shown")

    # ----- Shutdown ------------------------------------------------------

    def quit(self):
        print("[main] Shutting down...")
        if self.hotkeys is not None:
            self.hotkeys.stop()
        try:
            self.screen_capture.close()
        except Exception:
            pass
        QApplication.quit()

    # ----- Main run loop -------------------------------------------------

    def run(self):
        app = QApplication(sys.argv)
        app.setQuitOnLastWindowClosed(False)

        # Boot Claude + capture.
        self.preload()

        # Build the overlay (two-pane layout lives in OverlayWindow).
        self.overlay = OverlayWindow()

        # System tray is hidden in stealth mode to keep the app invisible.
        if STEALTH_MODE:
            self.tray = None
            print("[stealth] Tray icon HIDDEN — use hotkeys only")
        else:
            self.tray = SystemTray(app)
            # Tray actions wire to whatever we have — listening / notes
            # don't exist in this build, so we point them at the live handlers.
            self.tray.take_screenshot.connect(self.capture_and_ask)
            self.tray.quit_app.connect(self.quit)

        # Register hotkeys. The HotkeyManager silently skips actions whose
        # names don't appear in config.HOTKEYS — so leftover bindings in
        # config (if any) are harmless.
        self.hotkeys = HotkeyManager()
        self.hotkeys.register("screenshot", self.capture_and_ask)
        self.hotkeys.register("reset_session", self.reset_session)
        self.hotkeys.register("toggle_overlay", self.toggle_overlay)
        self.hotkeys.start()

        # Show the overlay and apply screen-capture exclusion right after
        # the HWND exists.
        self.overlay.show()
        QTimer.singleShot(100, self.overlay.apply_stealth)

        print("=" * 50)
        print("  CLUELY RUNNING")
        print("=" * 50)
        if STEALTH_MODE:
            print("  Stealth: ON (no tray, no taskbar, no Alt-Tab)")
        print("\n  Hotkeys:")
        print(self.hotkeys.get_bindings_display())
        print("\n  INSERT = capture screen + ask Sonnet (auto-unhides panel)")
        print("  HOME   = reset conversation memory")
        print("  END    = hide / show the panel")
        print("=" * 50 + "\n")

        sys.exit(app.exec())


if __name__ == "__main__":
    try:
        ClueyApp().run()
    except KeyboardInterrupt:
        print("\n[main] Interrupted.")
    except Exception as e:
        print(f"\n[CRASH] {e}")
        traceback.print_exc()
        input("Press Enter to exit...")
