import argparse
import subprocess

from app.database import SessionLocal
from app.evaluations.smoke_cases import SMOKE_SUITE_NAME
from app.evaluations.suites import BUILT_IN_SUITES
from app.providers.factory import get_chat_provider
from app.services.evaluation_service import EvaluationService


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run persisted end-to-end Reliability Agent evaluations.",
    )
    parser.add_argument(
        "--suite",
        default=SMOKE_SUITE_NAME,
        choices=sorted(BUILT_IN_SUITES.keys()),
        help="Built-in evaluation suite to seed and run.",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Optional model id from the server-side allowlist.",
    )
    parser.add_argument(
        "--dataset-version",
        default="sample_data/reliability",
        help="Dataset or seed version label to store on the eval run.",
    )
    parser.add_argument(
        "--seed-only",
        action="store_true",
        help="Create or update eval suites/cases without running them.",
    )
    parser.add_argument(
        "--batch-id",
        default=None,
        help="Optional batch identifier for grouping production eval runs.",
    )
    parser.add_argument(
        "--run-purpose",
        default="manual",
        help="Short purpose label, for example deploy-smoke or nightly.",
    )
    parser.add_argument(
        "--metadata",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Additional run metadata. Can be passed multiple times.",
    )
    args = parser.parse_args()

    description, cases = BUILT_IN_SUITES[args.suite]
    provider = get_chat_provider(args.model)

    with SessionLocal() as session:
        service = EvaluationService(session, provider)
        service.upsert_suite(
            name=args.suite,
            description=description,
            cases=cases,
        )

        if args.seed_only:
            print(f"Seeded evaluation suite: {args.suite}")
            print(f"Cases: {len(cases)}")
            return

        summary = service.run_suite(
            suite_name=args.suite,
            git_commit=current_git_commit(),
            dataset_version=args.dataset_version,
            run_metadata=_run_metadata(
                batch_id=args.batch_id,
                run_purpose=args.run_purpose,
                metadata_items=args.metadata,
            ),
        )

    print(f"Evaluation run: {summary.eval_run_id}")
    print(f"Status: {summary.status}")
    print(f"Cases: {summary.case_count}")
    print(f"Passed: {summary.passed_count}")
    print(f"Failed: {summary.failed_count}")
    if summary.aggregate_score is not None:
        print(f"Aggregate score: {summary.aggregate_score:.2%}")


def current_git_commit() -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None

    return result.stdout.strip() or None


def _run_metadata(
    *,
    batch_id: str | None,
    run_purpose: str,
    metadata_items: list[str],
) -> dict[str, str]:
    metadata = {
        "source": "app.cli.run_evaluation",
        "run_purpose": run_purpose,
    }
    if batch_id:
        metadata["batch_id"] = batch_id

    for item in metadata_items:
        if "=" not in item:
            raise ValueError(
                "Evaluation metadata must use KEY=VALUE format."
            )
        key, value = item.split("=", 1)
        normalized_key = key.strip()
        if not normalized_key:
            raise ValueError("Evaluation metadata keys cannot be empty.")
        metadata[normalized_key] = value.strip()

    return metadata

if __name__ == "__main__":
    main()
