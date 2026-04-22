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

"""Gmail connector — imports emails using gws CLI or Python Google API."""

from __future__ import annotations

from typing import Any

from create_context_graph.connectors import (
    BaseConnector,
    NormalizedData,
    register_connector,
)
from create_context_graph.connectors.oauth import check_gws_cli, run_gws_command


@register_connector("gmail")
class GmailConnector(BaseConnector):
    """Import emails from Gmail.

    Prefers the Google Workspace CLI (gws) if available; falls back to
    the Python Google API client with OAuth2.
    """

    service_name = "Gmail"
    service_description = "Import emails from Gmail (last 30 days, up to 200)"
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

        # Fall back to Python Google API
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
            scopes=["https://www.googleapis.com/auth/gmail.readonly"],
        )

        from google.oauth2.credentials import Credentials

        creds = Credentials(token=tokens["access_token"])
        self._service = build("gmail", "v1", credentials=creds)

    def _fetch_via_gws(self, limit: int) -> NormalizedData:
        """Fetch emails using the gws CLI."""
        entities: dict[str, list[dict]] = {"Person": [], "Email": []}
        relationships: list[dict] = []
        documents: list[dict] = []
        seen_users: set[str] = set()

        try:
            result = run_gws_command([
                "gmail", "+list",
                "--max-results", str(min(limit, 200)),
                "--query", "newer_than:30d",
            ])
        except RuntimeError:
            return NormalizedData(entities=entities, relationships=relationships, documents=documents)

        messages = result if isinstance(result, list) else result.get("messages", [])

        for msg_summary in messages[:limit]:
            msg_id = msg_summary.get("id", "")
            try:
                msg = run_gws_command(["gmail", "+get", "--id", msg_id])
            except RuntimeError:
                continue

            subject = ""
            from_addr = ""
            date = ""
            for header in msg.get("payload", {}).get("headers", []):
                name = header.get("name", "").lower()
                if name == "subject":
                    subject = header.get("value", "")
                elif name == "from":
                    from_addr = header.get("value", "")
                elif name == "date":
                    date = header.get("value", "")

            entities["Email"].append({
                "name": subject or f"Email {msg_id[:8]}",
                "message_id": msg_id,
                "subject": subject,
                "from_address": from_addr,
                "date": date,
                "snippet": msg.get("snippet", ""),
            })

            if from_addr and from_addr not in seen_users:
                seen_users.add(from_addr)
                entities["Person"].append({
                    "name": from_addr.split("<")[0].strip().strip('"'),
                    "email": from_addr,
                    "role": "email-contact",
                })

            if from_addr:
                relationships.append({
                    "type": "SENT",
                    "source_name": from_addr.split("<")[0].strip().strip('"'),
                    "source_label": "Person",
                    "target_name": subject or f"Email {msg_id[:8]}",
                    "target_label": "Email",
                })

            body = msg.get("snippet", "")
            if body:
                documents.append({
                    "title": subject or f"Email {msg_id[:8]}",
                    "content": body,
                    "type": "gmail-email",
                    "metadata": {"from": from_addr, "date": date},
                })

        return NormalizedData(entities=entities, relationships=relationships, documents=documents)

    def _fetch_via_api(self, limit: int) -> NormalizedData:
        """Fetch emails using the Python Google API client."""
        entities: dict[str, list[dict]] = {"Person": [], "Email": []}
        relationships: list[dict] = []
        documents: list[dict] = []
        seen_users: set[str] = set()

        results = self._service.users().messages().list(
            userId="me",
            maxResults=min(limit, 200),
            q="newer_than:30d",
        ).execute()

        for msg_summary in results.get("messages", []):
            msg = self._service.users().messages().get(
                userId="me", id=msg_summary["id"], format="metadata",
                metadataHeaders=["Subject", "From", "Date"],
            ).execute()

            subject = ""
            from_addr = ""
            date = ""
            for header in msg.get("payload", {}).get("headers", []):
                name = header.get("name", "").lower()
                if name == "subject":
                    subject = header.get("value", "")
                elif name == "from":
                    from_addr = header.get("value", "")
                elif name == "date":
                    date = header.get("value", "")

            entities["Email"].append({
                "name": subject or f"Email {msg['id'][:8]}",
                "message_id": msg["id"],
                "subject": subject,
                "from_address": from_addr,
                "date": date,
                "snippet": msg.get("snippet", ""),
            })

            if from_addr and from_addr not in seen_users:
                seen_users.add(from_addr)
                entities["Person"].append({
                    "name": from_addr.split("<")[0].strip().strip('"'),
                    "email": from_addr,
                    "role": "email-contact",
                })

            if from_addr:
                relationships.append({
                    "type": "SENT",
                    "source_name": from_addr.split("<")[0].strip().strip('"'),
                    "source_label": "Person",
                    "target_name": subject or f"Email {msg['id'][:8]}",
                    "target_label": "Email",
                })

            snippet = msg.get("snippet", "")
            if snippet:
                documents.append({
                    "title": subject or f"Email {msg['id'][:8]}",
                    "content": snippet,
                    "type": "gmail-email",
                    "metadata": {"from": from_addr, "date": date},
                })

        return NormalizedData(entities=entities, relationships=relationships, documents=documents)

    def fetch(self, **kwargs: Any) -> NormalizedData:
        limit = kwargs.get("limit", 200)
        if self._use_gws:
            return self._fetch_via_gws(limit)
        if self._service:
            return self._fetch_via_api(limit)
        raise RuntimeError("Call authenticate() first")
