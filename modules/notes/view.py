"""
modules/notes/view.py

Full Notes module: a left card-list of all notes (search, pin, new,
delete) and a right-hand editor (inline-editable title + body) that
autosaves on a debounce timer instead of requiring a manual save button.
A small status label in the editor header reflects save state ("Editing..."
-> "Saved HH:MM"), which is the "feels like an agent quietly keeping up
with you" behavior the rest of the app's modules don't have yet.

Layout:
    QHBoxLayout
      |-- list panel (search box, new/delete row, QListWidget of cards)
      |-- editor panel (title input, status label, pin/delete, QTextEdit)
"""

from datetime import datetime

from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QListWidget, QListWidgetItem, QTextEdit, QSizePolicy, QGraphicsOpacityEffect,
    QMessageBox, QFrame,
)

from modules.base_module import BaseModule
from modules.notes import storage as notes_storage

AUTOSAVE_DELAY_MS = 800

# Rotated through for new notes so the list doesn't look monotone -- purely
# cosmetic, stored in the existing `color` column.
ACCENT_PALETTE = ["#7c8cff", "#5fd1a0", "#f5a623", "#ff7a9c", "#5bc0de", "#b48cff"]


class NoteCard(QWidget):
    """One row in the note list. A plain QWidget (not a QListWidgetItem
    subclass) so we can lay out an accent strip + title + snippet + time
    instead of being stuck with QListWidgetItem's single-line text."""

    def __init__(self, note_row, parent=None):
        super().__init__(parent)
        self.note_id = note_row["id"]
        self.setObjectName("NoteCard")

        outer = QHBoxLayout(self)
        outer.setContentsMargins(10, 8, 10, 8)
        outer.setSpacing(8)

        strip = QFrame()
        strip.setFixedWidth(4)
        strip.setStyleSheet(
            f"background-color: {note_row['color'] or '#7c8cff'}; border-radius: 2px;"
        )
        outer.addWidget(strip)

        text_col = QVBoxLayout()
        text_col.setSpacing(2)

        title = note_row["title"] or "Untitled"
        title_label = QLabel(title)
        title_label.setObjectName("NoteCardTitle")
        title_font = QFont("Segoe UI", 10)
        title_font.setBold(True)
        title_label.setFont(title_font)
        text_col.addWidget(title_label)

        snippet_text = (note_row["body"] or "").strip().replace("\n", " ")
        if len(snippet_text) > 60:
            snippet_text = snippet_text[:60] + "..."
        snippet_label = QLabel(snippet_text or "No content yet")
        snippet_label.setObjectName("NoteCardSnippet")
        text_col.addWidget(snippet_label)

        time_label = QLabel(_relative_time(note_row["updated_at"]))
        time_label.setObjectName("NoteCardTime")
        text_col.addWidget(time_label)

        outer.addLayout(text_col, 1)

        if note_row["pinned"]:
            pin_indicator = QLabel("\U0001F4CC")
            pin_indicator.setObjectName("NoteCardPinIcon")
            outer.addWidget(pin_indicator, 0, Qt.AlignTop)


def _relative_time(iso_str: str) -> str:
    try:
        dt = datetime.fromisoformat(iso_str)
    except (TypeError, ValueError):
        return ""
    now = datetime.now()
    delta = now - dt
    if delta.days == 0 and now.day == dt.day:
        return f"Today - {dt.strftime('%H:%M')}"
    if delta.days == 1 or (delta.days == 0 and now.day != dt.day):
        return f"Yesterday - {dt.strftime('%H:%M')}"
    if delta.days < 7:
        return dt.strftime("%A")
    return dt.strftime("%d %b %Y")


