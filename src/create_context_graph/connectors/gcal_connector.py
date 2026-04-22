# Copyright 2026 Neo4j Labs
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Google Calendar connector — imports events using gws CLI or Python Google API."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from create_context_graph.connectors import (
    BaseConnector,
    NormalizedData,
    register_connector,
)
from create_context_graph.connectors.oauth import check_gws_cli, run_gws_command


@register_connector("gcal")
class GCalConnector(BaseConnector):
    """Import events from Google Calendar.

    Prefers the Google Workspace CLI (gws) if available; falls back to
    the Python Google API client with OAuth2.
    """

    service_name = "Google Calendar"
    service_description = "Import calendar events from Google Calendar (last 90 days)"
    requires_oauth = True

    def __init__(self):
        self._use_gws = False
        self._service = None

    def get_credential_prompts(self) -> list[dict[str, Any]]:
        if check_gws_cli():
            return []  # gws handles auth itself
        return [
            {
                "name": "client_id",
                "prompt": "Google OAuth2 Client ID:",
                "secret": False,
                "description": "From Google Cloud Console > APIs & Services > Credentials",
            },
            {
                "name": "client_secret",
                "prompt": "Google OAuth2 Client Secret:",
                "secret": True,
                "description": "From the same OAuth2 credentials page",
            },
        ]

    def authenticate(self, credentials: dict[str, str]) -> None:
        if check_gws_cli():
            self._use_gws = True
            return

        try:
            from googleapiclient.discovery import build
        except ImportError:
            raise ImportError(
                "google-api-python-client and google-auth-oauthlib are required. "
                "Install with: pip install google-api-python-client google-auth-oauthlib"
            )

        from create_context_graph.connectors.oauth import oauth2_authorize

        tokens = oauth2_authorize(
            auth_url="https://accounts.google.com/o/oauth2/v2/auth",
            token_url="https://oauth2.googleapis.com/token",
            client_id=credentials["client_id"],
            client_secret=credentials["client_secret"],
            scopes=["https://www.googleapis.com/auth/calendar.readonly"],
        )

        from google.oauth2.credentials import Credentials

        creds = Credentials(token=tokens["access_token"])
        self._service = build("calendar", "v3", credentials=creds)

    def _parse_event(self, event: dict) -> tuple[dict, list[dict], list[dict]]:
        """Parse a calendar event into entity, relationships, and attendee entities."""
        summary = event.get("summary", "Untitled Event")
        start = event.get("start", {}).get("dateTime", event.get("start", {}).get("date", ""))
        end = event.get("end", {}).get("dateTime", event.get("end", {}).get("date", ""))

        entity = {
            "name": summary,
            "event_id": event.get("id", ""),
            "start_time": start,
            "end_time": end,
            "location": event.get("location", ""),
            "description": event.get("description", ""),
            "status": event.get("status", ""),
        }

        attendees = []
        relationships = []
        for attendee in event.get("attendees", []):
            email = attendee.get("email", "")
            name = attendee.get("displayName", email.split("@")[0] if email else "Unknown")
            attendees.append({
                "name": name,
                "email": email,
                "role": "calendar-attendee",
                "description": f"Response: {attendee.get('responseStatus', 'unknown')}",
            })
            relationships.append({
                "type": "ATTENDING",
                "source_name": name,
                "source_label": "Person",
                "target_name": summary,
                "target_label": "CalendarEvent",
            })

        organizer = event.get("organizer", {})
        if organizer:
            org_email = organizer.get("email", "")
            org_name = organizer.get("displayName", org_email.split("@")[0] if org_email else "Unknown")
            relationships.append({
                "type": "ORGANIZED",
                "source_name": org_name,
                "source_label": "Person",
                "target_name": summary,
                "target_label": "CalendarEvent",
            })

        return entity, attendees, relationships

    def _fetch_via_gws(self, limit: int) -> NormalizedData:
        """Fetch calendar events using the gws CLI."""
        entities: dict[str, list[dict]] = {"Person": [], "CalendarEvent": []}
        relationships: list[dict] = []
        documents: list[dict] = []
        seen_users: set[str] = set()

        try:
            result = run_gws_command([
                "calendar", "+list",
                "--max-results", str(min(limit, 250)),
            ])
        except RuntimeError:
            return NormalizedData(entities=entities, relationships=relationships, documents=documents)

        events = result if isinstance(result, list) else result.get("items", [])

        for event in events[:limit]:
            entity, attendees, rels = self._parse_event(event)
            entities["CalendarEvent"].append(entity)
            relationships.extend(rels)
            for att in attendees:
                if att["email"] not in seen_users:
                    seen_users.add(att["email"])
                    entities["Person"].append(att)

            if event.get("description"):
                documents.append({
                    "title": event.get("summary", "Event"),
                    "content": event["description"],
                    "type": "calendar-event",
                    "metadata": {
                        "start": entity["start_time"],
                        "end": entity["end_time"],
                    },
                })

        return NormalizedData(entities=entities, relationships=relationships, documents=documents)

    def _fetch_via_api(self, limit: int) -> NormalizedData:
        """Fetch calendar events using the Python Google API client."""
        entities: dict[str, list[dict]] = {"Person": [], "CalendarEvent": []}
        relationships: list[dict] = []
        documents: list[dict] = []
        seen_users: set[str] = set()

        now = datetime.now(timezone.utc)
        time_min = (now - timedelta(days=90)).isoformat()

        results = self._service.events().list(
            calendarId="primary",
            timeMin=time_min,
            maxResults=min(limit, 250),
            singleEvents=True,
            orderBy="startTime",
        ).execute()

        for event in results.get("items", []):
            entity, attendees, rels = self._parse_event(event)
            entities["CalendarEvent"].append(entity)
            relationships.extend(rels)
            for att in attendees:
                if att["email"] not in seen_users:
                    seen_users.add(att["email"])
                    entities["Person"].append(att)

            if event.get("description"):
                documents.append({
                    "title": event.get("summary", "Event"),
                    "content": event["description"],
                    "type": "calendar-event",
                    "metadata": {
                        "start": entity["start_time"],
                        "end": entity["end_time"],
                    },
                })

        return NormalizedData(entities=entities, relationships=relationships, documents=documents)

    def fetch(self, **kwargs: Any) -> NormalizedData:
        limit = kwargs.get("limit", 250)
        if self._use_gws:
            return self._fetch_via_gws(limit)
        if self._service:
            return self._fetch_via_api(limit)
        raise RuntimeError("Call authenticate() first")
