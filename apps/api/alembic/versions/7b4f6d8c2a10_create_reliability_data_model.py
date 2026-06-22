"""create reliability data model

Revision ID: 7b4f6d8c2a10
Revises: 4c0790a50ea2
Create Date: 2026-06-22 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "7b4f6d8c2a10"
down_revision: Union[str, Sequence[str], None] = "4c0790a50ea2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "import_batches",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("source_name", sa.Text(), nullable=False),
        sa.Column("dataset_type", sa.Text(), nullable=False),
        sa.Column(
            "status",
            sa.Text(),
            server_default=sa.text("'pending'"),
            nullable=False,
        ),
        sa.Column(
            "record_count",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "dataset_type IN ('equipment', 'work_orders', "
            "'maintenance_strategies', 'failure_modes')",
            name="ck_import_batches_dataset_type",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'completed', 'failed')",
            name="ck_import_batches_status",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "equipment",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("equipment_number", sa.Text(), nullable=False),
        sa.Column("functional_location", sa.Text(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("parent_equipment_number", sa.Text(), nullable=True),
        sa.Column("parent_functional_location", sa.Text(), nullable=True),
        sa.Column("equipment_type", sa.Text(), nullable=True),
        sa.Column("system", sa.Text(), nullable=True),
        sa.Column("criticality", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("install_date", sa.Date(), nullable=True),
        sa.Column("import_batch_id", sa.UUID(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('active', 'inactive', 'decommissioned', 'unknown')",
            name="ck_equipment_status",
        ),
        sa.ForeignKeyConstraint(
            ["import_batch_id"],
            ["import_batches.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("equipment_number"),
    )
    op.create_index(
        op.f("ix_equipment_criticality"),
        "equipment",
        ["criticality"],
        unique=False,
    )
    op.create_index(
        op.f("ix_equipment_equipment_number"),
        "equipment",
        ["equipment_number"],
        unique=True,
    )
    op.create_index(
        op.f("ix_equipment_equipment_type"),
        "equipment",
        ["equipment_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_equipment_functional_location"),
        "equipment",
        ["functional_location"],
        unique=False,
    )
    op.create_index(
        op.f("ix_equipment_import_batch_id"),
        "equipment",
        ["import_batch_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_equipment_system"),
        "equipment",
        ["system"],
        unique=False,
    )

    op.create_table(
        "failure_modes",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("equipment_type", sa.Text(), nullable=True),
        sa.Column("mechanism", sa.Text(), nullable=True),
        sa.Column("cause", sa.Text(), nullable=True),
        sa.Column("symptom", sa.Text(), nullable=True),
        sa.Column("consequence_category", sa.Text(), nullable=True),
        sa.Column("import_batch_id", sa.UUID(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["import_batch_id"],
            ["import_batches.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "name",
            "equipment_type",
            name="uq_failure_modes_name_equipment_type",
        ),
    )
    op.create_index(
        op.f("ix_failure_modes_consequence_category"),
        "failure_modes",
        ["consequence_category"],
        unique=False,
    )
    op.create_index(
        op.f("ix_failure_modes_equipment_type"),
        "failure_modes",
        ["equipment_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_failure_modes_import_batch_id"),
        "failure_modes",
        ["import_batch_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_failure_modes_name"),
        "failure_modes",
        ["name"],
        unique=False,
    )

    op.create_table(
        "import_validation_results",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("import_batch_id", sa.UUID(), nullable=False),
        sa.Column("severity", sa.Text(), nullable=False),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("source_column", sa.Text(), nullable=True),
        sa.Column("source_row_number", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "severity IN ('info', 'warning', 'error')",
            name="ck_import_validation_results_severity",
        ),
        sa.ForeignKeyConstraint(
            ["import_batch_id"],
            ["import_batches.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_import_validation_results_code"),
        "import_validation_results",
        ["code"],
        unique=False,
    )
    op.create_index(
        op.f("ix_import_validation_results_import_batch_id"),
        "import_validation_results",
        ["import_batch_id"],
        unique=False,
    )

    op.create_table(
        "maintenance_strategies",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("strategy_number", sa.Text(), nullable=True),
        sa.Column("task_number", sa.Text(), nullable=True),
        sa.Column("equipment_id", sa.UUID(), nullable=True),
        sa.Column("functional_location", sa.Text(), nullable=True),
        sa.Column("task_description", sa.Text(), nullable=False),
        sa.Column("strategy_type", sa.Text(), nullable=False),
        sa.Column("frequency_value", sa.Numeric(12, 2), nullable=True),
        sa.Column("frequency_unit", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("import_batch_id", sa.UUID(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "strategy_type IN ('time_based', 'condition_based', "
            "'inspection', 'lubrication', 'statutory', 'other')",
            name="ck_maintenance_strategies_strategy_type",
        ),
        sa.CheckConstraint(
            "status IN ('active', 'inactive', 'draft')",
            name="ck_maintenance_strategies_status",
        ),
        sa.CheckConstraint(
            "equipment_id IS NOT NULL OR functional_location IS NOT NULL",
            name="ck_maintenance_strategies_has_asset_reference",
        ),
        sa.ForeignKeyConstraint(
            ["equipment_id"],
            ["equipment.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["import_batch_id"],
            ["import_batches.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_maintenance_strategies_equipment_id"),
        "maintenance_strategies",
        ["equipment_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_maintenance_strategies_functional_location"),
        "maintenance_strategies",
        ["functional_location"],
        unique=False,
    )
    op.create_index(
        op.f("ix_maintenance_strategies_import_batch_id"),
        "maintenance_strategies",
        ["import_batch_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_maintenance_strategies_strategy_number"),
        "maintenance_strategies",
        ["strategy_number"],
        unique=False,
    )
    op.create_index(
        op.f("ix_maintenance_strategies_task_number"),
        "maintenance_strategies",
        ["task_number"],
        unique=False,
    )

    op.create_table(
        "work_orders",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("order_number", sa.Text(), nullable=False),
        sa.Column("notification_number", sa.Text(), nullable=True),
        sa.Column("equipment_id", sa.UUID(), nullable=True),
        sa.Column("functional_location", sa.Text(), nullable=True),
        sa.Column("order_type", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=True),
        sa.Column("priority", sa.Text(), nullable=True),
        sa.Column("maintenance_activity_type", sa.Text(), nullable=False),
        sa.Column("short_text", sa.Text(), nullable=True),
        sa.Column("long_text", sa.Text(), nullable=True),
        sa.Column("created_at_source", sa.DateTime(timezone=True), nullable=True),
        sa.Column("required_by_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("total_cost", sa.Numeric(14, 2), nullable=True),
        sa.Column("downtime_hours", sa.Numeric(12, 2), nullable=True),
        sa.Column("import_batch_id", sa.UUID(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "maintenance_activity_type IN ('corrective', 'preventive', "
            "'emergency', 'inspection', 'condition_monitoring', 'other', "
            "'unknown')",
            name="ck_work_orders_maintenance_activity_type",
        ),
        sa.ForeignKeyConstraint(
            ["equipment_id"],
            ["equipment.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["import_batch_id"],
            ["import_batches.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("order_number"),
    )
    op.create_index(
        op.f("ix_work_orders_created_at_source"),
        "work_orders",
        ["created_at_source"],
        unique=False,
    )
    op.create_index(
        op.f("ix_work_orders_equipment_id"),
        "work_orders",
        ["equipment_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_work_orders_finished_at"),
        "work_orders",
        ["finished_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_work_orders_functional_location"),
        "work_orders",
        ["functional_location"],
        unique=False,
    )
    op.create_index(
        op.f("ix_work_orders_import_batch_id"),
        "work_orders",
        ["import_batch_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_work_orders_notification_number"),
        "work_orders",
        ["notification_number"],
        unique=False,
    )
    op.create_index(
        op.f("ix_work_orders_order_number"),
        "work_orders",
        ["order_number"],
        unique=True,
    )
    op.create_index(
        op.f("ix_work_orders_order_type"),
        "work_orders",
        ["order_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_work_orders_priority"),
        "work_orders",
        ["priority"],
        unique=False,
    )
    op.create_index(
        op.f("ix_work_orders_status"),
        "work_orders",
        ["status"],
        unique=False,
    )

    op.create_table(
        "work_order_failure_modes",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("work_order_id", sa.UUID(), nullable=False),
        sa.Column("failure_mode_id", sa.UUID(), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Numeric(4, 3), nullable=True),
        sa.Column("evidence", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "source IN ('user', 'rule', 'agent', 'import')",
            name="ck_work_order_failure_modes_source",
        ),
        sa.CheckConstraint(
            "confidence IS NULL OR (confidence >= 0 AND confidence <= 1)",
            name="ck_work_order_failure_modes_confidence_range",
        ),
        sa.ForeignKeyConstraint(
            ["failure_mode_id"],
            ["failure_modes.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["work_order_id"],
            ["work_orders.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "work_order_id",
            "failure_mode_id",
            name="uq_work_order_failure_modes_work_order_failure_mode",
        ),
    )
    op.create_index(
        op.f("ix_work_order_failure_modes_failure_mode_id"),
        "work_order_failure_modes",
        ["failure_mode_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_work_order_failure_modes_work_order_id"),
        "work_order_failure_modes",
        ["work_order_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        op.f("ix_work_order_failure_modes_work_order_id"),
        table_name="work_order_failure_modes",
    )
    op.drop_index(
        op.f("ix_work_order_failure_modes_failure_mode_id"),
        table_name="work_order_failure_modes",
    )
    op.drop_table("work_order_failure_modes")

    op.drop_index(op.f("ix_work_orders_status"), table_name="work_orders")
    op.drop_index(op.f("ix_work_orders_priority"), table_name="work_orders")
    op.drop_index(op.f("ix_work_orders_order_type"), table_name="work_orders")
    op.drop_index(op.f("ix_work_orders_order_number"), table_name="work_orders")
    op.drop_index(
        op.f("ix_work_orders_notification_number"),
        table_name="work_orders",
    )
    op.drop_index(
        op.f("ix_work_orders_import_batch_id"),
        table_name="work_orders",
    )
    op.drop_index(
        op.f("ix_work_orders_functional_location"),
        table_name="work_orders",
    )
    op.drop_index(op.f("ix_work_orders_finished_at"), table_name="work_orders")
    op.drop_index(op.f("ix_work_orders_equipment_id"), table_name="work_orders")
    op.drop_index(
        op.f("ix_work_orders_created_at_source"),
        table_name="work_orders",
    )
    op.drop_table("work_orders")

    op.drop_index(
        op.f("ix_maintenance_strategies_task_number"),
        table_name="maintenance_strategies",
    )
    op.drop_index(
        op.f("ix_maintenance_strategies_strategy_number"),
        table_name="maintenance_strategies",
    )
    op.drop_index(
        op.f("ix_maintenance_strategies_import_batch_id"),
        table_name="maintenance_strategies",
    )
    op.drop_index(
        op.f("ix_maintenance_strategies_functional_location"),
        table_name="maintenance_strategies",
    )
    op.drop_index(
        op.f("ix_maintenance_strategies_equipment_id"),
        table_name="maintenance_strategies",
    )
    op.drop_table("maintenance_strategies")

    op.drop_index(
        op.f("ix_import_validation_results_import_batch_id"),
        table_name="import_validation_results",
    )
    op.drop_index(
        op.f("ix_import_validation_results_code"),
        table_name="import_validation_results",
    )
    op.drop_table("import_validation_results")

    op.drop_index(op.f("ix_failure_modes_name"), table_name="failure_modes")
    op.drop_index(
        op.f("ix_failure_modes_import_batch_id"),
        table_name="failure_modes",
    )
    op.drop_index(
        op.f("ix_failure_modes_equipment_type"),
        table_name="failure_modes",
    )
    op.drop_index(
        op.f("ix_failure_modes_consequence_category"),
        table_name="failure_modes",
    )
    op.drop_table("failure_modes")

    op.drop_index(op.f("ix_equipment_system"), table_name="equipment")
    op.drop_index(op.f("ix_equipment_import_batch_id"), table_name="equipment")
    op.drop_index(
        op.f("ix_equipment_functional_location"),
        table_name="equipment",
    )
    op.drop_index(op.f("ix_equipment_equipment_type"), table_name="equipment")
    op.drop_index(op.f("ix_equipment_equipment_number"), table_name="equipment")
    op.drop_index(op.f("ix_equipment_criticality"), table_name="equipment")
    op.drop_table("equipment")

    op.drop_table("import_batches")
