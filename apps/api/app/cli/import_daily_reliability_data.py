import argparse
from pathlib import Path

from app.database import SessionLocal
from app.services.daily_reliability_import_service import (
    DailyReliabilityImportError,
    DailyReliabilityImportService,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Import daily Polaris Watch work-order data.",
    )
    parser.add_argument("--work-orders-csv", type=Path, required=True)
    parser.add_argument("--work-order-failure-modes-csv", type=Path, required=True)
    args = parser.parse_args()

    with SessionLocal() as session:
        try:
            summary = DailyReliabilityImportService(session).import_files(
                args.work_orders_csv,
                args.work_order_failure_modes_csv,
            )
        except DailyReliabilityImportError:
            session.rollback()
            raise

    print("Imported daily reliability data:")
    print(f"- Work orders: {summary.work_order_count}")
    print(
        "- Work order failure mode links: "
        f"{summary.work_order_failure_mode_count}"
    )


if __name__ == "__main__":
    main()
