"""
ui/theme.py

Builds the app-wide Qt stylesheet from a single PALETTE dict below, so
every widget gets consistent surfaces, spacing, and color just by using
the right objectName.

This is a self-contained rewrite of the previous version (which pulled
colors from core.config.THEMES). The "rich dashboard" redesign uses a
layered-surface palette (BASE -> SURFACE_1 -> SURFACE_2) instead of the
old flat bg/bg_elevated pair, plus a single indigo ACCENT, a TEAL used
only for "saved / success" states, and CORAL reserved only for
destructive actions -- so color carries meaning instead of being
decorative. If you want theme-name switching back (e.g. a light theme),
add a second dict here and pick between them in build_stylesheet();
nothing else in the app needs to change since callers just pass a
theme_name string through.
"""

PALETTE = {
    "base": "#13141a",          # page / window background
    "surface_1": "#1a1c24",     # nav rail, title bar, panels
    "surface_2": "#272a38",     # cards, inputs, raised content
    "surface_3": "#15161c",     # recessed content (editor body)
    "border": "#2e3040",
    "border_strong": "#3a3d52",
    "text": "#e8e7f0",
    "text_secondary": "#c5c4cc",
    "text_muted": "#8b8a94",
    "accent": "#6b66e0",
    "accent_hover": "#5a56c9",
    "accent_bg": "#272a38",     # accent-tinted card bg (e.g. active note card)
    "accent_fg": "#cdcaf7",     # accent color used for icons/text on dark bg
    "success": "#1d9e75",
    "success_bg": "#16261f",
    "danger": "#a32d2d",
    "danger_bg": "#3a1f1f",
    "danger_fg": "#e0807e",
}


