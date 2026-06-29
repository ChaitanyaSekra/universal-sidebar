"""
core/event_bus.py

A single QObject holding Qt signals that any part of the app can connect to
or emit from. This is the desktop equivalent of the "messaging system"
between background/content/sidebar layers in the original browser-extension
plan: instead of every widget needing a direct reference to every other
widget, things emit a signal and whoever cares connects to it.

Why this matters specifically here: the global hotkey listener (Phase 3)
runs its callback on a background thread (the `keyboard` library's own
listener thread), NOT the Qt main thread. Qt signals are thread-safe to
emit from any thread as long as the connection type is queued (the default
for cross-thread connections), so routing every cross-thread interaction
through this bus avoids the classic "called a Qt widget method from a
worker thread and the UI silently corrupted" bug class.
"""

from PySide6.QtCore import QObject, Signal


class EventBus(QObject):
    # Fired by the global hotkey thread (or tray icon) to ask the main
    # window to show/hide itself.
    toggle_sidebar_requested = Signal()

    # Fired to open the command palette overlay.
    open_command_palette_requested = Signal()

    # Fired by any module when it wants the sidebar to switch to a
    # specific module by key, e.g. "notes", "calculator".
    navigate_to_module = Signal(str)

    # Fired whenever the theme changes, so every open module can restyle
    # itself immediately instead of requiring a restart.
    theme_changed = Signal(str)

    # Fired when the OS clipboard watcher detects new text, carrying the
    # captured string.
    clipboard_captured = Signal(str)

    # Fired when the app wants to quit cleanly (closes DB, unhooks hotkeys).
    quit_requested = Signal()


# Single shared instance imported everywhere: `from core.event_bus import bus`
bus = EventBus()
