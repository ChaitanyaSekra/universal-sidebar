"""
ui/tray.py

Since the app has no taskbar window most of the time (the sidebar slides
away and the window is hidden, not closed), the tray icon is the only
always-visible piece of UI. It offers Show/Hide, Settings, and Quit, and
left/double clicking it toggles the sidebar the same as the global hotkey.
"""

from PySide6.QtWidgets import QSystemTrayIcon, QMenu
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor
from PySide6.QtCore import Qt

from core.event_bus import bus


def _fallback_icon() -> QIcon:
    """Draw a simple solid-color circle icon at runtime. This means the
    app has a usable tray icon even before real branded .ico/.png assets
    are designed -- swapping in assets/icons/tray.ico later is a one-line
    change in TrayManager.__init__."""
    pixmap = QPixmap(32, 32)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setBrush(QColor("#7c8cff"))
    painter.setPen(Qt.NoPen)
    painter.drawEllipse(2, 2, 28, 28)
    painter.end()
    return QIcon(pixmap)


class TrayManager:
    def __init__(self, main_window):
        self.main_window = main_window
        self.tray = QSystemTrayIcon(_fallback_icon())
        self.tray.setToolTip("Universal Sidebar")

        menu = QMenu()
        self.toggle_action = menu.addAction("Show / Hide Sidebar")
        self.toggle_action.triggered.connect(self.main_window.toggle)

        settings_action = menu.addAction("Settings")
        settings_action.triggered.connect(lambda: self._open_settings())

        menu.addSeparator()
        quit_action = menu.addAction("Quit Universal Sidebar")
        quit_action.triggered.connect(bus.quit_requested.emit)

        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._on_activated)
        self.tray.show()

    def _on_activated(self, reason):
        # Left-click or double-click toggles the sidebar; right-click is
        # handled automatically by Qt to open the context menu.
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            self.main_window.toggle()

    def _open_settings(self):
        if not self.main_window.isVisible():
            self.main_window.show_animated()
        self.main_window.show_module("settings")

    def notify(self, title: str, message: str):
        """Used by the Timer module to show a native Windows toast when a
        Pomodoro/countdown finishes."""
        self.tray.showMessage(title, message, QSystemTrayIcon.Information, 5000)
