"""
modules/notes/view.py

Redesigned layout (v3): the old fixed 230px side-by-side list panel is gone.
Notes now live behind a single horizontal search bar at the top -- typing
or clicking it drops down a floating list of matching notes (most-recent-
first, like a command palette / combobox), and picking one loads it into
an editor that now owns the *entire* remaining width and height. This
fixes the "cards and editor fighting for space" problem at its root by
removing the permanent side panel instead of trying to make it narrower.

How the dropdown works:
  - `self._dropdown` is a QFrame parented directly to the module (not laid
    out by a QLayout), manually positioned with setGeometry() right under
    the search bar and raised above the editor -- this is what gives the
    "floats over the content" combobox feel instead of pushing the editor
    down.
  - It opens on search-box focus-in or on text change, and closes on:
    Escape, picking a note, or a mouse press anywhere outside the search
    bar + dropdown (handled via an eventFilter installed on the app so we
    catch clicks on any descendant widget, not just this module).
  - The dropdown reuses NoteCard (now takes a `compact` flag for a tighter
    row height appropriate to a dropdown list vs. the old full list).

Layout:
    QVBoxLayout
      |-- top bar (search box w/ leading search icon, + new-note button)
      |-- [floating, not in layout] dropdown of matching notes
      |-- editor (title input, status badge, pin/delete, body), full width/height
"""

from datetime import datetime

from PySide6.QtCore import QEvent, QObject, Qt, QTimer, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QListWidget, QListWidgetItem, QTextEdit, QSizePolicy,
    QGraphicsOpacityEffect, QMessageBox, QFrame,
)

from modules.base_module import BaseModule
from modules.notes import storage as notes_storage
from ui.icon_loader import get_icon, icon_size
from ui.theme import PALETTE

AUTOSAVE_DELAY_MS = 800
ICON_PX = 16
DROPDOWN_MAX_HEIGHT = 280

# Rotated through for new notes so the list doesn't look monotone -- purely
# cosmetic, stored in the existing `color` column.
ACCENT_PALETTE = ["#7c8cff", "#5fd1a0", "#f5a623", "#ff7a9c", "#5bc0de", "#b48cff"]


