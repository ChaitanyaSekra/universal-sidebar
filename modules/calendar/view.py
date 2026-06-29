"""
modules/calendar/view.py

Month-view calendar wired directly to the user's Google Calendar
(primary calendar): selecting a date loads that day's Google events,
and the user can create, edit, and delete events from here -- changes
land on the real Google Calendar immediately.

No local-only event storage is used for this module (the user chose
"Create/edit/delete Google events" only, not a separate local list), so
the `calendar_events` table created in storage/database.py is unused by
this view; it's left in the schema in case a future "offline notes on
dates" feature wants it.
"""

from datetime import datetime, timedelta

from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QCalendarWidget,
    QListWidget, QListWidgetItem, QMessageBox
)
from PySide6.QtCore import Qt, QDate

from modules.base_module import BaseModule
from modules.calendar import google_auth, google_service
from modules.calendar.workers import run_async
from modules.calendar.event_dialog import EventDialog


class CalendarModule(BaseModule):
    MODULE_KEY = "calendar"
    MODULE_LABEL = "Calendar"

    def __init__(self, parent=None):
        super().__init__(parent)
        self._events_by_id = {}  # event_id -> event dict, for the currently loaded day
        self._active_worker = None
        self._build_ui()
        self._refresh_connection_state()

    # -- UI construction --------------------------------------------------

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        # Connection bar
        conn_row = QHBoxLayout()
        self.status_label = QLabel("")
        self.status_label.setObjectName("MutedLabel")
        conn_row.addWidget(self.status_label)
        conn_row.addStretch(1)
        self.connect_btn = QPushButton("Connect Google Calendar")
        self.connect_btn.clicked.connect(self._on_connect_clicked)
        conn_row.addWidget(self.connect_btn)
        root.addLayout(conn_row)

        # Month calendar
        self.calendar = QCalendarWidget()
        self.calendar.setGridVisible(True)
        self.calendar.selectionChanged.connect(self._on_date_selected)
        root.addWidget(self.calendar)

        # Selected-day events
        day_header = QHBoxLayout()
        self.day_label = QLabel("")
        day_header.addWidget(self.day_label)
        day_header.addStretch(1)
        add_btn = QPushButton("+ New event")
        add_btn.clicked.connect(self._on_add_event)
        day_header.addWidget(add_btn)
        root.addLayout(day_header)

        self.events_list = QListWidget()
        self.events_list.itemDoubleClicked.connect(self._on_edit_event)
        root.addWidget(self.events_list, 1)

        actions_row = QHBoxLayout()
        actions_row.addStretch(1)
        delete_btn = QPushButton("Delete selected")
        delete_btn.setObjectName("DangerButton")
        delete_btn.clicked.connect(self._on_delete_event)
        actions_row.addWidget(delete_btn)
        root.addLayout(actions_row)

    # -- connection state -----------------------------------------------------

    def _refresh_connection_state(self):
        connected = google_auth.is_connected()
        self.connect_btn.setText("Disconnect" if connected else "Connect Google Calendar")
        self.status_label.setText(
            "Connected to Google Calendar" if connected
            else "Not connected -- showing nothing until you connect"
        )
        self.calendar.setEnabled(connected)
        if connected:
            self._load_events_for_selected_date()
        else:
            self.events_list.clear()
            self.day_label.setText("")

    def _on_connect_clicked(self):
        if google_auth.is_connected():
            google_auth.disconnect()
            self._refresh_connection_state()
            return

        if not google_auth.credentials_file_exists():
            QMessageBox.warning(
                self, "Setup required",
                f"No credentials.json found at:\n{google_auth.CREDENTIALS_PATH}\n\n"
                "See the README's 'Connecting Google Calendar' section for the "
                "one-time Google Cloud setup steps, then try again."
            )
            return

        self.connect_btn.setEnabled(False)
        self.status_label.setText("Opening browser for Google sign-in...")
        self._active_worker = run_async(
            google_auth.connect_interactive,
            self._on_connect_succeeded,
            self._on_connect_failed,
        )

    def _on_connect_succeeded(self, _creds):
        self.connect_btn.setEnabled(True)
        self._refresh_connection_state()

    def _on_connect_failed(self, message: str):
        self.connect_btn.setEnabled(True)
        self.status_label.setText("Connection failed")
        QMessageBox.critical(self, "Google Calendar connection failed", message)

    # -- loading events for the selected day --------------------------------

    def _on_date_selected(self):
        self._load_events_for_selected_date()

    def _selected_date(self):
        qd: QDate = self.calendar.selectedDate()
        return qd.toPython()

    def _load_events_for_selected_date(self):
        if not google_auth.is_connected():
            return
        d = self._selected_date()
        self.day_label.setText(d.strftime("%A, %B %d, %Y"))
        start = datetime.combine(d, datetime.min.time())
        end = start + timedelta(days=1)

        self.events_list.clear()
        self.events_list.addItem("Loading...")
        self._active_worker = run_async(
            google_service.list_events,
            self._on_events_loaded,
            self._on_events_load_failed,
            start, end,
        )

    def _on_events_loaded(self, events: list):
        self.events_list.clear()
        self._events_by_id.clear()
        if not events:
            self.events_list.addItem("No events on this day")
            return
        for event in events:
            self._events_by_id[event["id"]] = event
            time_label = "All day" if event["all_day"] else self._format_time_range(event)
            item = QListWidgetItem(f"{time_label}  —  {event['title']}")
            item.setData(Qt.UserRole, event["id"])
            self.events_list.addItem(item)

    def _on_events_load_failed(self, message: str):
        self.events_list.clear()
        self.events_list.addItem("Failed to load events")
        QMessageBox.critical(self, "Google Calendar error", message)

    @staticmethod
    def _format_time_range(event: dict) -> str:
        try:
            start = datetime.fromisoformat(event["start"]).strftime("%H:%M")
            end = datetime.fromisoformat(event["end"]).strftime("%H:%M")
            return f"{start}–{end}"
        except (ValueError, KeyError):
            return ""

    # -- create / edit / delete -----------------------------------------------

    def _on_add_event(self):
        if not google_auth.is_connected():
            QMessageBox.information(self, "Not connected", "Connect Google Calendar first.")
            return
        dialog = EventDialog(self, default_date=self._selected_date())
        if dialog.exec():
            values = dialog.get_values()
            self._active_worker = run_async(
                google_service.create_event,
                self._on_mutation_succeeded,
                self._on_mutation_failed,
                values["title"], values["start"], values["end"],
                values["description"], values["all_day"],
            )

    def _on_edit_event(self, item: QListWidgetItem):
        event_id = item.data(Qt.UserRole)
        event = self._events_by_id.get(event_id)
        if event is None:
            return
        dialog = EventDialog(self, default_date=self._selected_date(), existing=event)
        if dialog.exec():
            values = dialog.get_values()
            self._active_worker = run_async(
                google_service.update_event,
                self._on_mutation_succeeded,
                self._on_mutation_failed,
                event_id, values["title"], values["start"], values["end"],
                values["description"], values["all_day"],
            )

    def _on_delete_event(self):
        item = self.events_list.currentItem()
        if item is None:
            return
        event_id = item.data(Qt.UserRole)
        if not event_id:
            return
        confirm = QMessageBox.question(
            self, "Delete event", "Delete this event from Google Calendar?"
        )
        if confirm == QMessageBox.Yes:
            self._active_worker = run_async(
                google_service.delete_event,
                self._on_mutation_succeeded,
                self._on_mutation_failed,
                event_id,
            )

    def _on_mutation_succeeded(self, _result):
        self._load_events_for_selected_date()

    def _on_mutation_failed(self, message: str):
        QMessageBox.critical(self, "Google Calendar error", message)

    def on_shown(self):
        self._refresh_connection_state()
