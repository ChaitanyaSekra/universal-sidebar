"""
storage/settings_store.py

Wraps the generic `settings` key/value table with simple get/set helpers
and the specific defaults this app needs (theme, sidebar width/state,
last opened module, hotkeys). Every value is stored as TEXT in SQLite, so
this layer also handles the str <-> int/bool conversion so callers can
just pass/receive native Python types.
"""

from storage.database import db
from core.config import DEFAULT_THEME, DEFAULT_SIDEBAR_WIDTH, DEFAULT_TOGGLE_HOTKEY, \
    DEFAULT_COMMAND_PALETTE_HOTKEY


_DEFAULTS = {
    "theme": DEFAULT_THEME,
    "sidebar_width": str(DEFAULT_SIDEBAR_WIDTH),
    "sidebar_compact": "0",
    "last_module": "notes",
    "toggle_hotkey": DEFAULT_TOGGLE_HOTKEY,
    "command_palette_hotkey": DEFAULT_COMMAND_PALETTE_HOTKEY,
    "clipboard_max_items": "200",
}


def get(key: str) -> str:
    """Return the stored string value for `key`, falling back to the
    built-in default, and finally to an empty string if neither exists."""
    row = db.query_one("SELECT value FROM settings WHERE key = ?", (key,))
    if row is not None:
        return row["value"]
    return _DEFAULTS.get(key, "")


def get_int(key: str) -> int:
    return int(get(key))


def get_bool(key: str) -> bool:
    return get(key) == "1"


def set(key: str, value) -> None:
    """Upsert a setting. Booleans are stored as '1'/'0', everything else
    as str(value)."""
    if isinstance(value, bool):
        value = "1" if value else "0"
    else:
        value = str(value)
    db.execute(
        """
        INSERT INTO settings (key, value) VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value
        """,
        (key, value),
    )


def all_settings() -> dict:
    """Return every stored setting merged over the defaults -- useful for
    the Settings module to render a full picture in one call."""
    merged = dict(_DEFAULTS)
    for row in db.query("SELECT key, value FROM settings"):
        merged[row["key"]] = row["value"]
    return merged
