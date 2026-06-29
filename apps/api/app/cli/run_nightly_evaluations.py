import argparse
from datetime import UTC, datetime

from app.cli.run_evaluation import current_git_commit
from app.database import SessionLocal
from app.evaluations.suites import BUILT_IN_SUITES, NIGHTLY_SUITE_NAMES
from app.providers.factory import get_chat_provider
from app.services.evaluation_service import EvaluationService


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Run the off-hours nightly Reliability Agent evaluation batch."
        ),
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Optional model id from the server-side allowlist.",
    )
    parser.add_argument(
        "--dataset-version",
        default="production",
        help="Dataset or seed version label to store on each eval run.",
    )
    parser.add_argument(
        "--batch-id",
        default=None,
        help="Optional batch identifier. Defaults to nightly-YYYYMMDD.",
    )
    args = parser.parse_args()

    batch_id = args.batch_id or datetime.now(UTC).strftime("nightly-%Y%m%d")
    provider = get_chat_provider(args.model)
    git_commit = current_git_commit()

    with SessionLocal() as session:
        service = EvaluationService(session, provider)

        for suite_name in NIGHTLY_SUITE_NAMES:
            description, cases = BUILT_IN_SUITES[suite_name]
            service.upsert_suite(
                name=suite_name,
                description=description,
                cases=cases,
            )
            summary = service.run_suite(
                suite_name=suite_name,
                git_commit=git_commit,
                dataset_version=args.dataset_version,
                run_metadata={
                    "source": "app.cli.run_nightly_evaluations",
                    "run_purpose": "nightly",
                    "scheduled_for_local_time": "00:00",
                    "batch_id": batch_id,
                },
            )
            score = (
                f"{summary.aggregate_score:.2%}"
                if summary.aggregate_score is not None
                else "n/a"
            )
            print(
                f"{suite_name}: {summary.status} "
                f"{summary.passed_count}/{summary.case_count} passed "
                f"score={score} run={summary.eval_run_id}"
            )


if __name__ == "__main__":
    main()
