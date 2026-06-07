"""
Overlay Window
==============
Two-pane horizontal layout: code on the LEFT, explanation on the RIGHT.
Invisible to screen capture via SetWindowDisplayAffinity.

Flow:
- User presses INSERT → screenshot captured → Sonnet streams a response
- During streaming, raw text accumulates in a hidden buffer
- When the stream finishes, we parse the response (first ``` ... ``` fence becomes
  the code pane, everything else becomes the explanation pane) and snap both
  panes to the top so the user reads the answer FIRST, no scrolling.
"""

import re

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QLabel,
    QApplication, QSizeGrip, QFrame,
)
from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QFont, QTextCursor

from ui.styles import OVERLAY_STYLESHEET


# Regex that finds the FIRST fenced code block.
# Group 1 = language hint (may be empty), Group 2 = code body.
_CODE_FENCE_RE = re.compile(r"```([a-zA-Z0-9_+\-]*)\s*\n(.*?)```", re.DOTALL)


def split_code_and_explanation(raw: str):
    """
    Pull the first ``` ... ``` block out of Sonnet's response.
    Returns (code, language, explanation_after_code).
    If there is no code block, the whole response is treated as explanation.
    """
    match = _CODE_FENCE_RE.search(raw)
    if not match:
        return "", "", raw.strip()

    language = (match.group(1) or "").strip() or "text"
    code = match.group(2).rstrip()

    # Everything that isn't the code block is the explanation. We drop the
    # code-block region and stitch the surrounding prose back together so
    # any "leading sentence" + "trailing sentence" both end up in the right pane.
    explanation = (raw[:match.start()] + raw[match.end():]).strip()
    return code, language, explanation


