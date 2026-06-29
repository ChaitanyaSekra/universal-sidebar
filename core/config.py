"""
core/config.py

Central place for constants used across the whole app: where data lives on
disk, default hotkeys, sidebar geometry defaults, and theme color tokens.
Keeping these in one file means no module ever hardcodes a path or a magic
number that someone else has to hunt down later.
"""

import os

# ---------------------------------------------------------------------------
# Data location
# ---------------------------------------------------------------------------
# All persistent data (database, settings, exported files) lives under the
# user's APPDATA folder so the app behaves like a normal, well-behaved
# Windows application and survives reinstalls of the app code itself.
APP_NAME = "UniversalSidebar"
APP_DATA_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), APP_NAME)
DB_PATH = os.path.join(APP_DATA_DIR, "universal_sidebar.db")
EXPORT_DIR = os.path.join(APP_DATA_DIR, "exports")

# ---------------------------------------------------------------------------
# Hotkeys
# ---------------------------------------------------------------------------
DEFAULT_TOGGLE_HOTKEY = "ctrl+shift+s"
DEFAULT_COMMAND_PALETTE_HOTKEY = "ctrl+shift+p"

# ---------------------------------------------------------------------------
# Sidebar geometry defaults (used the very first time the app runs, before
# any user preference has been saved)
# ---------------------------------------------------------------------------
DEFAULT_SIDEBAR_WIDTH = 380
MIN_SIDEBAR_WIDTH = 300
MAX_SIDEBAR_WIDTH = 720
COMPACT_SIDEBAR_WIDTH = 64
SIDEBAR_ANIMATION_MS = 220

# ---------------------------------------------------------------------------
# Theme tokens
# ---------------------------------------------------------------------------
# Two flat palettes. The UI layer reads from whichever is active rather than
# hardcoding colors in widget code, so adding a third theme later only means
# adding a third dict here.
THEMES = {
    "dark": {
        "bg": "#1e1f26",
        "bg_elevated": "#262833",
        "bg_hover": "#323544",
        "border": "#3a3d4d",
        "text": "#e8e9ee",
        "text_muted": "#9a9cab",
        "accent": "#7c8cff",
        "accent_hover": "#909eff",
        "danger": "#ff6b6b",
        "success": "#5fd98a",
    },
    "light": {
        "bg": "#fafafc",
        "bg_elevated": "#ffffff",
        "bg_hover": "#f0f0f5",
        "border": "#e2e2ea",
        "text": "#1c1d24",
        "text_muted": "#6b6c7a",
        "accent": "#5b6cff",
        "accent_hover": "#4453e6",
        "danger": "#e0413f",
        "success": "#2c9c5e",
    },
}

DEFAULT_THEME = "dark"


def ensure_app_dirs():
    """Create the APPDATA folder structure on first run. Safe to call every
    startup -- os.makedirs with exist_ok is a no-op if the dirs exist."""
    os.makedirs(APP_DATA_DIR, exist_ok=True)
    os.makedirs(EXPORT_DIR, exist_ok=True)