class NotesModule(BaseModule):
    MODULE_KEY = "notes"
    MODULE_LABEL = "Notes"

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_note_id = None
        self._loading = False  # guards against autosave firing while we load a note
        self._palette_cursor = 0

        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.timeout.connect(self._save_current_note)

        self._build_ui()
        self._refresh_list(select_first=True)
        self.setFocusPolicy(Qt.StrongFocus)

    # -- UI construction --------------------------------------------------

    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_list_panel())
        root.addWidget(self._build_editor_panel(), 1)

    def _build_list_panel(self):
        panel = QWidget()
        panel.setObjectName("NotesListPanel")
        panel.setFixedWidth(220)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(10, 10, 6, 10)
        layout.setSpacing(8)

        top_row = QHBoxLayout()
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search notes...")
        self.search_box.textChanged.connect(lambda _: self._refresh_list())
        top_row.addWidget(self.search_box)

        new_btn = QPushButton("+")
        new_btn.setObjectName("IconButton")
        new_btn.setFixedWidth(32)
        new_btn.setToolTip("New note (Ctrl+N)")
        new_btn.clicked.connect(self._new_note)
        top_row.addWidget(new_btn)
        layout.addLayout(top_row)

        self.note_list = QListWidget()
        self.note_list.setObjectName("NoteList")
        self.note_list.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        self.note_list.itemClicked.connect(self._on_card_clicked)
        layout.addWidget(self.note_list, 1)

        return panel

    def _build_editor_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)

        header = QHBoxLayout()
        self.title_input = QLineEdit()
        self.title_input.setObjectName("NoteTitleInput")
        title_font = QFont("Segoe UI", 16)
        title_font.setBold(True)
        self.title_input.setFont(title_font)
        self.title_input.setPlaceholderText("Untitled")
        self.title_input.textEdited.connect(self._on_content_changed)
        header.addWidget(self.title_input, 1)

        self.pin_btn = QPushButton("\U0001F4CC")
        self.pin_btn.setObjectName("IconButton")
        self.pin_btn.setFixedWidth(32)
        self.pin_btn.setToolTip("Pin / unpin")
        self.pin_btn.clicked.connect(self._toggle_pin)
        header.addWidget(self.pin_btn)

        delete_btn = QPushButton("Delete")
        delete_btn.setObjectName("DangerButton")
        delete_btn.clicked.connect(self._delete_current_note)
        header.addWidget(delete_btn)
        layout.addLayout(header)

        status_row = QHBoxLayout()
        self.status_label = QLabel("")
        self.status_label.setObjectName("MutedLabel")
        self._status_opacity = QGraphicsOpacityEffect(self.status_label)
        self.status_label.setGraphicsEffect(self._status_opacity)
        self._status_opacity.setOpacity(1.0)
        self._status_anim = QPropertyAnimation(self._status_opacity, b"opacity")
        self._status_anim.setDuration(900)
        self._status_anim.setEasingCurve(QEasingCurve.InOutQuad)
        status_row.addWidget(self.status_label)
        status_row.addStretch(1)
        layout.addLayout(status_row)

        self.body_edit = QTextEdit()
        self.body_edit.setPlaceholderText("Start typing...")
        self.body_edit.setFont(QFont("Segoe UI", 11))
        self.body_edit.textChanged.connect(self._on_content_changed)
        layout.addWidget(self.body_edit, 1)

        self.empty_state = QLabel("No notes yet -- click + to create one.")
        self.empty_state.setObjectName("MutedLabel")
        self.empty_state.setAlignment(Qt.AlignCenter)
        self.empty_state.hide()
        layout.addWidget(self.empty_state)

        return panel

    # -- list management --------------------------------------------------

    def _refresh_list(self, select_first: bool = False):
        query = self.search_box.text() if hasattr(self, "search_box") else ""
        rows = notes_storage.list_notes(query)

        self.note_list.clear()
        for row in rows:
            item = QListWidgetItem()
            item.setData(Qt.UserRole, row["id"])
            card = NoteCard(row)
            item.setSizeHint(card.sizeHint())
            self.note_list.addItem(item)
            self.note_list.setItemWidget(item, card)

        if not rows:
            self._current_note_id = None
            self._set_editor_enabled(False)
            return

        self._set_editor_enabled(True)
        if select_first or self._current_note_id is None:
            self.note_list.setCurrentRow(0)
            self._load_note(rows[0]["id"])
        else:
            found = False
            for i in range(self.note_list.count()):
                if self.note_list.item(i).data(Qt.UserRole) == self._current_note_id:
                    self.note_list.setCurrentRow(i)
                    found = True
                    break
            if not found:
                self.note_list.setCurrentRow(0)
                self._load_note(rows[0]["id"])

    def _set_editor_enabled(self, enabled: bool):
        self.title_input.setEnabled(enabled)
        self.body_edit.setEnabled(enabled)
        self.pin_btn.setEnabled(enabled)
        self.empty_state.setVisible(not enabled)
        self.title_input.setVisible(enabled)
        self.body_edit.setVisible(enabled)
        if not enabled:
            self.title_input.clear()
            self.body_edit.clear()
            self.status_label.setText("")

    def _on_card_clicked(self, item: QListWidgetItem):
        note_id = item.data(Qt.UserRole)
        if note_id != self._current_note_id:
            self._save_current_note()  # flush any pending edit before switching
            self._load_note(note_id)

    # -- editor <-> storage --------------------------------------------------

    def _load_note(self, note_id: int):
        row = notes_storage.get_note(note_id)
        if row is None:
            return
        self._loading = True
        self._current_note_id = note_id
        self.title_input.setText(row["title"])
        self.body_edit.setPlainText(row["body"])
        self._set_status_saved(row["updated_at"])
        self._loading = False

    def _on_content_changed(self):
        if self._loading or self._current_note_id is None:
            return
        self.status_label.setText("Editing...")
        self._status_anim.stop()
        self._status_opacity.setOpacity(1.0)
        self._save_timer.start(AUTOSAVE_DELAY_MS)

    def _save_current_note(self):
        if self._current_note_id is None:
            return
        title = self.title_input.text().strip() or "Untitled"
        body = self.body_edit.toPlainText()
        notes_storage.update_note(self._current_note_id, title=title, body=body)
        self._set_status_saved(datetime.now().isoformat(timespec="seconds"))
        self._refresh_current_card()

    def _refresh_current_card(self):
        """Update just the one card's text (title/snippet/time) without
        rebuilding and re-selecting the whole list, so typing doesn't
        cause the list to jump around under the cursor."""
        row = notes_storage.get_note(self._current_note_id)
        if row is None:
            return
        for i in range(self.note_list.count()):
            item = self.note_list.item(i)
            if item.data(Qt.UserRole) == self._current_note_id:
                card = NoteCard(row)
                item.setSizeHint(card.sizeHint())
                self.note_list.setItemWidget(item, card)
                break

    def _set_status_saved(self, iso_timestamp: str):
        try:
            dt = datetime.fromisoformat(iso_timestamp)
            self.status_label.setText(f"Saved - {dt.strftime('%H:%M')}")
        except (TypeError, ValueError):
            self.status_label.setText("Saved")
        self._status_anim.stop()
        self._status_opacity.setOpacity(1.0)
        self._status_anim.setStartValue(1.0)
        self._status_anim.setEndValue(0.45)
        self._status_anim.start()

    # -- actions -----------------------------------------------------

    def _new_note(self):
        self._save_current_note()
        new_id = notes_storage.create_note("Untitled")
        # tag with a rotating accent color for visual variety in the list
        self._palette_cursor = (self._palette_cursor + 1) % len(ACCENT_PALETTE)
        from storage.database import db
        db.execute(
            "UPDATE notes SET color = ? WHERE id = ?",
            (ACCENT_PALETTE[self._palette_cursor], new_id),
        )
        self.search_box.clear()
        self._current_note_id = new_id
        self._refresh_list(select_first=False)
        for i in range(self.note_list.count()):
            if self.note_list.item(i).data(Qt.UserRole) == new_id:
                self.note_list.setCurrentRow(i)
                break
        self._load_note(new_id)
        self.title_input.setFocus()
        self.title_input.selectAll()

    def _delete_current_note(self):
        if self._current_note_id is None:
            return
        confirm = QMessageBox.question(
            self, "Delete note", "Delete this note? This can't be undone.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            return
        notes_storage.delete_note(self._current_note_id)
        self._save_timer.stop()
        self._current_note_id = None
        self._refresh_list(select_first=True)

    def _toggle_pin(self):
        if self._current_note_id is None:
            return
        notes_storage.toggle_pin(self._current_note_id)
        self._refresh_list(select_first=False)

    # -- keyboard / lifecycle -----------------------------------------------------

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_N and event.modifiers() & Qt.ControlModifier:
            self._new_note()
        elif event.key() == Qt.Key_F and event.modifiers() & Qt.ControlModifier:
            self.search_box.setFocus()
            self.search_box.selectAll()
        else:
            super().keyPressEvent(event)

    def on_shown(self):
        self._refresh_list(select_first=self._current_note_id is None)

    def hideEvent(self, event):
        # flush a pending debounced save if the user navigates away mid-edit
        if self._save_timer.isActive():
            self._save_timer.stop()
            self._save_current_note()
        super().hideEvent(event)