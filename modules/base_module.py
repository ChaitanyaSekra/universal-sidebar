"""
modules/base_module.py

Every module (Notes, Calculator, Chat, ...) is a QWidget subclass that
plugs into the main window's QStackedWidget via
`main_window.register_module(key, widget)`. This base class exists purely
to guarantee every module exposes the same minimal contract (a `MODULE_KEY`
and a `MODULE_LABEL`), so the future Command Palette (Phase 13) can build
its "open <module>" command list generically instead of hardcoding a
switch statement over every module name.
"""

from PySide6.QtWidgets import QWidget


class BaseModule(QWidget):
    MODULE_KEY: str = "base"
    MODULE_LABEL: str = "Module"

    def on_shown(self):
        """Optional hook modules can override to refresh data each time
        the user navigates to them (e.g. Notes reloading its list in case
        another part of the app changed it)."""
        pass
