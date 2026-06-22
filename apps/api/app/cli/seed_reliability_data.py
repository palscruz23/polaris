import argparse
from pathlib import Path

from app.database import SessionLocal
from app.services.reliability_seed_loader import (
    SeedLoadError,
    load_clean_reliability_seed_data,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Load clean reliability seed data from CSV files.",
    )
    parser.add_argument(
        "seed_directory",
        type=Path,
        help="Directory containing reliability seed CSV files.",
    )
    args = parser.parse_args()

    with SessionLocal() as session:
        try:
            summary = load_clean_reliability_seed_data(
                session,
                args.seed_directory,
            )
        except SeedLoadError:
            session.rollback()
            raise

    print("Loaded clean reliability seed data:")
    print(f"- Equipment: {summary.equipment_count}")
    print(f"- Failure modes: {summary.failure_mode_count}")
    print(f"- Maintenance strategies: {summary.maintenance_strategy_count}")
    print(f"- Work orders: {summary.work_order_count}")
    print(
        "- Work order failure mode links: "
        f"{summary.work_order_failure_mode_count}"
    )


if __name__ == "__main__":
    main()
