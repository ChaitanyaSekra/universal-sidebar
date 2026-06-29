"""
ui/title_bar.py

A frameless QWidget has no OS-drawn title bar, so we draw our own: a thin
strip with the app name, a compact-mode toggle, and a close button. It
also implements drag-to-move by tracking mouse press/move deltas, since
frameless windows can't be dragged by their (nonexistent) native title bar.

Redesign notes: the close/compact buttons now use real Tabler icons
instead of unicode glyphs (◧ / ✕), which rendered inconsistently across
fonts and looked like stray text rather than buttons. The title label has
an explicit stretch + minimum-width-0 so it elides gracefully under the
window's resizable range instead of squeezing the buttons.
"""

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QSizePolicy, QWidget

from ui.icon_loader import get_icon, icon_size
from ui.theme import PALETTE

ICON_PX = 16


class TitleBar(QWidget):
    close_clicked = Signal()
    compact_toggle_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("TitleBar")
        self.setFixedHeight(40)
        self._drag_pos = None

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 0, 8, 0)
        layout.setSpacing(4)

        title = QLabel("Universal Sidebar")
        title.setObjectName("TitleBarLabel")
        title.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        title.setMinimumWidth(0)
        layout.addWidget(title)

        self.compact_btn = QPushButton()
        self.compact_btn.setObjectName("TitleBarIconButton")
        self.compact_btn.setIcon(get_icon("layout-sidebar", PALETTE["text_muted"], ICON_PX))
        self.compact_btn.setIconSize(icon_size(ICON_PX))
        self.compact_btn.setFixedSize(30, 30)
        self.compact_btn.setToolTip("Toggle compact mode")
        self.compact_btn.clicked.connect(self.compact_toggle_clicked.emit)
        layout.addWidget(self.compact_btn)

        close_btn = QPushButton()
        close_btn.setObjectName("TitleBarIconButton")
        close_btn.setProperty("danger", "true")
        close_btn.setIcon(get_icon("x", PALETTE["text_muted"], ICON_PX))
        close_btn.setIconSize(icon_size(ICON_PX))
        close_btn.setFixedSize(30, 30)
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
