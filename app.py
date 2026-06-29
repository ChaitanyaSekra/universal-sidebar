"""
app.py

The single entry point. Running `python app.py` (or the packaged .exe
built from this in the Packaging phase) starts the whole application:

  1. Build the QApplication (quitOnLastWindowClosed=False, because closing
     the sidebar window should hide it, not kill the tray-resident app).
  2. Build the MainWindow shell and register every module page into it.
  3. Start the global hotkey listener on its background thread.
  4. Start the system tray icon.
  5. Wire the EventBus signals to the actions they trigger.
  6. Run the Qt event loop.

Module pages are imported and registered here, in one place, rather than
the main window importing them directly -- this keeps ui/main_window.py
generic (it only knows about a "module key" + "widget"), and makes adding
a new module later a one-line addition to MODULE_CLASSES below.
"""

import sys

from PySide6.QtWidgets import QApplication

from core.event_bus import bus
from core.hotkeys import hotkey_manager
from storage.database import db  # noqa: F401  (import triggers schema creation)
from ui.main_window import MainWindow
from ui.tray import TrayManager
from storage import settings_store

from modules.chat.view import ChatModule
from modules.notes.view import NotesModule
from modules.calculator.view import CalculatorModule
from modules.calendar.view import CalendarModule
from modules.clipboard.view import ClipboardModule
from modules.favorites.view import FavoritesModule
from modules.quicklinks.view import QuickLinksModule
from modules.todo.view import TodoModule
from modules.timer.view import TimerModule
from modules.settings.view import SettingsModule

MODULE_CLASSES = [
    ChatModule,
    NotesModule,
    CalculatorModule,
    CalendarModule,
    ClipboardModule,
    FavoritesModule,
    QuickLinksModule,
    TodoModule,
    TimerModule,
    SettingsModule,
]


def main():
    app = QApplication(sys.argv)
    # Critical for a tray-resident app: without this, hiding the sidebar
    # window (its only window) would quit the whole application.
    app.setQuitOnLastWindowClosed(False)

    window = MainWindow()

    for module_cls in MODULE_CLASSES:
        window.register_module(module_cls.MODULE_KEY, module_cls())

    # Restore whichever module the user was last looking at.
    window.show_module(settings_store.get("last_module"))

    tray = TrayManager(window)

    hotkey_manager.start()

    # Wire cross-cutting signals to their handlers.
    bus.toggle_sidebar_requested.connect(window.toggle)
    bus.navigate_to_module.connect(window.show_module)

    def _quit():
        hotkey_manager.stop()
        db.close()
        app.quit()

    bus.quit_requested.connect(_quit)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
