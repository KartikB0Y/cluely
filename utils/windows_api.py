"""
Windows API Utilities
=====================
Handles Windows-specific functionality:
- Excluding windows from screen capture (the stealth feature)
- Always-on-top window management
- Native window handle (HWND) access
"""

import ctypes
import ctypes.wintypes

# Windows Display Affinity constants
WDA_NONE = 0x00000000
WDA_MONITOR = 0x00000001              # Legacy: shows black in capture
WDA_EXCLUDEFROMCAPTURE = 0x00000011   # Win10 2004+: completely invisible in capture

user32 = ctypes.windll.user32


def set_window_exclude_from_capture(hwnd):
    """
    Make a window INVISIBLE to all screen capture methods.

    This uses SetWindowDisplayAffinity with WDA_EXCLUDEFROMCAPTURE.
    Available on Windows 10 version 2004 (May 2020 Update) and later.

    The window will be invisible to:
    - Zoom screen sharing
    - Google Meet screen sharing
    - Microsoft Teams screen sharing
    - OBS Studio capture
    - Windows Game Bar
    - PrintScreen / Snipping Tool
    - Any app using BitBlt, PrintWindow, or DXGI capture

    The window remains visible on the physical display.

    Args:
        hwnd: Native window handle (int or ctypes handle)

    Returns:
        bool: True if successful
    """
    result = user32.SetWindowDisplayAffinity(int(hwnd), WDA_EXCLUDEFROMCAPTURE)
    if result == 0:
        error = ctypes.get_last_error()
        # Try fallback to WDA_MONITOR (older Windows versions)
        result = user32.SetWindowDisplayAffinity(int(hwnd), WDA_MONITOR)
        if result == 0:
            print(f"[windows_api] WARNING: SetWindowDisplayAffinity failed. "
                  f"Error: {error}. Window may be visible in screen capture.")
            return False
        else:
            print(f"[windows_api] Using WDA_MONITOR fallback (shows black in capture instead of invisible)")
            return True
    return True


def remove_capture_exclusion(hwnd):
    """Remove capture exclusion - make window visible in screen capture again."""
    result = user32.SetWindowDisplayAffinity(int(hwnd), WDA_NONE)
    return result != 0


def set_always_on_top(hwnd, on_top=True):
    """Set or unset a window as always-on-top."""
    HWND_TOPMOST = -1
    HWND_NOTOPMOST = -2
    SWP_NOMOVE = 0x0002
    SWP_NOSIZE = 0x0001
    SWP_NOACTIVATE = 0x0010

    insert_after = HWND_TOPMOST if on_top else HWND_NOTOPMOST
    user32.SetWindowPos(
        int(hwnd),
        insert_after,
        0, 0, 0, 0,
        SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE
    )


def set_click_through(hwnd, click_through=True):
    """
    Make a window click-through (mouse events pass to windows below).
    Useful for overlay mode where you want to interact with apps behind it.
    """
    GWL_EXSTYLE = -20
    WS_EX_TRANSPARENT = 0x00000020
    WS_EX_LAYERED = 0x00080000

    style = user32.GetWindowLongW(int(hwnd), GWL_EXSTYLE)
    if click_through:
        style |= WS_EX_TRANSPARENT | WS_EX_LAYERED
    else:
        style &= ~WS_EX_TRANSPARENT
    user32.SetWindowLongW(int(hwnd), GWL_EXSTYLE, style)


def get_hwnd_from_pyqt(widget):
    """
    Get the native Windows HWND from a PyQt6 widget.

    Args:
        widget: A PyQt6 QWidget instance

    Returns:
        int: The native window handle
    """
    return int(widget.winId())


def setup_stealth_window(widget, exclude_from_capture=True, always_on_top=True):
    """
    One-call setup for a stealth overlay window.

    Args:
        widget: PyQt6 QWidget (must be shown/visible first)
        exclude_from_capture: Hide from screen capture
        always_on_top: Keep window above all others

    Returns:
        dict: Status of each operation
    """
    hwnd = get_hwnd_from_pyqt(widget)
    status = {"hwnd": hwnd}

    if exclude_from_capture:
        status["capture_excluded"] = set_window_exclude_from_capture(hwnd)

    if always_on_top:
        set_always_on_top(hwnd, True)
        status["always_on_top"] = True

    return status


def check_windows_version():
    """
    Check if the Windows version supports WDA_EXCLUDEFROMCAPTURE.
    Requires Windows 10 version 2004 (build 19041) or later.
    """
    try:
        version = ctypes.windll.ntdll.RtlGetVersion
        osvi = ctypes.wintypes.OSVERSIONINFOW()
        osvi.dwOSVersionInfoSize = ctypes.sizeof(osvi)
        version(ctypes.byref(osvi))

        build = osvi.dwBuildNumber
        if build >= 19041:
            return {
                "supported": True,
                "build": build,
                "method": "WDA_EXCLUDEFROMCAPTURE (fully invisible)"
            }
        elif build >= 10000:
            return {
                "supported": True,
                "build": build,
                "method": "WDA_MONITOR (shows black rectangle)"
            }
        else:
            return {
                "supported": False,
                "build": build,
                "method": "Not supported"
            }
    except Exception as e:
        return {"supported": False, "error": str(e)}
