"""
modules/calendar/google_auth.py

Handles the OAuth 2.0 "installed app" flow for Google Calendar access.

How it works end to end:
  1. The user drops a `credentials.json` (downloaded from Google Cloud
     Console -- see README for exact steps) into the app's data folder.
  2. On first connect, we run InstalledAppFlow.run_local_server(), which
     opens the user's default browser to Google's consent screen and spins
     up a temporary local HTTP server on localhost to catch the redirect
     with the authorization code. This is the standard, Google-recommended
     flow for desktop apps (no embedded browser, no client secret exposed
     to a public redirect URI).
  3. The resulting credentials (access + refresh token) are pickled to
     `token.pickle` in the app data folder. On every subsequent run we load
     that file and silently refresh the access token in the background
     using the refresh token -- no browser popup needed again unless the
     user revokes access.

This file deliberately knows nothing about UI; google_service.py and
view.py call into it and react to success/failure.
"""

import os
import pickle

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

from core.config import APP_DATA_DIR

SCOPES = ["https://www.googleapis.com/auth/calendar"]

CREDENTIALS_PATH = os.path.join(APP_DATA_DIR, "credentials.json")
TOKEN_PATH = os.path.join(APP_DATA_DIR, "token.pickle")


class GoogleAuthError(Exception):
    pass


def credentials_file_exists() -> bool:
    return os.path.isfile(CREDENTIALS_PATH)


def is_connected() -> bool:
    """True if we have a usable (or refreshable) token on disk, without
    triggering any network call or browser popup."""
    if not os.path.isfile(TOKEN_PATH):
        return False
    try:
        creds = _load_token()
    except Exception:
        return False
    return creds is not None and (creds.valid or creds.refresh_token is not None)


def get_credentials() -> Credentials:
    """Return valid credentials, refreshing silently if expired, or
    raising GoogleAuthError if the user needs to (re)connect via
    connect_interactive()."""
    if not os.path.isfile(TOKEN_PATH):
        raise GoogleAuthError("Not connected to Google Calendar yet.")

    creds = _load_token()
    if creds is None:
        raise GoogleAuthError("Stored Google credentials are invalid. Please reconnect.")

    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        _save_token(creds)

    if not creds.valid:
        raise GoogleAuthError("Google credentials expired. Please reconnect.")

    return creds


def connect_interactive() -> Credentials:
    """Run the full first-time consent flow: opens the browser, waits for
    the user to approve, saves the resulting token. Raises GoogleAuthError
    with a clear message if credentials.json is missing."""
    if not credentials_file_exists():
        raise GoogleAuthError(
            f"No credentials.json found at:\n{CREDENTIALS_PATH}\n\n"
            "See the README's 'Connecting Google Calendar' section for how "
            "to create and download one from Google Cloud Console."
        )

    flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
    creds = flow.run_local_server(port=0)
    _save_token(creds)
    return creds


def disconnect():
    """Remove the stored token. credentials.json is left alone since it's
    the app's client identity, not the user's personal grant."""
    if os.path.isfile(TOKEN_PATH):
        os.remove(TOKEN_PATH)


def _load_token():
    with open(TOKEN_PATH, "rb") as f:
        return pickle.load(f)


def _save_token(creds: Credentials):
    os.makedirs(APP_DATA_DIR, exist_ok=True)
    with open(TOKEN_PATH, "wb") as f:
        pickle.dump(creds, f)
