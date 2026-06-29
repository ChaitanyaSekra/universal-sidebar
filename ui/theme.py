"""
ui/theme.py

Turns the flat color dicts in core.config.THEMES into a Qt stylesheet
string. Centralizing this means every widget gets consistent rounded
corners, spacing, and colors for free just by using the right objectName,
instead of each module hand-rolling its own styling.
"""

from core.config import THEMES


def build_stylesheet(theme_name: str) -> str:
    t = THEMES.get(theme_name, THEMES["dark"])
    return f"""
    QWidget {{
        background-color: {t['bg']};
        color: {t['text']};
        font-family: 'Segoe UI', sans-serif;
        font-size: 13px;
    }}

    #SidebarRoot {{
        background-color: {t['bg']};
        border: 1px solid {t['border']};
    }}

    #NavRail {{
        background-color: {t['bg_elevated']};
        border-right: 1px solid {t['border']};
    }}

    #NavButton {{
        background-color: transparent;
        border: none;
        border-radius: 10px;
        color: {t['text_muted']};
        font-weight: 600;
    }}

    #NavButton:hover {{
        background-color: {t['bg_hover']};
        color: {t['text']};
    }}

    #NavButton:checked {{
        background-color: {t['accent']};
        color: #ffffff;
    }}

    #TitleBar {{
        background-color: {t['bg_elevated']};
        border-bottom: 1px solid {t['border']};
    }}

    QPushButton {{
        background-color: {t['accent']};
        color: #ffffff;
        border: none;
        border-radius: 8px;
        padding: 6px 12px;
    }}

    QPushButton:hover {{
        background-color: {t['accent_hover']};
    }}

    QPushButton#DangerButton {{
        background-color: {t['danger']};
    }}

    QLineEdit, QTextEdit, QPlainTextEdit, QListWidget, QCalendarWidget {{
        background-color: {t['bg_elevated']};
        border: 1px solid {t['border']};
        border-radius: 8px;
        padding: 6px;
        selection-background-color: {t['accent']};
    }}

    QScrollBar:vertical {{
        background: transparent;
        width: 8px;
    }}

    QScrollBar::handle:vertical {{
        background: {t['border']};
        border-radius: 4px;
        min-height: 24px;
    }}

    QLabel#MutedLabel {{
        color: {t['text_muted']};
    }}

    /* -- Notes module ------------------------------------------------ */

    #NotesListPanel {{
        background-color: {t['bg_elevated']};
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
        margin-bottom: 4px;
    }}

    #NoteCard {{
        background-color: {t['bg']};
        border: 1px solid {t['border']};
        border-radius: 10px;
    }}

    #NoteList::item:selected #NoteCard,
    #NoteCard:hover {{
        border: 1px solid {t['accent']};
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
    }}

    QPushButton#IconButton {{
        background-color: {t['bg_elevated']};
        color: {t['text']};
        border: 1px solid {t['border']};
        border-radius: 8px;
        padding: 6px;
    }}

    QPushButton#IconButton:hover {{
        background-color: {t['bg_hover']};
    }}
    """