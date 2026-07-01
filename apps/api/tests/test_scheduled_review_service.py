from datetime import UTC, datetime, timedelta
from typing import Any

from app.models import ScheduledReviewRun
from app.services.scheduled_review_service import (
    ScheduledReviewService,
    resolve_review_window,
)


class FakeSession:
    def __init__(self) -> None:
        self.added: list[Any] = []
        self.commit_count = 0

    def add(self, item: Any) -> None:
        self.added.append(item)

    def commit(self) -> None:
        self.commit_count += 1


class FakeDeliveryService:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def send(self, markdown: str) -> dict:
        self.messages.append(markdown)
        return {"status_code": 202}


class FakeScheduledReviewService(ScheduledReviewService):
    def _build_report(self, template_id, window_start_at, window_end_at):
        from app.services.scheduled_review_report_builder import ScheduledReviewReport

        return ScheduledReviewReport(
            markdown=f"# {self.report_builder.title}",
            summary_json={"template_id": template_id},
        )


class FakeReportBuilder:
    title = "Bad Actor Watchlist"


def test_resolve_review_window_uses_utc_now() -> None:
    now = datetime(2026, 6, 30, 0, 0, tzinfo=UTC)

    start, end = resolve_review_window(lookback_days=7, now=now)

    assert start == now - timedelta(days=7)
    assert end == now


def test_service_persists_successful_review_run() -> None:
    session = FakeSession()
    delivery = FakeDeliveryService()
    service = FakeScheduledReviewService(
        session,  # type: ignore[arg-type]
        report_builder=FakeReportBuilder(),
        delivery_service=delivery,
    )

    run = service.run_template(
        template_id="bad_actor_watchlist",
        lookback_days=30,
        now=datetime(2026, 6, 30, tzinfo=UTC),
    )

    assert isinstance(run, ScheduledReviewRun)
    assert run.template_id == "bad_actor_watchlist"
    assert run.status == "succeeded"
    assert run.report_markdown == "# Bad Actor Watchlist"
    assert delivery.messages == ["# Bad Actor Watchlist"]
    assert session.commit_count == 2


class FailingDeliveryService:
    def send(self, markdown: str) -> dict:
        raise RuntimeError("Teams webhook rejected the report")


def test_service_marks_partial_success_when_delivery_fails() -> None:
    session = FakeSession()
    service = FakeScheduledReviewService(
        session,  # type: ignore[arg-type]
        report_builder=FakeReportBuilder(),
        delivery_service=FailingDeliveryService(),
    )

    run = service.run_template(
        template_id="bad_actor_watchlist",
        lookback_days=30,
        now=datetime(2026, 6, 30, tzinfo=UTC),
    )

    assert run.status == "partially_succeeded"
    assert run.report_markdown == "# Bad Actor Watchlist"
    assert "Teams webhook rejected" in run.deliveries[0].error_message
