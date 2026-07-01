from datetime import UTC, datetime

from app.services.scheduled_review_report_builder import (
    ScheduledReviewReport,
    ScheduledReviewReportBuilder,
)


def test_report_builder_includes_required_sections() -> None:
    report = ScheduledReviewReportBuilder().build(
        template_id="bad_actor_watchlist",
        title="Bad Actor Watchlist",
        window_start_at=datetime(2026, 6, 29, tzinfo=UTC),
        window_end_at=datetime(2026, 6, 30, tzinfo=UTC),
        summary="3 assets require review.",
        key_findings=["P-101 has recurring seal leakage."],
        recommended_actions=["Open a defect elimination review for P-101."],
        evidence=["WO-1, WO-2"],
        limitations=["Synthetic sample data only."],
    )

    assert isinstance(report, ScheduledReviewReport)
    assert "# Bad Actor Watchlist" in report.markdown
    assert "## Key findings" in report.markdown
    assert "- P-101 has recurring seal leakage." in report.markdown
    assert report.summary_json["template_id"] == "bad_actor_watchlist"
    assert report.summary_json["finding_count"] == 1
