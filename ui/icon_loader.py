"""
ui/icon_loader.py

Loads the bundled Tabler outline icons (assets/icons/*.svg, MIT licensed)
and recolors them on demand. The SVGs ship with stroke="currentColor",
which Qt's QSvgRenderer can't resolve on its own (no CSS engine), so we
do a plain string substitution before rendering -- icons are <1KB each so
this is cheap, and results are cached by (name, color, size) since the
same icon/color combo gets requested repeatedly (e.g. every nav button
re-rendering its active/inactive state).
"""

from pathlib import Path

from PySide6.QtCore import QByteArray, QSize, Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

ICONS_DIR = Path(__file__).resolve().parent.parent / "assets" / "icons"

_cache: dict[tuple[str, str, int], QIcon] = {}


def get_icon(name: str, color: str, size: int = 20) -> QIcon:
    """Return a QIcon for assets/icons/{name}.svg recolored to `color`.

    Falls back to a blank icon (instead of raising) if the icon file is
    missing, so a typo in an icon name degrades to "no icon" rather than
    crashing the app.
    """
    key = (name, color, size)
    cached = _cache.get(key)
    if cached is not None:
        return cached

    svg_path = ICONS_DIR / f"{name}.svg"
    if not svg_path.exists():
        icon = QIcon()
        _cache[key] = icon
        return icon

    svg_text = svg_path.read_text(encoding="utf-8")
    svg_text = svg_text.replace('stroke="currentColor"', f'stroke="{color}"')

    renderer = QSvgRenderer(QByteArray(svg_text.encode("utf-8")))
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()

    icon = QIcon(pixmap)
    _cache[key] = icon
    return icon


def icon_size(size: int = 20) -> QSize:
    return QSize(size, size)