def build_stylesheet(theme_name: str = "dark") -> str:
    t = PALETTE
    return f"""
    QWidget {{
        background-color: {t['base']};
        color: {t['text']};
        font-family: 'Segoe UI', sans-serif;
        font-size: 13px;
    }}

    #SidebarRoot {{
        background-color: {t['base']};
        border: 1px solid {t['border']};
        border-radius: 12px;
    }}

    /* -- Nav rail ------------------------------------------------------- */

    #NavRail {{
        background-color: {t['surface_1']};
        border-right: 1px solid {t['border']};
    }}

    #NavBrand {{
        background-color: {t['accent_bg']};
        border: none;
        border-radius: 10px;
    }}

    #NavButton {{
        background-color: transparent;
        border: none;
        border-radius: 10px;
        color: {t['text_muted']};
        font-weight: 500;
        text-align: left;
        padding-left: 10px;
    }}

    #NavButton:hover {{
        background-color: {t['surface_2']};
        color: {t['text']};
    }}

    #NavButton:checked {{
        background-color: {t['surface_2']};
        border: 1px solid {t['accent_hover']};
        color: {t['accent_fg']};
    }}

    /* -- Title bar ------------------------------------------------------- */

    #TitleBar {{
        background-color: {t['surface_1']};
        border-bottom: 1px solid {t['border']};
        border-top-left-radius: 12px;
        border-top-right-radius: 12px;
    }}

    QLabel#TitleBarLabel {{
        color: {t['text']};
        font-weight: 500;
        font-size: 13px;
    }}

    QPushButton#TitleBarIconButton {{
        background-color: transparent;
        border: none;
        border-radius: 8px;
        padding: 4px;
    }}

    QPushButton#TitleBarIconButton:hover {{
        background-color: {t['surface_2']};
    }}

    QPushButton#TitleBarIconButton[danger="true"]:hover {{
        background-color: {t['danger_bg']};
    }}

    /* -- General buttons -------------------------------------------------- */

    QPushButton {{
        background-color: {t['accent']};
        color: #ffffff;
        border: none;
        border-radius: 8px;
        padding: 6px 12px;
        font-weight: 500;
    }}

    QPushButton:hover {{
        background-color: {t['accent_hover']};
    }}

    QPushButton:disabled {{
        background-color: {t['surface_2']};
        color: {t['text_muted']};
    }}

    QPushButton#DangerButton {{
        background-color: {t['danger']};
    }}

    QPushButton#SecondaryButton {{
        background-color: {t['surface_2']};
        color: {t['text']};
        border: 1px solid {t['border']};
    }}

    QPushButton#SecondaryButton:hover {{
        background-color: {t['surface_2']};
        border: 1px solid {t['border_strong']};
    }}

    QPushButton#IconButton {{
        background-color: {t['surface_2']};
        border: 1px solid {t['border']};
        border-radius: 8px;
        padding: 6px;
    }}

    QPushButton#IconButton:hover {{
        border: 1px solid {t['border_strong']};
    }}

    QPushButton#IconButton[active="true"] {{
        background-color: {t['success_bg']};
        border: 1px solid {t['success']};
    }}

    QPushButton#IconButton[danger="true"]:hover {{
        background-color: {t['danger_bg']};
        border: 1px solid {t['danger']};
    }}

    /* -- Inputs / lists ---------------------------------------------------- */

    QLineEdit, QTextEdit, QPlainTextEdit, QListWidget, QCalendarWidget {{
        background-color: {t['surface_2']};
        border: 1px solid {t['border']};
        border-radius: 8px;
        padding: 6px;
        selection-background-color: {t['accent']};
    }}

    QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
        border: 1px solid {t['accent_hover']};
    }}

    QScrollBar:vertical {{
        background: transparent;
        width: 8px;
    }}

    QScrollBar::handle:vertical {{
        background: {t['border_strong']};
        border-radius: 4px;
        min-height: 24px;
    }}

    QLabel#MutedLabel {{
        color: {t['text_muted']};
    }}

    QLabel#SavedBadge {{
        color: {t['success']};
        background-color: {t['success_bg']};
        border-radius: 6px;
        padding: 3px 9px;
        font-size: 11px;
    }}

    /* -- Notes module ------------------------------------------------ */

    #NotesListPanel {{
        background-color: {t['surface_1']};
        border-right: 1px solid {t['border']};
    }}

    #NoteList {{
        background-color: transparent;
        border: none;
        padding: 0px;
    }}

    #NoteList::item {{
        border: none;
        padding: 0px;
        margin-bottom: 6px;
    }}

    #NoteCard {{
        background-color: {t['surface_2']};
        border: 1px solid transparent;
        border-radius: 10px;
    }}

    #NoteList::item:selected #NoteCard,
    #NoteCard:hover {{
        border: 1px solid {t['accent_hover']};
    }}

    QLabel#NoteCardTitle {{
        color: {t['text']};
    }}

    QLabel#NoteCardSnippet {{
        color: {t['text_muted']};
        font-size: 11px;
    }}

    QLabel#NoteCardTime {{
        color: {t['text_muted']};
        font-size: 10px;
    }}

    QLineEdit#NoteTitleInput {{
        background-color: transparent;
        border: none;
        border-radius: 0px;
        padding: 2px 0px;
        font-size: 16px;
    }}

    QTextEdit#NoteBodyEdit {{
        background-color: {t['surface_3']};
    }}

    /* -- Calculator module ------------------------------------------- */

    QPushButton#CalcDigit {{
        background-color: {t['surface_2']};
        color: {t['text']};
        border: 1px solid {t['border']};
    }}

    QPushButton#CalcDigit:hover {{
        background-color: {t['surface_2']};
        border: 1px solid {t['border_strong']};
    }}

    QPushButton#CalcOperator {{
        background-color: {t['surface_1']};
        color: {t['accent_fg']};
        border: 1px solid {t['border']};
    }}

    QPushButton#CalcEquals {{
        background-color: {t['accent']};
        color: #ffffff;
        border: none;
    }}

    QLineEdit#CalcDisplay {{
        background-color: {t['surface_3']};
        border: 1px solid {t['border']};
        font-size: 22px;
    }}

    /* -- Calendar module ------------------------------------------- */

    QCalendarWidget QAbstractItemView {{
        background-color: {t['surface_2']};
        selection-background-color: {t['accent']};
    }}

    QCalendarWidget QToolButton {{
        background-color: transparent;
        color: {t['text']};
    }}
    """
