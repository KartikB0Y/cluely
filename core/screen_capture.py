"""
Screen Capture Module
=====================
Captures screenshots for sending to Claude's vision API.
Uses mss for fast, cross-platform screen capture.
"""

import base64
import io


class ScreenCapture:
    """
    Fast screenshot capture for Claude vision integration.

    IMPORTANT: A fresh mss.mss() is created INSIDE each capture call. We can't
    cache it on self because mss's Windows GDI Device Context (srcdc) is stored
    in a thread-local, and Cluely runs each Insert press on a new worker thread.
    A cached instance from thread A crashes with "_thread._local has no attribute
    'srcdc'" when used from thread B.
    """

    def __init__(self):
        # Nothing to hold — every call constructs its own mss in the calling thread.
        pass

    def capture_primary(self) -> bytes:
        """Capture the primary monitor as PNG bytes."""
        from PIL import Image
        import mss

        # Construct mss in THIS thread so its thread-local DC handles are valid here.
        with mss.mss() as sct:
            monitor = sct.monitors[1]  # index 0 = virtual screen across all monitors
            screenshot = sct.grab(monitor)
            size = screenshot.size
            bgra = bytes(screenshot.bgra)  # copy out before mss closes

        # Convert raw BGRA bytes to a PNG via Pillow.
        img = Image.frombytes("RGB", size, bgra, "raw", "BGRX")

        # Cap width to keep API payload small (Claude vision handles up to 8000px
        # but we don't need that, and smaller = faster upload + cheaper tokens).
        max_width = 1920
        if img.width > max_width:
            ratio = max_width / img.width
            img = img.resize((max_width, int(img.height * ratio)), Image.LANCZOS)

        buf = io.BytesIO()
        img.save(buf, format="PNG", optimize=True)
        return buf.getvalue()

    def capture_region(self, x: int, y: int, width: int, height: int) -> bytes:
        """Capture a specific screen rectangle as PNG bytes."""
        from PIL import Image
        import mss

        with mss.mss() as sct:
            region = {"left": x, "top": y, "width": width, "height": height}
            screenshot = sct.grab(region)
            size = screenshot.size
            bgra = bytes(screenshot.bgra)

        img = Image.frombytes("RGB", size, bgra, "raw", "BGRX")
        buf = io.BytesIO()
        img.save(buf, format="PNG", optimize=True)
        return buf.getvalue()

    def capture_as_base64(self) -> str:
        """Capture primary monitor as a base64-encoded PNG (ready for Claude vision)."""
        png_bytes = self.capture_primary()
        return base64.b64encode(png_bytes).decode("utf-8")

    def close(self):
        """No-op — nothing cached to release. Kept for API compatibility."""
        pass
