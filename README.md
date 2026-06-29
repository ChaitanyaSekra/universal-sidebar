# Universal Sidebar (Python Desktop App)

A floating, always-on-top productivity sidebar for Windows, built with
PySide6. Summon it from anywhere with a global hotkey or the system tray
icon — no browser required.

## Status: Phase 1–3 + Calculator + Google Calendar complete

What works right now:
- Frameless, always-on-top window docked to the right screen edge
- Smooth slide-in/out animation
- Resizable by dragging the left edge (300–720px), remembers width
- Compact mode toggle
- Custom draggable title bar (no OS chrome)
- Dark/light theme system (`ui/theme.py`, `core/config.py`)
- System tray icon with Show/Hide, Settings, Quit
- Global hotkeys: `Ctrl+Shift+S` (toggle sidebar), `Ctrl+Shift+P` (command
  palette — wiring comes in its own phase)
- SQLite storage layer with the full schema for every planned module
  already created (`storage/database.py`)
- Settings key/value store with sensible defaults
- **Calculator**: basic + scientific modes, safe expression evaluator
  (no `eval()` — see `modules/calculator/engine.py`), full keyboard input,
  history panel backed by SQLite, copy-result button
- **Calendar**: live-connected to Google Calendar. Month view, click a day
  to see its events, create/edit/delete events that land on your real
  Google Calendar immediately. All network calls run on a background
  thread so the sidebar UI never freezes.
- Remaining module pages (Notes, Chat, Clipboard, Favorites, Quick Links,
  Todo, Timer, Settings, Command Palette) are real, navigable placeholder
  widgets — full features land in their own phases.

What's *not* built yet: Notes editor, AI Chat (mocked), Clipboard watcher,
Favorites/Quick Links CRUD, Todo list, Timer/Pomodoro, Settings UI,
Command Palette overlay, packaging into a `.exe`.

## Requirements

- Windows 10/11
- Python 3.11+

## Setup

```bash
pip install -r requirements.txt
python app.py
```

On first run, the app creates its data folder at:

```
%APPDATA%\UniversalSidebar\
    universal_sidebar.db
    exports\
```

## Connecting Google Calendar

The Calendar module talks to your real Google Calendar, which requires a
one-time setup in Google Cloud Console to get a `credentials.json` file.
This is required by Google for *any* app (including ones you write
yourself) that wants to access Calendar data — there's no way around this
step, but it only takes a few minutes and you only do it once.

### Step 1 — Create a Google Cloud project

