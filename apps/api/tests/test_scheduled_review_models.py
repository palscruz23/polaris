from sqlalchemy import CheckConstraint

from app.models import ScheduledReviewDelivery, ScheduledReviewRun


def test_scheduled_review_models_are_exported() -> None:
    assert ScheduledReviewRun.__tablename__ == "scheduled_review_runs"
    assert ScheduledReviewDelivery.__tablename__ == "scheduled_review_deliveries"


def test_scheduled_review_run_metadata_includes_window_constraint() -> None:
    constraint_names = {
        constraint.name
        for constraint in ScheduledReviewRun.__table__.constraints
        if isinstance(constraint, CheckConstraint)
    }

    assert "ck_scheduled_review_runs_window_start_before_end" in constraint_names


def test_scheduled_review_status_columns_have_server_defaults() -> None:
    assert str(ScheduledReviewRun.__table__.c.status.server_default.arg) == "'running'"
    assert (
        str(ScheduledReviewDelivery.__table__.c.status.server_default.arg)
        == "'pending'"
    )


def test_scheduled_review_relationship_is_wired_both_ways() -> None:
    assert ScheduledReviewRun.__mapper__.relationships["deliveries"].back_populates == "run"
    assert ScheduledReviewDelivery.__mapper__.relationships["run"].back_populates == "deliveries"
