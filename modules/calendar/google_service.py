"""
modules/calendar/google_service.py

Thin wrapper around the Google Calendar API v3 client. Every function
takes/returns plain Python dicts/strings rather than leaking the Google
client library's objects into the UI layer, so view.py doesn't need to
know anything about googleapiclient.

All times are handled as naive local datetimes formatted as ISO 8601;
Calendar API expects timezone info, so we attach the system's local
timezone before sending and strip it back off when displaying.
"""

from datetime import datetime, timezone

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from modules.calendar.google_auth import get_credentials, GoogleAuthError


class GoogleCalendarError(Exception):
    pass


def _service():
    try:
        creds = get_credentials()
    except GoogleAuthError as exc:
        raise GoogleCalendarError(str(exc))
    return build("calendar", "v3", credentials=creds, cache_discovery=False)


def _local_tz_offset_iso(dt: datetime) -> str:
    """Attach the machine's local UTC offset to a naive datetime and
    return RFC3339 string, which is what the Calendar API requires."""
    local_dt = dt.astimezone() if dt.tzinfo else dt.replace(
        tzinfo=datetime.now().astimezone().tzinfo
    )
    return local_dt.isoformat()


def list_events(start: datetime, end: datetime, max_results: int = 50) -> list[dict]:
    """List events on the primary calendar between start and end
    (inclusive), sorted by start time. Returns simplified dicts:
    {id, title, description, start, end, all_day}."""
    service = _service()
    try:
        result = service.events().list(
            calendarId="primary",
            timeMin=_local_tz_offset_iso(start),
            timeMax=_local_tz_offset_iso(end),
            maxResults=max_results,
            singleEvents=True,
            orderBy="startTime",
        ).execute()
    except HttpError as exc:
        raise GoogleCalendarError(f"Google Calendar API error: {exc}")

    events = []
    for item in result.get("items", []):
        start_info = item.get("start", {})
        end_info = item.get("end", {})
        all_day = "date" in start_info  # all-day events use 'date', not 'dateTime'
        events.append({
            "id": item.get("id"),
            "title": item.get("summary", "(no title)"),
            "description": item.get("description", ""),
            "start": start_info.get("dateTime") or start_info.get("date"),
            "end": end_info.get("dateTime") or end_info.get("date"),
            "all_day": all_day,
        })
    return events


def create_event(title: str, start: datetime, end: datetime, description: str = "",
                  all_day: bool = False) -> dict:
    service = _service()
    body = {"summary": title, "description": description}
    if all_day:
        body["start"] = {"date": start.strftime("%Y-%m-%d")}
        body["end"] = {"date": end.strftime("%Y-%m-%d")}
    else:
        body["start"] = {"dateTime": _local_tz_offset_iso(start)}
        body["end"] = {"dateTime": _local_tz_offset_iso(end)}

    try:
        return service.events().insert(calendarId="primary", body=body).execute()
    except HttpError as exc:
        raise GoogleCalendarError(f"Failed to create event: {exc}")


def update_event(event_id: str, title: str, start: datetime, end: datetime,
                  description: str = "", all_day: bool = False) -> dict:
    service = _service()
    body = {"summary": title, "description": description}
    if all_day:
        body["start"] = {"date": start.strftime("%Y-%m-%d")}
        body["end"] = {"date": end.strftime("%Y-%m-%d")}
    else:
        body["start"] = {"dateTime": _local_tz_offset_iso(start)}
        body["end"] = {"dateTime": _local_tz_offset_iso(end)}

    try:
        return service.events().update(
            calendarId="primary", eventId=event_id, body=body
        ).execute()
    except HttpError as exc:
        raise GoogleCalendarError(f"Failed to update event: {exc}")


def delete_event(event_id: str) -> None:
    service = _service()
    try:
        service.events().delete(calendarId="primary", eventId=event_id).execute()
    except HttpError as exc:
        raise GoogleCalendarError(f"Failed to delete event: {exc}")
