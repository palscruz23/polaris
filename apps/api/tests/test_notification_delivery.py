import httpx

from app.services.notification_delivery import TeamsNotificationProvider


def test_teams_provider_posts_markdown_message() -> None:
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(202, text="accepted")

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)
    provider = TeamsNotificationProvider(
        webhook_url="https://example.test/webhook",
        destination_label="Reliability Team",
        client=client,
    )

    result = provider.send("# Report")

    assert result["status_code"] == 202
    assert requests[0].url == "https://example.test/webhook"
    assert requests[0].headers["content-type"] == "application/json"
    assert b"# Report" in requests[0].content
