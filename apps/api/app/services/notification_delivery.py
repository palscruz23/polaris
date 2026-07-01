from typing import Protocol

import httpx


class NotificationDeliveryService(Protocol):
    def send(self, markdown: str) -> dict:
        """Send a notification and return provider response metadata."""


class TeamsNotificationProvider:
    def __init__(
        self,
        webhook_url: str,
        destination_label: str,
        client: httpx.Client | None = None,
    ):
        self.webhook_url = webhook_url
        self.destination_label = destination_label
        self.client = client or httpx.Client(timeout=20)

    def send(self, markdown: str) -> dict:
        response = self.client.post(
            self.webhook_url,
            json={
                "type": "message",
                "attachments": [
                    {
                        "contentType": (
                            "application/vnd.microsoft.card.adaptive"
                        ),
                        "content": {
                            "$schema": (
                                "http://adaptivecards.io/schemas/"
                                "adaptive-card.json"
                            ),
                            "type": "AdaptiveCard",
                            "version": "1.4",
                            "body": [
                                {
                                    "type": "TextBlock",
                                    "text": markdown,
                                    "wrap": True,
                                }
                            ],
                        },
                    }
                ],
            },
        )
        response.raise_for_status()
        return {
            "status_code": response.status_code,
            "destination_label": self.destination_label,
            "response_text": response.text[:500],
        }
