"""
ui/nav_rail.py

The slim vertical strip of icon buttons on the left edge of the sidebar
window, used to switch between modules (Chat, Notes, Calculator, ...).
Kept as its own widget so the main window doesn't have to know how the
nav buttons are laid out or styled -- it just asks the rail for the list
of module keys and listens for `module_selected`.
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QButtonGroup
from PySide6.QtCore import Signal, Qt


# (module_key, short_label) -- short_label is shown as the button text since
# we don't ship custom icon assets yet; swapping in QIcon() later is a
# one-line change per button.
MODULE_ORDER = [
    ("chat", "Chat"),
    ("notes", "Notes"),
    ("calculator", "Calc"),
    ("calendar", "Cal"),
    ("clipboard", "Clip"),
    ("favorites", "Fav"),
    ("quicklinks", "Links"),
    ("todo", "Todo"),
    ("timer", "Timer"),
    ("settings", "Set"),
]


class NavRail(QWidget):
    module_selected = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(64)
        self.setObjectName("NavRail")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 12, 4, 12)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignTop)

        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        self._buttons = {}

        for key, label in MODULE_ORDER:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setFixedHeight(48)
            btn.setObjectName("NavButton")
            btn.clicked.connect(lambda checked, k=key: self._on_clicked(k))
            self._group.addButton(btn)
            self._buttons[key] = btn
            layout.addWidget(btn)

        layout.addStretch(1)

    def _on_clicked(self, key: str):
        self.module_selected.emit(key)

    def set_active(self, key: str):
        """Programmatically highlight a module button, e.g. when navigation
        is triggered by the command palette rather than a direct click."""
        btn = self._buttons.get(key)
        if btn is not None:
            btn.setChecked(True)
