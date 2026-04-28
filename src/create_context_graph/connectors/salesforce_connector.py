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

"""Salesforce connector — imports accounts, contacts, and opportunities."""

from __future__ import annotations

from typing import Any

from create_context_graph.connectors import (
    BaseConnector,
    NormalizedData,
    register_connector,
)


@register_connector("salesforce")
class SalesforceConnector(BaseConnector):
    """Import data from Salesforce CRM."""

    service_name = "Salesforce"
    service_description = "Import accounts, contacts, and opportunities from Salesforce"
    requires_oauth = False  # Supports username/password auth

    def __init__(self):
        self._sf = None

    def get_credential_prompts(self) -> list[dict[str, Any]]:
        return [
            {
                "name": "username",
                "prompt": "Salesforce username:",
                "secret": False,
                "description": "Your Salesforce login email",
            },
            {
                "name": "password",
                "prompt": "Salesforce password:",
                "secret": True,
                "description": "Your Salesforce password",
            },
            {
                "name": "security_token",
                "prompt": "Salesforce security token:",
                "secret": True,
                "description": "From Settings > Personal > Reset My Security Token",
            },
            {
                "name": "domain",
                "prompt": "Salesforce domain (login/test):",
                "secret": False,
                "description": "'login' for production, 'test' for sandbox",
            },
        ]

    def authenticate(self, credentials: dict[str, str]) -> None:
        try:
            from simple_salesforce import Salesforce
        except ImportError:
            raise ImportError(
                "simple-salesforce is required for the Salesforce connector. "
                "Install it with: pip install simple-salesforce"
            )

        self._sf = Salesforce(
            username=credentials["username"],
            password=credentials["password"],
            security_token=credentials.get("security_token", ""),
            domain=credentials.get("domain", "login"),
        )

    def fetch(self, **kwargs: Any) -> NormalizedData:
        if not self._sf:
            raise RuntimeError("Call authenticate() first")

        limit = kwargs.get("limit", 100)
        entities: dict[str, list[dict]] = {
            "Person": [],
            "Account": [],
            "Opportunity": [],
        }
        relationships: list[dict] = []
        documents: list[dict] = []

        # Accounts
        account_query = f"SELECT Id, Name, Industry, Type, Description, Website FROM Account ORDER BY LastModifiedDate DESC LIMIT {limit}"
        accounts = self._sf.query(account_query)
        for record in accounts.get("records", []):
            entities["Account"].append({
                "name": record.get("Name", ""),
                "account_id": record.get("Id", ""),
                "industry": record.get("Industry", ""),
                "type": record.get("Type", ""),
                "website": record.get("Website", ""),
                "description": record.get("Description", ""),
            })

        # Contacts
        contact_query = f"SELECT Id, FirstName, LastName, Email, Title, AccountId, Account.Name FROM Contact ORDER BY LastModifiedDate DESC LIMIT {limit}"
        contacts = self._sf.query(contact_query)
        for record in contacts.get("records", []):
            name = f"{record.get('FirstName', '')} {record.get('LastName', '')}".strip()
            entities["Person"].append({
                "name": name,
                "email": record.get("Email", ""),
                "role": record.get("Title", ""),
                "description": f"Salesforce contact: {name}",
            })

            account = record.get("Account")
            if account and account.get("Name"):
                relationships.append({
                    "type": "WORKS_FOR",
                    "source_name": name,
                    "source_label": "Person",
                    "target_name": account["Name"],
                    "target_label": "Account",
                })

        # Opportunities
        opp_query = f"SELECT Id, Name, StageName, Amount, CloseDate, AccountId, Account.Name, Description FROM Opportunity ORDER BY LastModifiedDate DESC LIMIT {limit}"
        opps = self._sf.query(opp_query)
        for record in opps.get("records", []):
            entities["Opportunity"].append({
                "name": record.get("Name", ""),
                "opportunity_id": record.get("Id", ""),
                "stage": record.get("StageName", ""),
                "amount": record.get("Amount"),
                "close_date": record.get("CloseDate", ""),
            })

            account = record.get("Account")
            if account and account.get("Name"):
                relationships.append({
                    "type": "OPPORTUNITY_FOR",
                    "source_name": record.get("Name", ""),
                    "source_label": "Opportunity",
                    "target_name": account["Name"],
                    "target_label": "Account",
                })

            if record.get("Description"):
                documents.append({
                    "title": f"Opportunity: {record.get('Name', '')}",
                    "content": record["Description"],
                    "type": "salesforce-opportunity",
                    "metadata": {
                        "stage": record.get("StageName", ""),
                        "amount": record.get("Amount"),
                    },
                })

        return NormalizedData(
            entities=entities,
            relationships=relationships,
            documents=documents,
        )
