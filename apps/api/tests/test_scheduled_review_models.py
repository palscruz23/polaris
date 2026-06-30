from app.models import ScheduledReviewDelivery, ScheduledReviewRun


def test_scheduled_review_models_are_exported() -> None:
    assert ScheduledReviewRun.__tablename__ == "scheduled_review_runs"
    assert ScheduledReviewDelivery.__tablename__ == "scheduled_review_deliveries"
