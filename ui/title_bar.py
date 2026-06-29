"""
ui/title_bar.py

A frameless QWidget has no OS-drawn title bar, so we draw our own: a thin
strip with the app name, a compact-mode toggle, and a close button. It
also implements drag-to-move by tracking mouse press/move deltas, since
frameless windows can't be dragged by their (nonexistent) native title bar.
"""

from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Qt, Signal, QPoint


class TitleBar(QWidget):
    close_clicked = Signal()
    compact_toggle_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("TitleBar")
        self.setFixedHeight(36)
        self._drag_pos = None

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 8, 0)

        title = QLabel("Universal Sidebar")
        title.setStyleSheet("font-weight: 600;")
        layout.addWidget(title)
        layout.addStretch(1)

        self.compact_btn = QPushButton("◧")
        self.compact_btn.setFixedSize(28, 28)
        self.compact_btn.setToolTip("Toggle compact mode")
        self.compact_btn.clicked.connect(self.compact_toggle_clicked.emit)
        layout.addWidget(self.compact_btn)

        close_btn = QPushButton("✕")
        close_btn.setObjectName("DangerButton")
        close_btn.setFixedSize(28, 28)
        close_btn.setToolTip("Hide sidebar (keeps running in tray)")
        close_btn.clicked.connect(self.close_clicked.emit)
        layout.addWidget(close_btn)

    # -- drag to move the frameless window ----------------------------------

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.window().pos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_pos is not None and event.buttons() & Qt.LeftButton:
            self.window().move(event.globalPosition().toPoint() - self._drag_pos)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        super().mouseReleaseEvent(event)
