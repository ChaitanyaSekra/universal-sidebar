"""
ui/main_window.py

The single top-level window of the app. It is:
  - Frameless (no OS title bar) and always-on-top.
  - Docked to the right edge of the primary screen.
  - Slide-in/out animated via QPropertyAnimation on its x position.
  - Resizable by dragging its left edge (custom mouse-event handling,
    since a frameless window has no native resize grip).
  - Persists width and compact/expanded state to settings so it reopens
    exactly how the user left it.

Module pages are added via `register_module(key, widget)` from app.py,
keeping this file ignorant of what Notes/Calculator/etc. actually contain.
"""

from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QStackedWidget, QApplication
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QPoint, QRect
from PySide6.QtGui import QGuiApplication

from ui.nav_rail import NavRail
from ui.title_bar import TitleBar
from ui.theme import build_stylesheet
from core.config import (
    DEFAULT_SIDEBAR_WIDTH, MIN_SIDEBAR_WIDTH, MAX_SIDEBAR_WIDTH,
    COMPACT_SIDEBAR_WIDTH, SIDEBAR_ANIMATION_MS,
)
from core.event_bus import bus
from storage import settings_store

RESIZE_MARGIN = 6  # px of the left edge that counts as the resize grip


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("SidebarRoot")
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground, False)

        self._expanded_width = settings_store.get_int("sidebar_width")
        self._is_compact = settings_store.get_bool("sidebar_compact")
        self._is_visible_on_screen = False
        self._resizing = False

        self._build_ui()
        self._apply_theme(settings_store.get("theme"))
        self._restore_geometry()

        bus.theme_changed.connect(self._apply_theme)

    # -- construction --------------------------------------------------

    def _build_ui(self):
        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self.nav_rail = NavRail()
        self.nav_rail.module_selected.connect(self._on_module_selected)
        outer.addWidget(self.nav_rail)

        right_column = QWidget()
        right_layout = QVBoxLayout(right_column)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        self.title_bar = TitleBar()
        self.title_bar.close_clicked.connect(self.hide_animated)
        self.title_bar.compact_toggle_clicked.connect(self.toggle_compact)
        right_layout.addWidget(self.title_bar)

        self.stack = QStackedWidget()
        right_layout.addWidget(self.stack)

        outer.addWidget(right_column, 1)

        self._module_index = {}

    def register_module(self, key: str, widget: QWidget):
        """Add a module page to the stack. Called once per module from
        app.py during startup wiring."""
        index = self.stack.addWidget(widget)
        self._module_index[key] = index

    def show_module(self, key: str):
        index = self._module_index.get(key)
        if index is not None:
            self.stack.setCurrentIndex(index)
            self.nav_rail.set_active(key)
            settings_store.set("last_module", key)

    def _on_module_selected(self, key: str):
        self.show_module(key)

    # -- theme -----------------------------------------------------------

    def _apply_theme(self, theme_name: str):
        self.setStyleSheet(build_stylesheet(theme_name))
        settings_store.set("theme", theme_name)

    # -- geometry: docking to right edge, width, compact mode --------------

    def _screen_geometry(self) -> QRect:
        screen = QGuiApplication.primaryScreen()
        return screen.availableGeometry()

    def _target_width(self) -> int:
        return COMPACT_SIDEBAR_WIDTH if self._is_compact else self._expanded_width

    def _docked_geometry(self, visible: bool) -> QRect:
        """Geometry when fully shown (visible=True) or fully hidden just
        off the right edge of the screen (visible=False), used as the
        animation start/end points."""
        screen = self._screen_geometry()
        width = self._target_width()
        height = screen.height()
        x = screen.right() - width + 1 if visible else screen.right() + 1
        return QRect(x, screen.top(), width, height)

    def _restore_geometry(self):
        self.setFixedHeight(self._screen_geometry().height())
        self.setGeometry(self._docked_geometry(visible=False))
        self._update_fixed_width()

    def _update_fixed_width(self):
        if not self._resizing:
            self.setMinimumWidth(self._target_width())
            self.setMaximumWidth(self._target_width())

    # -- show / hide animation -------------------------------------------

    def toggle(self):
        if self._is_visible_on_screen:
            self.hide_animated()
        else:
            self.show_animated()

    def show_animated(self):
        self._update_fixed_width()
        self.show()
        self.raise_()
        self.activateWindow()
        start = self._docked_geometry(visible=False)
        end = self._docked_geometry(visible=True)
        self._animate(start, end)
        self._is_visible_on_screen = True

    def hide_animated(self):
        start = self._docked_geometry(visible=True)
        end = self._docked_geometry(visible=False)
        anim = self._animate(start, end)
        anim.finished.connect(self.hide)
        self._is_visible_on_screen = False

    def _animate(self, start: QRect, end: QRect) -> QPropertyAnimation:
        anim = QPropertyAnimation(self, b"geometry")
        anim.setDuration(SIDEBAR_ANIMATION_MS)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        anim.setStartValue(start)
        anim.setEndValue(end)
        anim.start(QPropertyAnimation.DeleteWhenStopped)
        self._active_anim = anim  # keep a reference so it isn't GC'd mid-flight
        return anim

    def toggle_compact(self):
        self._is_compact = not self._is_compact
        settings_store.set("sidebar_compact", self._is_compact)
        self._update_fixed_width()
        if self._is_visible_on_screen:
            self.setGeometry(self._docked_geometry(visible=True))

    # -- manual resize via left-edge drag ---------------------------------

    def mousePressEvent(self, event):
        if not self._is_compact and event.position().x() <= RESIZE_MARGIN:
            self._resizing = True
            self.setMinimumWidth(MIN_SIDEBAR_WIDTH)
            self.setMaximumWidth(MAX_SIDEBAR_WIDTH)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._resizing:
            screen_right = self._screen_geometry().right() + 1
            new_width = max(
                MIN_SIDEBAR_WIDTH,
                min(MAX_SIDEBAR_WIDTH, screen_right - event.globalPosition().toPoint().x()),
            )
            geo = self.geometry()
            geo.setX(screen_right - new_width)
            geo.setWidth(new_width)
            self.setGeometry(geo)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._resizing:
            self._resizing = False
            self._expanded_width = self.width()
            settings_store.set("sidebar_width", self._expanded_width)
            self._update_fixed_width()
        super().mouseReleaseEvent(event)