class OverlayWindow(QWidget):
    """Two-pane stealth overlay. Code (left) + Explanation (right)."""

    # Signals — must be used for any UI update coming from a worker thread.
    status_signal = pyqtSignal(str, bool)          # (message, is_active)
    stream_chunk_signal = pyqtSignal(str)          # raw chunk during streaming
    finalize_signal = pyqtSignal(str)              # full raw response — triggers split + render
    clear_signal = pyqtSignal()
    visibility_signal = pyqtSignal(bool)           # True = show, False = hide

    def __init__(self):
        super().__init__()
        from config import (
            OVERLAY_OPACITY, OVERLAY_WIDTH, OVERLAY_HEIGHT,
            OVERLAY_MARGIN, OVERLAY_POSITION, OVERLAY_FONT_SIZE,
            OVERLAY_EXCLUDE_FROM_CAPTURE,
        )

        self.opacity = OVERLAY_OPACITY
        self.width_px = OVERLAY_WIDTH
        self.height_px = OVERLAY_HEIGHT
        self.margin = OVERLAY_MARGIN
        self.position = OVERLAY_POSITION
        self.font_size = OVERLAY_FONT_SIZE
        self.exclude_from_capture = OVERLAY_EXCLUDE_FROM_CAPTURE

        self._drag_pos = None

        # Buffer that accumulates the streaming response text. Filled by chunk
        # signal, drained by finalize signal.
        self._stream_buffer = ""

        self._setup_window()
        self._setup_ui()
        self._connect_signals()

    # ----- Window / chrome ------------------------------------------------

    def _setup_window(self):
        """Configure frameless, always-on-top, taskbar-hidden window."""
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool  # Hides from taskbar / Alt-Tab
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowOpacity(self.opacity)
        self.setObjectName("OverlayMain")
        self.setStyleSheet(OVERLAY_STYLESHEET)

        screen = QApplication.primaryScreen().geometry()
        if self.position == "right":
            x = screen.width() - self.width_px - self.margin
            y = (screen.height() - self.height_px) // 2
        elif self.position == "left":
            x = self.margin
            y = (screen.height() - self.height_px) // 2
        else:  # bottom
            x = (screen.width() - self.width_px) // 2
            y = screen.height() - self.height_px - self.margin

        self.setGeometry(x, y, self.width_px, self.height_px)

    def _setup_ui(self):
        """Build the two-pane UI."""
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 6, 8, 8)
        root.setSpacing(4)

        # --- Title bar (drag handle + status) ---
        title_bar = QHBoxLayout()
        self.title_label = QLabel("CLUELY")
        self.title_label.setObjectName("TitleBar")
        title_bar.addWidget(self.title_label)

        title_bar.addStretch()

        self.status_label = QLabel("Ready — press Insert to capture")
        self.status_label.setObjectName("StatusLabel")
        title_bar.addWidget(self.status_label)
        root.addLayout(title_bar)

        # --- Two panes side by side ---
        panes = QHBoxLayout()
        panes.setSpacing(6)

        # LEFT — code pane (monospace, syntax-color via stylesheet)
        left_column = QVBoxLayout()
        left_column.setSpacing(2)
        left_label = QLabel("CODE")
        left_label.setObjectName("SectionLabel")
        left_column.addWidget(left_label)

        self.code_area = QTextEdit()
        self.code_area.setObjectName("CodeArea")
        self.code_area.setReadOnly(True)
        self.code_area.setFont(QFont("Consolas", self.font_size))
        self.code_area.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        left_column.addWidget(self.code_area, stretch=1)

        # RIGHT — explanation pane (proportional font, prose)
        right_column = QVBoxLayout()
        right_column.setSpacing(2)
        right_label = QLabel("EXPLANATION")
        right_label.setObjectName("SectionLabel")
        right_column.addWidget(right_label)

        self.explanation_area = QTextEdit()
        self.explanation_area.setObjectName("ExplanationArea")
        self.explanation_area.setReadOnly(True)
        self.explanation_area.setFont(QFont("Segoe UI", self.font_size + 1))
        right_column.addWidget(self.explanation_area, stretch=1)

        # Wrap each column in a QFrame so the stylesheet can give them a border.
        left_frame = QFrame()
        left_frame.setLayout(left_column)
        right_frame = QFrame()
        right_frame.setLayout(right_column)

        # 60/40 split — code gets more space because that's what the user reads first.
        panes.addWidget(left_frame, stretch=6)
        panes.addWidget(right_frame, stretch=4)
        root.addLayout(panes, stretch=1)

        # --- Bottom row: just the resize grip, no buttons (single hotkey UI) ---
        bottom = QHBoxLayout()
        bottom.addStretch()
        bottom.addWidget(QSizeGrip(self))
        root.addLayout(bottom)

        # Compatibility shims: a few legacy callers (system tray, button bindings
        # in main.py) reference these attributes. We expose stubs that are
        # never actually clicked under the single-hotkey flow.
        self.btn_listen = _NoopButton()
        self.btn_ask = _NoopButton()
        self.btn_screenshot = _NoopButton()

    # ----- Signal wiring --------------------------------------------------

    def _connect_signals(self):
        self.status_signal.connect(self._on_status)
        self.stream_chunk_signal.connect(self._on_stream_chunk)
        self.finalize_signal.connect(self._on_finalize)
        self.clear_signal.connect(self._on_clear)
        self.visibility_signal.connect(self._on_visibility)

    @pyqtSlot(bool)
    def _on_visibility(self, should_show: bool):
        """Show or hide the overlay, re-applying stealth on each show()."""
        if should_show:
            self.show()
            # Re-apply WDA_EXCLUDEFROMCAPTURE — show() can re-create the HWND
            # in some Qt edge cases, and the stealth flag is per-HWND.
            self.apply_stealth()
        else:
            self.hide()

    @pyqtSlot(str, bool)
    def _on_status(self, message: str, is_active: bool):
        self.status_label.setText(message)
        # Toggle the object name so the QSS rule for an active state applies.
        self.status_label.setObjectName("StatusActive" if is_active else "StatusLabel")
        self.status_label.setStyleSheet(self.status_label.styleSheet())

    @pyqtSlot(str)
    def _on_stream_chunk(self, chunk: str):
        """
        Append a streaming chunk to the right pane for live feedback while
        Sonnet thinks. We also keep a raw copy in _stream_buffer so finalize()
        can parse the whole response.
        """
        self._stream_buffer += chunk
        cursor = self.explanation_area.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(chunk)
        # Keep the streaming visible at the bottom so the user can watch tokens land.
        self.explanation_area.setTextCursor(cursor)

    @pyqtSlot(str)
    def _on_finalize(self, raw_response: str):
        """
        Stream is complete. Parse the response, route code → left, prose → right,
        snap both panes to the top so the user sees the answer first.
        """
        code, language, explanation = split_code_and_explanation(raw_response)

        # Left pane: just the code (monospace, no decoration). If the model
        # somehow produced no fenced block, show a one-line "see right pane".
        self.code_area.clear()
        if code:
            self.code_area.setPlainText(code)
        else:
            self.code_area.setPlainText("(no code block in response)")

        # Right pane: the explanation, rendered as simple HTML so line breaks
        # and emphasis survive. We strip any trailing whitespace and the
        # explanation slot was already partly filled by streaming chunks — wipe
        # and re-render so the user gets a CLEAN final layout, not a messy mix.
        self.explanation_area.clear()
        if explanation:
            html = (
                f"<div style='line-height:1.45; font-size:{self.font_size + 1}px'>"
                f"{_to_html(explanation)}"
                f"</div>"
            )
            self.explanation_area.setHtml(html)
        else:
            self.explanation_area.setPlainText("(no explanation provided)")

        # Snap both panes to the very top — the whole point of this UI is that
        # the user reads the START of the answer immediately, no scrolling.
        self._scroll_to_top(self.code_area)
        self._scroll_to_top(self.explanation_area)

    @pyqtSlot()
    def _on_clear(self):
        """Wipe both panes and the streaming buffer."""
        self._stream_buffer = ""
        self.code_area.clear()
        self.explanation_area.clear()

    @staticmethod
    def _scroll_to_top(text_edit: QTextEdit):
        cursor = text_edit.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        text_edit.setTextCursor(cursor)
        text_edit.verticalScrollBar().setValue(0)
        text_edit.horizontalScrollBar().setValue(0)

    # ----- Stealth (capture exclusion) -----------------------------------

    def apply_stealth(self):
        """Apply screen-capture exclusion. Must run AFTER show() so HWND exists."""
        if not self.exclude_from_capture:
            return {}
        from utils.windows_api import setup_stealth_window
        status = setup_stealth_window(self)
        if status.get("capture_excluded"):
            print("[overlay] Stealth mode active — invisible to screen capture")
        else:
            print("[overlay] WARNING: Could not enable stealth mode")
        return status

    # ----- Drag-to-move ---------------------------------------------------

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if self._drag_pos and event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None

    # ----- Public, thread-safe API used by main.py -----------------------

    def set_status(self, message: str, is_active: bool = False):
        self.status_signal.emit(message, is_active)

    def append_stream_chunk(self, chunk: str):
        """Live streaming chunk (goes to the explanation pane during loading)."""
        self.stream_chunk_signal.emit(chunk)

    def finalize_response(self, full_response: str):
        """Stream is done — parse it and render both panes cleanly."""
        self.finalize_signal.emit(full_response)

    def clear(self):
        self.clear_signal.emit()

    def hide_panel(self):
        """Thread-safe hide. Hotkey callbacks fire off the Qt thread."""
        self.visibility_signal.emit(False)

    def show_panel(self):
        """Thread-safe show. Re-applies screen-capture stealth on the new HWND state."""
        self.visibility_signal.emit(True)

    # Legacy API shims — main.py and other modules still call these names.
    # Forwarding them keeps the existing wiring functional without churn.
    def clear_response(self):
        self.clear()

    def append_response_chunk(self, chunk: str):
        self.append_stream_chunk(chunk)

    def set_response(self, text: str):
        """Treat a one-shot 'set this text' as a finalize call."""
        self.finalize_response(text)


class _NoopButton:
    """
    Placeholder so legacy code like `self.overlay.btn_listen.clicked.connect(...)`
    keeps working even though the new UI has no buttons. clicked.connect is
    just absorbed.
    """
    class _Signal:
        def connect(self, *_args, **_kwargs):
            pass
    def __init__(self):
        self.clicked = self._Signal()


def _to_html(text: str) -> str:
    """
    Minimal markdown → HTML for the explanation pane.
    We don't pull a full markdown lib because the explanation is 1-2 sentences;
    we just need newlines + `inline code` + **bold** to render.
    """
    # Escape HTML first.
    out = (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
    # `inline code` → <code>
    out = re.sub(r"`([^`]+)`", r"<code style='background:#222;padding:1px 4px;border-radius:3px'>\1</code>", out)
    # **bold** → <b>
    out = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", out)
    # Paragraph breaks
    out = out.replace("\n\n", "</p><p>")
    out = out.replace("\n", "<br>")
    return f"<p>{out}</p>"
