"""
modules/notes/storage.py

Thin wrapper over the `notes` table (already created in
storage/database.py). Same separation-of-concerns pattern as
modules/calculator/storage.py -- the view never touches SQL directly.
"""

from datetime import datetime

from storage.database import db


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def create_note(title: str = "Untitled") -> int:
    now = _now()
    db.execute(
        "INSERT INTO notes (title, body, color, tags, pinned, created_at, updated_at) "
        "VALUES (?, '', '#7c8cff', '', 0, ?, ?)",
        (title, now, now),
    )
    return db.last_insert_id()


def list_notes(query: str = ""):
    """Pinned notes first, then most-recently-updated. `query` filters on
    title or body (case-insensitive substring match)."""
    if query.strip():
        like = f"%{query.strip()}%"
        return db.query(
            "SELECT id, title, body, color, tags, pinned, created_at, updated_at "
            "FROM notes WHERE title LIKE ? OR body LIKE ? "
            "ORDER BY pinned DESC, updated_at DESC",
            (like, like),
        )
    return db.query(
        "SELECT id, title, body, color, tags, pinned, created_at, updated_at "
        "FROM notes ORDER BY pinned DESC, updated_at DESC"
    )


def get_note(note_id: int):
    return db.query_one(
        "SELECT id, title, body, color, tags, pinned, created_at, updated_at "
        "FROM notes WHERE id = ?",
        (note_id,),
    )


def update_note(note_id: int, title: str = None, body: str = None) -> None:
    """Partial update -- only touches the fields actually passed in, and
    always bumps updated_at so the list re-sorts correctly."""
    fields, params = [], []
    if title is not None:
        fields.append("title = ?")
        params.append(title)
    if body is not None:
        fields.append("body = ?")
        params.append(body)
    if not fields:
        return
    fields.append("updated_at = ?")
    params.append(_now())
    params.append(note_id)
    db.execute(f"UPDATE notes SET {', '.join(fields)} WHERE id = ?", tuple(params))


def delete_note(note_id: int) -> None:
    db.execute("DELETE FROM notes WHERE id = ?", (note_id,))


def toggle_pin(note_id: int) -> None:
    db.execute(
        "UPDATE notes SET pinned = CASE WHEN pinned = 1 THEN 0 ELSE 1 END "
        "WHERE id = ?",
        (note_id,),
    )


def note_count() -> int:
    row = db.query_one("SELECT COUNT(*) AS c FROM notes")
    return row["c"] if row else 0