"""
modules/calendar/event_dialog.py

A modal dialog for creating a new event or editing an existing one.
Returns the entered fields via get_values(); view.py decides whether to
call google_service.create_event() or update_event() with them.
"""

from datetime import datetime, date, time, timedelta

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QTextEdit, QDateEdit,
    QTimeEdit, QCheckBox, QDialogButtonBox, QHBoxLayout
)
from PySide6.QtCore import QDate, QTime


class EventDialog(QDialog):
    def __init__(self, parent=None, default_date: date = None, existing: dict = None):
        super().__init__(parent)
        self.setWindowTitle("Edit event" if existing else "New event")
        self.setMinimumWidth(320)
        self._existing = existing

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.title_input = QLineEdit()
        form.addRow("Title", self.title_input)

        self.description_input = QTextEdit()
        self.description_input.setFixedHeight(60)
        form.addRow("Description", self.description_input)

        self.all_day_checkbox = QCheckBox("All-day event")
        self.all_day_checkbox.toggled.connect(self._on_all_day_toggled)
        form.addRow("", self.all_day_checkbox)

        d = default_date or date.today()
        self.start_date = QDateEdit(QDate(d.year, d.month, d.day))
        self.start_date.setCalendarPopup(True)
        self.end_date = QDateEdit(QDate(d.year, d.month, d.day))
        self.end_date.setCalendarPopup(True)

        date_row = QHBoxLayout()
        date_row.addWidget(self.start_date)
        date_row.addWidget(self.end_date)
        form.addRow("Date range", date_row)

        self.start_time = QTimeEdit(QTime(9, 0))
        self.end_time = QTimeEdit(QTime(10, 0))
        time_row = QHBoxLayout()
        time_row.addWidget(self.start_time)
        time_row.addWidget(self.end_time)
        form.addRow("Time range", time_row)

        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        if existing:
            self._populate_from_existing(existing)

    def _on_all_day_toggled(self, checked: bool):
        self.start_time.setEnabled(not checked)
        self.end_time.setEnabled(not checked)

    def _populate_from_existing(self, existing: dict):
        self.title_input.setText(existing.get("title", ""))
        self.description_input.setPlainText(existing.get("description", ""))
        self.all_day_checkbox.setChecked(existing.get("all_day", False))

        start_str = existing.get("start", "")
        end_str = existing.get("end", "")
        try:
            if existing.get("all_day"):
                sd = datetime.strptime(start_str, "%Y-%m-%d").date()
                ed = datetime.strptime(end_str, "%Y-%m-%d").date()
                self.start_date.setDate(QDate(sd.year, sd.month, sd.day))
                self.end_date.setDate(QDate(ed.year, ed.month, ed.day))
            else:
                sdt = datetime.fromisoformat(start_str)
                edt = datetime.fromisoformat(end_str)
                self.start_date.setDate(QDate(sdt.year, sdt.month, sdt.day))
                self.end_date.setDate(QDate(edt.year, edt.month, edt.day))
                self.start_time.setTime(QTime(sdt.hour, sdt.minute))
                self.end_time.setTime(QTime(edt.hour, edt.minute))
        except ValueError:
            pass  # fall back to dialog defaults if the API gave us something odd

    def get_values(self) -> dict:
        """Returns dict ready to pass into google_service.create_event /
        update_event as keyword-ish data: title, description, start (dt),
        end (dt), all_day (bool)."""
        title = self.title_input.text().strip() or "(no title)"
        description = self.description_input.toPlainText().strip()
        all_day = self.all_day_checkbox.isChecked()

        sd = self.start_date.date().toPython()
        ed = self.end_date.date().toPython()

        if all_day:
            # Google Calendar's all-day "end" is exclusive, so add a day.
            start_dt = datetime.combine(sd, time.min)
            end_dt = datetime.combine(ed + timedelta(days=1), time.min)
        else:
            st = self.start_time.time().toPython()
            et = self.end_time.time().toPython()
            start_dt = datetime.combine(sd, st)
            end_dt = datetime.combine(ed, et)

        return {
            "title": title,
            "description": description,
            "start": start_dt,
            "end": end_dt,
            "all_day": all_day,
        }
