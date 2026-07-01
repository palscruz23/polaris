import argparse

from app.config import settings
from app.database import SessionLocal
from app.services.notification_delivery import TeamsNotificationProvider
from app.services.scheduled_review_service import ScheduledReviewService


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run one Polaris Watch scheduled review template.",
    )
    parser.add_argument(
        "--template",
        choices=[
            "breakdown_strategy_gap",
            "bad_actor_watchlist",
            "maintenance_strategy_health_check",
        ],
        required=True,
    )
    parser.add_argument("--lookback-days", type=int, required=True)
    return parser.parse_args(argv)


def main() -> None:
    args = parse_args()
    if not settings.scheduled_review_teams_webhook_url:
        raise RuntimeError("SCHEDULED_REVIEW_TEAMS_WEBHOOK_URL is not configured.")
    delivery = TeamsNotificationProvider(
        webhook_url=settings.scheduled_review_teams_webhook_url,
        destination_label=settings.scheduled_review_teams_destination_label,
    )
    with SessionLocal() as session:
        run = ScheduledReviewService(
            session,
            delivery_service=delivery,
        ).run_template(
            template_id=args.template,
            lookback_days=args.lookback_days,
        )

    print(
        f"{run.template_id}: {run.status} "
        f"window={run.window_start_at.isoformat()}.."
        f"{run.window_end_at.isoformat()} "
        f"run={run.id}"
    )


if __name__ == "__main__":
    main()
