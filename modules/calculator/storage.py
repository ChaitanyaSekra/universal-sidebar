"""
modules/calculator/storage.py

Thin wrapper over the `calc_history` table (already created in
storage/database.py). Kept separate from engine.py so the math logic has
zero knowledge of persistence -- the engine could be unit tested or reused
with no database at all.
"""

from datetime import datetime

from storage.database import db


def add_entry(expression: str, result: str) -> None:
    db.execute(
        "INSERT INTO calc_history (expression, result, created_at) VALUES (?, ?, ?)",
        (expression, result, datetime.now().isoformat(timespec="seconds")),
    )


def list_entries(limit: int = 100):
    return db.query(
        "SELECT expression, result, created_at FROM calc_history "
        "ORDER BY id DESC LIMIT ?",
        (limit,),
    )


def clear_history() -> None:
    db.execute("DELETE FROM calc_history")
