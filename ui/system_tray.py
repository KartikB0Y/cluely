"""
System Tray Icon
================
Provides a system tray icon with right-click menu for controlling Cluely.
"""

from PyQt6.QtWidgets import QSystemTrayIcon, QMenu
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QAction
from PyQt6.QtCore import pyqtSignal, QObject


class SystemTray(QObject):
    """System tray icon with control menu."""

    # Signals
    toggle_listening = pyqtSignal()
    toggle_overlay = pyqtSignal()
    ask_claude = pyqtSignal()
    take_screenshot = pyqtSignal()
    generate_notes = pyqtSignal()
    quit_app = pyqtSignal()

    def __init__(self, app):
        super().__init__()
        self.app = app
        self._listening = False

        # Create a simple colored icon (green circle)
        self.icon_active = self._create_icon(QColor(68, 221, 102))   # Green
        self.icon_idle = self._create_icon(QColor(136, 136, 170))    # Gray

        self.tray = QSystemTrayIcon(self.icon_idle, self.app)
        self.tray.setToolTip("Cluely - AI Meeting Assistant")

        self._build_menu()
        self.tray.show()

    def _create_icon(self, color):
        """Create a simple circular icon."""
        pixmap = QPixmap(32, 32)
        pixmap.fill(QColor(0, 0, 0, 0))  # Transparent
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(color)
        painter.setPen(QColor(0, 0, 0, 0))
        painter.drawEllipse(4, 4, 24, 24)
        painter.end()
        return QIcon(pixmap)

    def _build_menu(self):
        """Build the right-click context menu."""
        menu = QMenu()

        self.action_listen = QAction("Start Listening", self)
        self.action_listen.triggered.connect(self._on_toggle_listening)
        menu.addAction(self.action_listen)

        action_overlay = QAction("Toggle Overlay", self)
        action_overlay.triggered.connect(self.toggle_overlay.emit)
        menu.addAction(action_overlay)

        menu.addSeparator()

        action_ask = QAction("Ask AI (Ctrl+Shift+A)", self)
        action_ask.triggered.connect(self.ask_claude.emit)
        menu.addAction(action_ask)

        action_screen = QAction("Screenshot (Ctrl+Shift+P)", self)
        action_screen.triggered.connect(self.take_screenshot.emit)
        menu.addAction(action_screen)

        action_notes = QAction("Generate Notes (Ctrl+Shift+N)", self)
        action_notes.triggered.connect(self.generate_notes.emit)
        menu.addAction(action_notes)

        menu.addSeparator()

        action_quit = QAction("Quit", self)
        action_quit.triggered.connect(self.quit_app.emit)
        menu.addAction(action_quit)

        self.tray.setContextMenu(menu)

    def _on_toggle_listening(self):
        """Toggle listening state and update icon/menu."""
        self._listening = not self._listening
        if self._listening:
            self.tray.setIcon(self.icon_active)
            self.action_listen.setText("Stop Listening")
            self.tray.setToolTip("Cluely - Listening...")
        else:
            self.tray.setIcon(self.icon_idle)
            self.action_listen.setText("Start Listening")
            self.tray.setToolTip("Cluely - AI Meeting Assistant")
        self.toggle_listening.emit()

    def set_listening(self, active: bool):
        """Set listening state from external source."""
        self._listening = active
        if active:
            self.tray.setIcon(self.icon_active)
            self.action_listen.setText("Stop Listening")
        else:
            self.tray.setIcon(self.icon_idle)
            self.action_listen.setText("Start Listening")

    def show_notification(self, title: str, message: str):
        """Show a system notification."""
        self.tray.showMessage(title, message, QSystemTrayIcon.MessageIcon.Information, 3000)