1. Go to [console.cloud.google.com](https://console.cloud.google.com/)
   and sign in with the Google account whose calendar you want to access.
2. Click the project dropdown at the top → **New Project**.
3. Name it anything (e.g. "Universal Sidebar") → **Create**.
4. Make sure the new project is selected in the dropdown before continuing.

### Step 2 — Enable the Calendar API

1. In the left sidebar, go to **APIs & Services → Library**.
2. Search for "Google Calendar API" → click it → **Enable**.

### Step 3 — Configure the OAuth consent screen

1. Go to **APIs & Services → OAuth consent screen**.
2. User type: choose **External** (unless you have a Google Workspace
   organization, in which case Internal is fine too) → **Create**.
3. Fill in an app name (e.g. "Universal Sidebar"), your email as the
   support email, and your email again under developer contact info →
   **Save and Continue**.
4. On the Scopes screen, click **Add or Remove Scopes**, search for
   "Calendar API", check the one with scope
   `https://www.googleapis.com/auth/calendar` → **Update** → **Save and
   Continue**.
5. On the Test users screen, click **Add Users** and add the Gmail
   address you'll actually use with this app → **Save and Continue**.
   (Because this is your own personal app, not a published public one,
   Google requires your account to be explicitly listed as a test user.)
6. Review and go back to the dashboard.

### Step 4 — Create OAuth credentials

1. Go to **APIs & Services → Credentials**.
2. Click **Create Credentials → OAuth client ID**.
3. Application type: **Desktop app**.
4. Name it anything (e.g. "Universal Sidebar Desktop") → **Create**.
5. A dialog shows your client ID/secret — click **Download JSON**.

### Step 5 — Install it for the app

Rename the downloaded file to exactly `credentials.json` and place it at:

```
%APPDATA%\UniversalSidebar\credentials.json
```

(Create the `UniversalSidebar` folder if it doesn't exist yet — it's also
where the app's database lives.)

### Step 6 — Connect from the app

1. Run the app, open the **Calendar** module.
2. Click **Connect Google Calendar**.
3. Your browser opens to Google's consent screen — sign in with the same
   account you added as a test user, and approve access.
4. The browser tab will say something like "The authentication flow has
   completed" — you can close it and return to the app. The Calendar
   module now shows your real events.

Your access/refresh token is saved locally at
`%APPDATA%\UniversalSidebar\token.pickle` so you won't have to repeat this
browser step on future launches — the app refreshes the token silently.
Click **Disconnect** in the Calendar module at any time to remove the
local token (this doesn't revoke access on Google's side — to fully revoke
it, visit [myaccount.google.com/permissions](https://myaccount.google.com/permissions)
and remove the app there too).

> **Note on the "unverified app" warning:** since this is your own personal
> OAuth client (not submitted for Google's verification review, which is
> meant for public-facing apps), Google's consent screen will show an
> "unverified app" warning. This is expected and safe to proceed through
> (click "Advanced" → "Go to [app name] (unsafe)") — it just means Google
> hasn't reviewed an app that only you, as a listed test user, can use.



## Testing locally

- **Run it:** `python app.py`. The window starts hidden; press
  `Ctrl+Shift+S` or click the tray icon to slide it in.
- **Calculator:** open the Calculator module, try typing on your keyboard
  directly (digits, `+ - * / ( ) . %`, Enter for `=`, Backspace, Escape to
  clear) as well as clicking buttons. Toggle "Scientific mode" for
  trig/log/sqrt/factorial. Double-click a history entry to reuse it.
- **Calendar:** follow "Connecting Google Calendar" above first. Once
  connected, click any date, then "+ New event" to create one — check your
  actual Google Calendar (web or phone) to confirm it appears in real time.
  Double-click an event to edit it; select one and click "Delete selected"
  to remove it.
- **Tray icon:** look in the Windows system tray (you may need to click
  the "^" overflow arrow). Right-click for the menu, left-click/double-click
  to toggle the sidebar.
- **Resize:** hover the very left edge of the sidebar until the cursor
  would normally change, then drag.
- **Compact mode:** click the `◧` button in the title bar.
- **Inspect the database:** open `%APPDATA%\UniversalSidebar\universal_sidebar.db`
  with [DB Browser for SQLite](https://sqlitebrowser.org/) to see the
  schema and any stored settings.
- **Changing hotkeys:** not yet exposed in UI (Settings module phase);
  for now you can test programmatically via `core/hotkeys.py`'s
  `update_hotkey()`.
- **Debugging:** run from a terminal (not double-clicked) so `print()`
  output and exceptions are visible. The `keyboard` library's hotkey
  registration requires running as Administrator on some Windows setups
  if other apps have claimed global hooks — if hotkeys silently don't
  fire, try running your terminal as Administrator.

## Project layout

```
app.py                  entry point — builds window, registers modules, starts hotkeys/tray
core/
  config.py             paths, hotkey defaults, theme palettes
  event_bus.py           Qt signals shared across the whole app
  hotkeys.py             global OS hotkey registration (background thread)
storage/
  database.py            SQLite connection + full schema
  settings_store.py       typed get/set over the settings table
ui/
  main_window.py         frameless animated sidebar shell
  nav_rail.py             left icon strip, switches modules
  title_bar.py            custom draggable title bar
  theme.py                stylesheet generator from theme palettes
  tray.py                 system tray icon + menu
modules/
  base_module.py          shared module contract
  chat/ notes/ calculator/ calendar/ clipboard/
  favorites/ quicklinks/ todo/ timer/ settings/ command_palette/
    view.py               each module's UI (placeholder for now)
```

## Notes on design decisions

- **PySide6 over CustomTkinter**: needed native always-on-top/frameless
  window flags, a system tray icon, and Qt's animation framework — none
  of which CustomTkinter supports well.
- **`keyboard` library for global hotkeys**: hooks the Windows keyboard
  driver directly, so shortcuts work even when another app has focus.
  Its callbacks fire on a non-Qt thread, so they only ever emit signals
  on `core/event_bus.py`'s `EventBus` — never touch a widget directly —
  to stay thread-safe.
- **Single shared SQLite connection**: SQLite only safely supports one
  writer at a time; one connection guarded by a lock avoids "database is
  locked" errors that crop up with multiple connections in one process.
- **No telemetry, no network calls** except the future user-configured
  AI provider in the Chat module (currently fully mocked, per your
  instruction).
