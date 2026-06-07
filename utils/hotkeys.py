"""
Global Hotkey Manager
=====================
Registers and handles system-wide hotkeys.
Uses 'keyboard' library (pip install keyboard).
Falls back to 'pynput' if keyboard is not available.

NOTE: On Windows, the 'keyboard' library may need to be run as administrator
for global hooks. If you get permission errors, either:
  1. Run your terminal as Administrator
  2. Or we automatically fall back to pynput
"""

from typing import Callable, Dict


class HotkeyManager:
    """Manages global hotkey registration and callbacks."""

    def __init__(self):
        from config import HOTKEYS
        self.bindings = HOTKEYS.copy()
        self._callbacks: Dict[str, Callable] = {}
        self._registered = False
        self._backend = None

    def register(self, action: str, callback: Callable):
        """
        Register a callback for a hotkey action.

        Args:
            action: Action name from config (e.g., "toggle_listening")
            callback: Function to call when hotkey is pressed
        """
        if action not in self.bindings:
            print(f"[hotkeys] Warning: Unknown action '{action}', skipping")
            return
        self._callbacks[action] = callback

    def _start_keyboard(self):
        """Try using the 'keyboard' library."""
        import keyboard
        for action, hotkey in self.bindings.items():
            if action in self._callbacks:
                keyboard.add_hotkey(hotkey, self._callbacks[action], suppress=False)
                print(f"[hotkeys] Registered: {hotkey} -> {action}")
        self._backend = "keyboard"
        return True

    def _start_pynput(self):
        """Fallback: use pynput library."""
        from pynput import keyboard as pynput_kb
        import threading

        # Parse hotkey strings into pynput format
        self._pynput_combos = {}
        self._pressed_keys = set()

        key_map = {
            'ctrl': pynput_kb.Key.ctrl_l,
            'shift': pynput_kb.Key.shift_l,
            'alt': pynput_kb.Key.alt_l,
        }

        for action, hotkey_str in self.bindings.items():
            if action not in self._callbacks:
                continue
            parts = hotkey_str.lower().split('+')
            keys = set()
            for part in parts:
                part = part.strip()
                if part in key_map:
                    keys.add(key_map[part])
                elif len(part) == 1:
                    keys.add(pynput_kb.KeyCode.from_char(part))
                else:
                    keys.add(pynput_kb.KeyCode.from_char(part[0]))
            self._pynput_combos[frozenset(keys)] = (action, self._callbacks[action])
            print(f"[hotkeys] Registered: {hotkey_str} -> {action}")

        def on_press(key):
            self._pressed_keys.add(key)
            frozen = frozenset(self._pressed_keys)
            for combo, (action, callback) in self._pynput_combos.items():
                if combo.issubset(frozen):
                    threading.Thread(target=callback, daemon=True).start()

        def on_release(key):
            self._pressed_keys.discard(key)

        self._pynput_listener = pynput_kb.Listener(on_press=on_press, on_release=on_release)
        self._pynput_listener.daemon = True
        self._pynput_listener.start()
        self._backend = "pynput"
        return True

    def start(self):
        """Register all hotkeys with the system."""
        if self._registered:
            return

        # Try keyboard first, then pynput
        try:
            self._start_keyboard()
            self._registered = True
            print(f"[hotkeys] Backend: keyboard")
            return
        except ImportError:
            print(f"[hotkeys] 'keyboard' not found, trying pynput...")
        except Exception as e:
            print(f"[hotkeys] 'keyboard' failed ({e}), trying pynput...")

        try:
            self._start_pynput()
            self._registered = True
            print(f"[hotkeys] Backend: pynput")
            return
        except ImportError:
            print(f"[hotkeys] 'pynput' not found either!")
            print(f"[hotkeys] Install one: pip install keyboard  OR  pip install pynput")
        except Exception as e:
            print(f"[hotkeys] pynput also failed: {e}")

        print(f"[hotkeys] WARNING: No hotkeys active! Use overlay buttons or system tray instead.")

    def stop(self):
        """Unregister all hotkeys."""
        try:
            if self._backend == "keyboard":
                import keyboard
                keyboard.unhook_all_hotkeys()
            elif self._backend == "pynput":
                if hasattr(self, '_pynput_listener'):
                    self._pynput_listener.stop()
        except Exception:
            pass
        self._registered = False
        print(f"[hotkeys] All hotkeys unregistered")

    def get_bindings_display(self) -> str:
        """Get a formatted string of all hotkey bindings."""
        lines = []
        for action, hotkey in self.bindings.items():
            label = action.replace("_", " ").title()
            lines.append(f"  {hotkey:<20} {label}")
        return "\n".join(lines)
