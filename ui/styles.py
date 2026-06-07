"""
UI Styles
=========
Dark theme styling for the overlay and system tray.
"""

OVERLAY_STYLESHEET = """
QWidget#OverlayMain {
    background-color: rgba(15, 15, 20, 200);
    border: 1px solid rgba(100, 100, 120, 80);
    border-radius: 12px;
}

QLabel#StatusLabel {
    color: #8888aa;
    font-size: 11px;
    padding: 4px 8px;
}

QLabel#StatusActive {
    color: #44dd66;
    font-size: 11px;
    padding: 4px 8px;
}

QTextEdit#CodeArea {
    background-color: rgba(18, 22, 30, 210);
    color: #e0e6ee;
    border: 1px solid rgba(80, 100, 130, 70);
    border-radius: 6px;
    padding: 8px;
    font-family: 'Consolas', 'Cascadia Code', monospace;
    font-size: 13px;
    selection-background-color: rgba(80, 100, 140, 180);
}

QTextEdit#ExplanationArea {
    background-color: rgba(22, 26, 22, 200);
    color: #c8d8c8;
    border: 1px solid rgba(80, 120, 80, 70);
    border-radius: 6px;
    padding: 8px;
    font-family: 'Segoe UI', sans-serif;
    font-size: 13px;
    selection-background-color: rgba(60, 120, 60, 150);
}

QLabel#SectionLabel {
    color: #6688aa;
    font-size: 10px;
    font-weight: bold;
    padding: 2px 8px;
    text-transform: uppercase;
}

QPushButton#MinimalButton {
    background-color: rgba(50, 50, 70, 150);
    color: #aaaacc;
    border: 1px solid rgba(80, 80, 100, 100);
    border-radius: 4px;
    padding: 3px 10px;
    font-size: 11px;
}

QPushButton#MinimalButton:hover {
    background-color: rgba(70, 70, 90, 180);
    color: #ccccee;
}

QPushButton#MinimalButton:pressed {
    background-color: rgba(40, 40, 60, 200);
}

QLabel#TitleBar {
    color: #666688;
    font-size: 10px;
    padding: 2px 8px;
}
"""

# Colors for reference
COLORS = {
    "bg_dark": (15, 15, 20),
    "bg_medium": (20, 20, 30),
    "text_primary": (204, 204, 221),
    "text_secondary": (136, 136, 170),
    "text_ai": (170, 221, 170),
    "accent_green": (68, 221, 102),
    "accent_blue": (102, 136, 170),
    "border": (100, 100, 120),
}
