# Universal Sidebar — UI Overhaul Drop-in Pack

## What's in here
```
assets/icons/*.svg          19 Tabler outline icons (MIT licensed), bundled locally
ui/icon_loader.py           NEW — loads + recolors the SVGs into QIcons, with caching
ui/theme.py                 REPLACED — new dashboard palette (see below)
ui/nav_rail.py               REPLACED — icon-only rail, expands on hover
ui/title_bar.py              REPLACED — icon buttons instead of glyph text
modules/notes/view.py        REPLACED — fixes the header truncation bug + icon buttons
modules/calculator/view.py   REPLACED — depth-styled button grid + icon buttons
modules/calendar/view.py     REPLACED — icon buttons on connect/add/delete
```

## How to apply
Copy each file into the matching path in your `universal_sidebar_app/` project,
overwriting the old versions. The `assets/icons/` folder is new — drop it at
the project root (sibling to `ui/`, `modules/`, etc).

## The truncation bug you saw in the screenshot
It wasn't the title bar — it was the Notes editor header. The old layout had
the title input, a text "📌" pin button, and a full "Delete" text button all
competing for space in a narrow panel, so under any width pressure it
collapsed to "itled" / "elet". Fixed by making pin/delete fixed-width (34px)
icon buttons and giving the title input an explicit stretch + minimumWidth(0)
so *it* elides gracefully instead of squeezing its neighbors.

## Palette (ui/theme.py -> PALETTE)
- base #13141a / surface_1 #1a1c24 / surface_2 #272a38 / surface_3 #15161c
  — layered depth instead of one flat background
- accent #6b66e0 (indigo) — the only "brand" color, used for active/selected states
- success #1d9e75 (teal) — reserved for "saved" / pinned states only
- danger #a32d2d / danger_fg #e0807e (coral) — reserved for destructive actions only

## Things to check after dropping this in
1. `core/config.py` previously fed `THEMES` into the old `theme.py` — the new
   `theme.py` is self-contained and no longer imports `core.config`. If
   anything else in your codebase imports `THEMES` from `core.config`, that's
   unaffected; only `theme.py`'s own import was removed.
2. Resolved the open question from last session: pin button now visibly
   toggles (filled teal pin when pinned, outline muted pin when not).
3. Not yet visually tested in a real PySide6 window (same caveat as last
   session — no PySide6 display environment here). Worth a quick visual pass,
   especially the nav rail's hover-expand animation and icon recoloring.
4. Calculator/Calendar modules got icon-button treatment but weren't part of
   the original screenshot — worth confirming spacing looks right once running.

## Not touched in this pass
Chat, Clipboard, Favorites, Quick Links, Todo, Timer, Settings, Command
Palette — still placeholder/unbuilt per the project summary. They'll
automatically inherit the new theme.py colors since they're built with the
same objectName conventions (QPushButton, #IconButton, etc), but icon-only
nav entries for them already exist in nav_rail.py's MODULE_ICONS.
