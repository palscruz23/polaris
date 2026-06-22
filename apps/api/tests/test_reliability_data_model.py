from app.database import Base
from app.models import (
    Equipment,
    FailureMode,
    ImportBatch,
    ImportValidationResult,
    MaintenanceStrategy,
    WorkOrder,
    WorkOrderFailureMode,
)


def test_reliability_data_model_tables_are_registered() -> None:
    expected_tables = {
        "equipment",
        "failure_modes",
        "import_batches",
        "import_validation_results",
        "maintenance_strategies",
        "work_order_failure_modes",
        "work_orders",
    }

    assert expected_tables.issubset(Base.metadata.tables.keys())


def test_reliability_data_model_core_relationships_are_named() -> None:
    assert Equipment.work_orders.property.back_populates == "equipment"
    assert WorkOrder.equipment.property.back_populates == "work_orders"
    assert WorkOrder.failure_mode_links.property.back_populates == "work_order"
    assert FailureMode.work_order_links.property.back_populates == "failure_mode"
    assert ImportBatch.validation_results.property.back_populates == "import_batch"
    assert ImportValidationResult.import_batch.property.back_populates == (
        "validation_results"
    )
    assert MaintenanceStrategy.equipment.property.back_populates == (
        "maintenance_strategies"
    )
    assert WorkOrderFailureMode.failure_mode.property.back_populates == (
        "work_order_links"
    )


def test_reliability_data_model_keeps_expected_integrity_constraints() -> None:
    equipment_constraints = {
        constraint.name for constraint in Equipment.__table__.constraints
    }
    work_order_constraints = {
        constraint.name for constraint in WorkOrder.__table__.constraints
    }
    strategy_constraints = {
        constraint.name for constraint in MaintenanceStrategy.__table__.constraints
    }
    failure_link_constraints = {
        constraint.name
        for constraint in WorkOrderFailureMode.__table__.constraints
    }

    assert "ck_equipment_status" in equipment_constraints
    assert "ck_work_orders_maintenance_activity_type" in work_order_constraints
    assert "ck_maintenance_strategies_has_asset_reference" in strategy_constraints
    assert (
        "uq_work_order_failure_modes_work_order_failure_mode"
        in failure_link_constraints
    )
