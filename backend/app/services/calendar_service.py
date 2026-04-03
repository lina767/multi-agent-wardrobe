from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from urllib.parse import quote

import httpx
from app.config import settings


@dataclass
class CalendarEvent:
    title: str
    starts_at: datetime
    location: str | None
    event_type: str
    source: str = "calendar"


class CalendarService:
    _cached_access_token: str | None = None
    _cached_access_token_expires_at: datetime | None = None

    async def list_upcoming_events(self, limit: int = 5) -> list[CalendarEvent]:
        remote_events = await self._list_google_events(limit=limit)
        if remote_events:
            return remote_events
        return self._list_json_events(limit=limit)

    async def _list_google_events(self, limit: int) -> list[CalendarEvent]:
        token = await self._get_google_access_token()
        calendar_ids = settings.google_calendar_ids
        if not token or not calendar_ids:
            return []
        now = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        events: list[CalendarEvent] = []
        async with httpx.AsyncClient(timeout=10.0) as client:
            for calendar_id in calendar_ids:
                encoded_calendar = quote(calendar_id, safe="")
                url = f"https://www.googleapis.com/calendar/v3/calendars/{encoded_calendar}/events"
                params = {
                    "timeMin": now,
                    "singleEvents": "true",
                    "orderBy": "startTime",
                    "maxResults": str(limit),
                }
                response = await client.get(url, params=params, headers={"Authorization": f"Bearer {token}"})
                if response.status_code != 200:
                    continue
                payload = response.json()
                for item in payload.get("items", []):
                    starts_at_raw = ((item.get("start") or {}).get("dateTime") or (item.get("start") or {}).get("date"))
                    starts_at = self._parse_dt(starts_at_raw)
                    if not starts_at:
                        continue
                    title = str(item.get("summary") or "Untitled event")
                    location = str(item.get("location")) if item.get("location") else None
                    events.append(
                        CalendarEvent(
                            title=title,
                            starts_at=starts_at,
                            location=location,
                            event_type=self._infer_event_type(title),
                            source=f"google:{calendar_id}",
                        )
                    )
        events.sort(key=lambda value: value.starts_at)
        return events[:limit]

    async def _get_google_access_token(self) -> str | None:
        now = datetime.now(UTC)
        if (
            self._cached_access_token
            and self._cached_access_token_expires_at
            and self._cached_access_token_expires_at > now
        ):
            return self._cached_access_token

        # Static token remains supported as a fallback.
        if settings.google_calendar_access_token:
            return settings.google_calendar_access_token

        refresh_token = settings.google_calendar_refresh_token
        client_id = settings.google_calendar_client_id
        client_secret = settings.google_calendar_client_secret
        if not refresh_token or not client_id or not client_secret:
            return None

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token",
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            if response.status_code != 200:
                return None
            payload = response.json()
            token = payload.get("access_token")
            expires_in = payload.get("expires_in", 3600)
            if not isinstance(token, str) or not token:
                return None
            if not isinstance(expires_in, int):
                try:
                    expires_in = int(expires_in)
                except (TypeError, ValueError):
                    expires_in = 3600
            # Keep a small safety buffer to avoid edge-expiry requests.
            safe_expires_in = max(60, expires_in - 90)
            self._cached_access_token = token
            self._cached_access_token_expires_at = datetime.now(UTC) + timedelta(seconds=safe_expires_in)
            return token

    def _list_json_events(self, limit: int) -> list[CalendarEvent]:
        raw = settings.calendar_events_json
        if not raw:
            return []
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            return []
        if not isinstance(payload, list):
            return []

        now = datetime.now(UTC)
        events: list[CalendarEvent] = []
        for event in payload:
            if not isinstance(event, dict):
                continue
            starts_at = self._parse_dt(event.get("starts_at"))
            if not starts_at or starts_at < now:
                continue
            events.append(
                CalendarEvent(
                    title=str(event.get("title") or "Untitled event"),
                    starts_at=starts_at,
                    location=str(event.get("location")) if event.get("location") else None,
                    event_type=str(event.get("event_type") or "other").lower(),
                    source=str(event.get("source") or "calendar"),
                )
            )
        events.sort(key=lambda value: value.starts_at)
        return events[:limit]

    def _parse_dt(self, value: object) -> datetime | None:
        if not isinstance(value, str):
            return None
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        return parsed

    def _infer_event_type(self, title: str) -> str:
        normalized = title.lower()
        if any(token in normalized for token in ["meeting", "sync", "review", "interview"]):
            return "meeting"
        if any(token in normalized for token in ["yoga", "gym", "workout", "run", "sport"]):
            return "errand"
        if "date" in normalized:
            return "date"
        if any(token in normalized for token in ["home", "remote", "wfh"]):
            return "home"
        return "other"