class NoteCard(QWidget):
    """One row, used both in the dropdown (compact=True, tighter padding,
    no time label) and anywhere else a full note summary is wanted."""

    def __init__(self, note_row, compact: bool = False, parent=None):
        super().__init__(parent)
        self.note_id = note_row["id"]
        self.setObjectName("NoteCard")

        outer = QHBoxLayout(self)
        v_pad = 6 if compact else 10
        outer.setContentsMargins(12, v_pad, 12, v_pad)
        outer.setSpacing(10)

        strip = QFrame()
        strip.setFixedWidth(4)
        strip.setStyleSheet(
            f"background-color: {note_row['color'] or '#7c8cff'}; border-radius: 2px;"
        )
        outer.addWidget(strip)

        text_col = QVBoxLayout()
        text_col.setSpacing(2 if compact else 3)

        title = note_row["title"] or "Untitled"
        title_label = QLabel(title)
        title_label.setObjectName("NoteCardTitle")
        title_font = QFont("Segoe UI", 10)
        title_font.setBold(True)
        title_label.setFont(title_font)
        text_col.addWidget(title_label)

        snippet_text = (note_row["body"] or "").strip().replace("\n", " ")
        max_len = 50 if compact else 60
        if len(snippet_text) > max_len:
            snippet_text = snippet_text[:max_len] + "..."
        snippet_label = QLabel(snippet_text or "No content yet")
        snippet_label.setObjectName("NoteCardSnippet")
        text_col.addWidget(snippet_label)

        if not compact:
            time_label = QLabel(_relative_time(note_row["updated_at"]))
            time_label.setObjectName("NoteCardTime")
            text_col.addWidget(time_label)

        outer.addLayout(text_col, 1)

        if note_row["pinned"]:
            pin_indicator = QLabel()
            pin_indicator.setPixmap(
                get_icon("pin-filled", PALETTE["success"], 14).pixmap(icon_size(14))
            )
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
        self._dropdown_open = False

        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.timeout.connect(self._save_current_note)

        self._build_ui()
        self._refresh_dropdown_list()
        self._load_most_recent_or_empty()
        self.setFocusPolicy(Qt.StrongFocus)

        # Catches clicks anywhere in the app so the dropdown can close when
        # you click outside it -- a plain mousePressEvent override on this
        # widget alone wouldn't see clicks that land on sibling modules or
        # the title bar, since those are different widgets entirely.
        self._outside_click_filter = _OutsideClickCloser(self)
        QApplication.instance().installEventFilter(self._outside_click_filter)

    # -- UI construction --------------------------------------------------

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 14, 16, 14)
        root.setSpacing(10)

        root.addLayout(self._build_top_bar())
        root.addWidget(self._build_editor_panel(), 1)

        self._build_dropdown()  # floating, added as a raw child, not to `root`

    def _build_top_bar(self):
        top_row = QHBoxLayout()
        top_row.setSpacing(8)

        self.search_box = QLineEdit()
        self.search_box.setObjectName("NotesSearchBar")
        self.search_box.setPlaceholderText("Search or pick a note...")
        self.search_box.addAction(
            get_icon("search", PALETTE["text_muted"], 14), QLineEdit.LeadingPosition
        )
        self.search_box.textChanged.connect(self._on_search_text_changed)
        self.search_box.installEventFilter(self)
        top_row.addWidget(self.search_box, 1)

        self.dropdown_toggle_btn = QPushButton()
        self.dropdown_toggle_btn.setObjectName("IconButton")
        self.dropdown_toggle_btn.setIcon(get_icon("chevron-right", PALETTE["text_muted"], ICON_PX))
        self.dropdown_toggle_btn.setIconSize(icon_size(ICON_PX))
        self.dropdown_toggle_btn.setFixedSize(38, 38)
        self.dropdown_toggle_btn.setToolTip("Browse all notes")
        self.dropdown_toggle_btn.clicked.connect(self._toggle_dropdown)
        top_row.addWidget(self.dropdown_toggle_btn)

        new_btn = QPushButton()
        new_btn.setObjectName("IconButton")
        new_btn.setIcon(get_icon("plus", PALETTE["accent_fg"], ICON_PX))
        new_btn.setIconSize(icon_size(ICON_PX))
        new_btn.setFixedSize(38, 38)
        new_btn.setToolTip("New note (Ctrl+N)")
        new_btn.clicked.connect(self._new_note)
        top_row.addWidget(new_btn)

        return top_row

    def _build_dropdown(self):
        self._dropdown = QFrame(self)
        self._dropdown.setObjectName("NotesDropdown")
        self._dropdown.setMaximumHeight(DROPDOWN_MAX_HEIGHT)
        dd_layout = QVBoxLayout(self._dropdown)
        dd_layout.setContentsMargins(4, 4, 4, 4)
        dd_layout.setSpacing(0)

        self.dropdown_list = QListWidget()
        self.dropdown_list.setObjectName("NoteList")
        self.dropdown_list.itemClicked.connect(self._on_dropdown_item_clicked)
        dd_layout.addWidget(self.dropdown_list)

        self._dropdown.hide()

    def _build_editor_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 4, 0, 0)
        layout.setSpacing(10)

        header = QHBoxLayout()
        header.setSpacing(8)

        self.title_input = QLineEdit()
        self.title_input.setObjectName("NoteTitleInput")
        self.title_input.setMinimumWidth(0)
        title_font = QFont("Segoe UI", 18)
        title_font.setBold(True)
        self.title_input.setFont(title_font)
        self.title_input.setPlaceholderText("Untitled")
        self.title_input.textEdited.connect(self._on_content_changed)
        header.addWidget(self.title_input, 1)

        self.pin_btn = QPushButton()
        self.pin_btn.setObjectName("IconButton")
        self.pin_btn.setIcon(get_icon("pin", PALETTE["text_muted"], ICON_PX))
        self.pin_btn.setIconSize(icon_size(ICON_PX))
        self.pin_btn.setFixedSize(36, 36)
        self.pin_btn.setToolTip("Pin / unpin")
        self.pin_btn.clicked.connect(self._toggle_pin)
        header.addWidget(self.pin_btn)

        delete_btn = QPushButton()
        delete_btn.setObjectName("IconButton")
        delete_btn.setProperty("danger", "true")
        delete_btn.setIcon(get_icon("trash", PALETTE["danger_fg"], ICON_PX))
        delete_btn.setIconSize(icon_size(ICON_PX))
        delete_btn.setFixedSize(36, 36)
        delete_btn.setToolTip("Delete note")
        delete_btn.clicked.connect(self._delete_current_note)
        header.addWidget(delete_btn)
        layout.addLayout(header)

        status_row = QHBoxLayout()
        self.status_label = QLabel("")
        self.status_label.setObjectName("SavedBadge")
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
        self.body_edit.setObjectName("NoteBodyEdit")
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

    # -- dropdown open/close/positioning --------------------------------------

    def _toggle_dropdown(self):
        if self._dropdown_open:
            self._close_dropdown()
        else:
            self._refresh_dropdown_list()
            self._open_dropdown()

    def _open_dropdown(self):
        if self.dropdown_list.count() == 0:
            return
        self._position_dropdown()
        self._dropdown.show()
        self._dropdown.raise_()
        self._dropdown_open = True
        self.dropdown_toggle_btn.setIcon(
            get_icon("chevron-left", PALETTE["accent_fg"], ICON_PX)
        )

    def _close_dropdown(self):
        self._dropdown.hide()
        self._dropdown_open = False
        self.dropdown_toggle_btn.setIcon(
            get_icon("chevron-right", PALETTE["text_muted"], ICON_PX)
        )

    def _position_dropdown(self):
        # Anchors the floating panel directly under the search bar, spanning
        # from the search bar's left edge to the new-note button's right
        # edge, so it visually reads as "this dropped out of the search bar"
        # rather than a disconnected overlay.
        top_left = self.search_box.mapTo(self, self.search_box.rect().topLeft())
        width = self.dropdown_toggle_btn.geometry().right() - self.search_box.geometry().left()
        y = self.search_box.geometry().bottom() + 6
        available_height = max(120, self.height() - y - 12)
        height = min(DROPDOWN_MAX_HEIGHT, available_height)
        self._dropdown.setGeometry(top_left.x(), y, width, height)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._dropdown_open:
            self._position_dropdown()

    # -- search / dropdown contents --------------------------------------------

    def _on_search_text_changed(self, _text):
        self._refresh_dropdown_list()
        if not self._dropdown_open:
            self._open_dropdown()
        else:
            self._position_dropdown()

    def _refresh_dropdown_list(self):
        query = self.search_box.text()
        rows = notes_storage.list_notes(query)
        self.dropdown_list.clear()
        for row in rows:
            item = QListWidgetItem()
            item.setData(Qt.UserRole, row["id"])
            card = NoteCard(row, compact=True)
            item.setSizeHint(card.sizeHint())
            self.dropdown_list.addItem(item)
            self.dropdown_list.setItemWidget(item, card)

    def _on_dropdown_item_clicked(self, item: QListWidgetItem):
        note_id = item.data(Qt.UserRole)
        self._save_current_note()  # flush any pending edit before switching
        self._load_note(note_id)
        self.search_box.clear()
        self._close_dropdown()
        self.title_input.setFocus()

    def eventFilter(self, obj, event):
        if obj is self.search_box and event.type() == QEvent.FocusIn:
            self._refresh_dropdown_list()
            self._open_dropdown()
        elif obj is self.search_box and event.type() == QEvent.KeyPress:
            if event.key() == Qt.Key_Escape:
                self._close_dropdown()
                self.search_box.clearFocus()
        return super().eventFilter(obj, event)

    # -- editor <-> storage --------------------------------------------------

    def _load_most_recent_or_empty(self):
        rows = notes_storage.list_notes("")
        if rows:
            self._load_note(rows[0]["id"])
        else:
            self._set_editor_enabled(False)

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

    def _load_note(self, note_id: int):
        row = notes_storage.get_note(note_id)
        if row is None:
            return
        self._set_editor_enabled(True)
        self._loading = True
        self._current_note_id = note_id
        self.title_input.setText(row["title"])
        self.body_edit.setPlainText(row["body"])
        self._set_status_saved(row["updated_at"])
        self._update_pin_button(bool(row["pinned"]))
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

    def _set_status_saved(self, iso_timestamp: str):
        try:
            dt = datetime.fromisoformat(iso_timestamp)
            self.status_label.setText(f"Saved {dt.strftime('%H:%M')}")
        except (TypeError, ValueError):
            self.status_label.setText("Saved")
        self._status_anim.stop()
        self._status_opacity.setOpacity(1.0)
        self._status_anim.setStartValue(1.0)
        self._status_anim.setEndValue(0.45)
        self._status_anim.start()

    def _update_pin_button(self, pinned: bool):
        icon_name = "pin-filled" if pinned else "pin"
        color = PALETTE["success"] if pinned else PALETTE["text_muted"]
        self.pin_btn.setIcon(get_icon(icon_name, color, ICON_PX))
        self.pin_btn.setProperty("active", "true" if pinned else "false")
        self.pin_btn.style().unpolish(self.pin_btn)
        self.pin_btn.style().polish(self.pin_btn)

    # -- actions -----------------------------------------------------

    def _new_note(self):
        self._save_current_note()
        new_id = notes_storage.create_note("Untitled")
        self._palette_cursor = (self._palette_cursor + 1) % len(ACCENT_PALETTE)
        from storage.database import db
        db.execute(
            "UPDATE notes SET color = ? WHERE id = ?",
            (ACCENT_PALETTE[self._palette_cursor], new_id),
        )
        self.search_box.clear()
        self._close_dropdown()
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
        self._load_most_recent_or_empty()

    def _toggle_pin(self):
        if self._current_note_id is None:
            return
        notes_storage.toggle_pin(self._current_note_id)
        row = notes_storage.get_note(self._current_note_id)
        if row is not None:
            self._update_pin_button(bool(row["pinned"]))

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
        if self._current_note_id is None:
            self._load_most_recent_or_empty()

    def hideEvent(self, event):
        # flush a pending debounced save if the user navigates away mid-edit
        if self._save_timer.isActive():
            self._save_timer.stop()
            self._save_current_note()
        self._close_dropdown()
        super().hideEvent(event)

    def closeEvent(self, event):
        QApplication.instance().removeEventFilter(self._outside_click_filter)
        super().closeEvent(event)


class _OutsideClickCloser(QObject):
    """Installed on the whole QApplication (not just NotesModule) so a
    click on a completely unrelated widget -- another module, the title
    bar, the nav rail -- still closes the dropdown. A mousePressEvent
    override on NotesModule itself would only see clicks that land inside
    NotesModule's own widget tree."""

    def __init__(self, module: "NotesModule"):
        super().__init__(module)
        self._module = module

    def eventFilter(self, obj, event):
        if event.type() == QEvent.MouseButtonPress and self._module._dropdown_open:
            pos = event.globalPosition().toPoint()
            dropdown = self._module._dropdown
            search_box = self._module.search_box
            toggle_btn = self._module.dropdown_toggle_btn
            inside = (
                dropdown.geometry().contains(dropdown.mapFromGlobal(pos))
                or search_box.rect().contains(search_box.mapFromGlobal(pos))
                or toggle_btn.rect().contains(toggle_btn.mapFromGlobal(pos))
            )
            if not inside:
                self._module._close_dropdown()
        return False
