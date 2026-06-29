"""
ui/nav_rail.py

The vertical strip of module-switcher buttons on the left edge of the
sidebar window. Redesigned to be icon-only by default: it sits at
COLLAPSED_WIDTH showing just Tabler icons, and on hover animates out to
EXPANDED_WIDTH revealing each button's label next to its icon -- so the
rail stays compact most of the time but isn't a guessing game of unlabeled
icons. Settings is pinned to the bottom via a stretch, everything else
keeps its original top-to-bottom order.

MODULE_ORDER is kept as a flat (key, label) list -- same shape as before
-- so anything elsewhere (e.g. main_window.py) that iterates module keys
doesn't need to change. The icon name for each module key lives in
MODULE_ICONS, separate from MODULE_ORDER, purely so existing callers that
unpack `for key, label in MODULE_ORDER` keep working unmodified.
"""

from PySide6.QtCore import QPropertyAnimation, QEasingCurve, Qt, Signal
from PySide6.QtWidgets import QButtonGroup, QPushButton, QVBoxLayout, QWidget

from ui.icon_loader import get_icon, icon_size
from ui.theme import PALETTE

COLLAPSED_WIDTH = 64
EXPANDED_WIDTH = 180
ICON_PX = 20
ANIM_MS = 140

MODULE_ORDER = [
    ("chat", "Chat"),
    ("notes", "Notes"),
    ("calculator", "Calculator"),
    ("calendar", "Calendar"),
    ("clipboard", "Clipboard"),
    ("favorites", "Favorites"),
    ("quicklinks", "Links"),
    ("todo", "Todo"),
    ("timer", "Timer"),
    ("settings", "Settings"),
]

MODULE_ICONS = {
    "chat": "message-circle",
    "notes": "notes",
    "calculator": "calculator",
    "calendar": "calendar",
    "clipboard": "clipboard",
    "favorites": "star",
    "quicklinks": "link",
    "todo": "checklist",
    "timer": "clock",
    "settings": "settings",
}


class NavRail(QWidget):
    module_selected = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("NavRail")
        self.setFixedWidth(COLLAPSED_WIDTH)
        self._expanded = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 14, 8, 14)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignTop)

        brand = QPushButton()
        brand.setObjectName("NavBrand")
        brand.setIcon(get_icon("layout-sidebar", PALETTE["accent_fg"], ICON_PX))
        brand.setIconSize(icon_size(ICON_PX))
        brand.setFixedHeight(40)
        brand.setEnabled(False)
        layout.addWidget(brand)
        layout.addSpacing(6)

        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        self._buttons = {}

        # Everything except the last entry (Settings) is added in order;
        # a stretch is inserted before Settings so it's pinned to the
        # bottom of the rail regardless of how many modules are above it.
        *top_entries, bottom_entry = MODULE_ORDER
        for key, label in top_entries:
            self._add_button(layout, key, label)
        layout.addStretch(1)
        self._add_button(layout, *bottom_entry)

        self._anim_min = QPropertyAnimation(self, b"minimumWidth")
        self._anim_max = QPropertyAnimation(self, b"maximumWidth")
        for anim in (self._anim_min, self._anim_max):
            anim.setDuration(ANIM_MS)
            anim.setEasingCurve(QEasingCurve.OutCubic)

    def _add_button(self, layout, key, label):
        btn = QPushButton()
        btn.setCheckable(True)
        btn.setFixedHeight(40)
        btn.setObjectName("NavButton")
        btn.setIcon(get_icon(MODULE_ICONS[key], PALETTE["text_muted"], ICON_PX))
        btn.setIconSize(icon_size(ICON_PX))
        btn.setToolTip(label)
        btn.setProperty("full_label", label)
        btn.clicked.connect(lambda checked, k=key: self._on_clicked(k))
        self._group.addButton(btn)
        self._buttons[key] = btn
        layout.addWidget(btn)

    # -- hover expand/collapse ------------------------------------------------

    def enterEvent(self, event):
        self._set_expanded(True)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._set_expanded(False)
        super().leaveEvent(event)

    def _set_expanded(self, expanded: bool):
        if expanded == self._expanded:
            return
        self._expanded = expanded
        target = EXPANDED_WIDTH if expanded else COLLAPSED_WIDTH

        for anim in (self._anim_min, self._anim_max):
            anim.stop()
            anim.setStartValue(self.width())
            anim.setEndValue(target)
            anim.start()

        for btn in self._buttons.values():
            btn.setText(f"  {btn.property('full_label')}" if expanded else "")

    # -- active state ----------------------------------------------------

    def _on_clicked(self, key: str):
        self.module_selected.emit(key)
        self._refresh_icon_colors()

    def _refresh_icon_colors(self):
        for key, btn in self._buttons.items():
            color = PALETTE["accent_fg"] if btn.isChecked() else PALETTE["text_muted"]
            btn.setIcon(get_icon(MODULE_ICONS[key], color, ICON_PX))

    def set_active(self, key: str):
        """Programmatically highlight a module button, e.g. when navigation
        is triggered by the command palette rather than a direct click."""
        btn = self._buttons.get(key)
        if btn is not None:
            btn.setChecked(True)
            self._refresh_icon_colors()
