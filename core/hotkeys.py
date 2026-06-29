"""
core/hotkeys.py

Registers OS-wide hotkeys using the `keyboard` library, which hooks the
Windows keyboard driver directly -- this is what makes the shortcuts work
even when some other application has focus, not just when our window does.

The `keyboard` library's hotkey callbacks run on its own internal listener
thread, never the Qt main thread. We never touch any Qt widget directly
from those callbacks; we only emit signals on the shared EventBus, and Qt's
queued cross-thread signal delivery marshals the actual work back onto the
main thread safely.
"""

import keyboard

from core.event_bus import bus
from storage import settings_store


class HotkeyManager:
    def __init__(self):
        self._registered_hotkeys = []

    def start(self):
        """Read hotkeys from settings (so users can have remapped them)
        and register them with the OS. Call once at startup."""
        toggle_key = settings_store.get("toggle_hotkey")
        palette_key = settings_store.get("command_palette_hotkey")

        self._register(toggle_key, lambda: bus.toggle_sidebar_requested.emit())
        self._register(palette_key, lambda: bus.open_command_palette_requested.emit())

    def _register(self, key_combo: str, callback):
        try:
            keyboard.add_hotkey(key_combo, callback)
            self._registered_hotkeys.append(key_combo)
        except Exception as exc:
            # A malformed or already-claimed combo shouldn't crash the app;
            # the user can fix it from Settings and we just skip it.
            print(f"[HotkeyManager] Failed to register '{key_combo}': {exc}")

    def update_hotkey(self, setting_key: str, new_combo: str, callback):
        """Re-register a single hotkey after the user changes it in
        Settings, without restarting the app."""
        old_combo = settings_store.get(setting_key)
        if old_combo in self._registered_hotkeys:
            try:
                keyboard.remove_hotkey(old_combo)
                self._registered_hotkeys.remove(old_combo)
            except (KeyError, ValueError):
                pass
        settings_store.set(setting_key, new_combo)
        self._register(new_combo, callback)

    def stop(self):
        """Unhook everything on app quit so we don't leave a dangling
        keyboard hook after the process exits."""
        for combo in list(self._registered_hotkeys):
            try:
                keyboard.remove_hotkey(combo)
            except (KeyError, ValueError):
                pass
        self._registered_hotkeys.clear()


hotkey_manager = HotkeyManager()
