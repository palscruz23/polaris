"""create scheduled review tables

Revision ID: b8c9d0e1f234
Revises: e6f7a8b9c012
Create Date: 2026-06-30 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b8c9d0e1f234"
down_revision: Union[str, Sequence[str], None] = "e6f7a8b9c012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "scheduled_review_runs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("template_id", sa.Text(), nullable=False),
        sa.Column(
            "status",
            sa.Text(),
            server_default=sa.text("'running'"),
            nullable=False,
        ),
        sa.Column("window_start_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window_end_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("report_markdown", sa.Text(), nullable=True),
        sa.Column("summary_json", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "template_id IN ('breakdown_strategy_gap', "
            "'bad_actor_watchlist', 'maintenance_strategy_health_check')",
            name="ck_scheduled_review_runs_template_id",
        ),
        sa.CheckConstraint(
            "window_start_at < window_end_at",
            name="ck_scheduled_review_runs_window_start_before_end",
        ),
        sa.CheckConstraint(
            "status IN ('running', 'succeeded', 'partially_succeeded', "
            "'failed')",
            name="ck_scheduled_review_runs_status",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_scheduled_review_runs_template_id"),
        "scheduled_review_runs",
        ["template_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_scheduled_review_runs_window_start_at"),
        "scheduled_review_runs",
        ["window_start_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_scheduled_review_runs_window_end_at"),
        "scheduled_review_runs",
        ["window_end_at"],
        unique=False,
    )

    op.create_table(
        "scheduled_review_deliveries",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("scheduled_review_run_id", sa.UUID(), nullable=False),
        sa.Column("provider", sa.Text(), nullable=False),
        sa.Column("destination_label", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.Text(),
            server_default=sa.text("'pending'"),
            nullable=False,
        ),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("provider_response_json", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "provider IN ('teams')",
            name="ck_scheduled_review_deliveries_provider",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'sent', 'failed')",
            name="ck_scheduled_review_deliveries_status",
        ),
        sa.ForeignKeyConstraint(
            ["scheduled_review_run_id"],
            ["scheduled_review_runs.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_scheduled_review_deliveries_scheduled_review_run_id"),
        "scheduled_review_deliveries",
        ["scheduled_review_run_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_scheduled_review_deliveries_scheduled_review_run_id"),
        table_name="scheduled_review_deliveries",
    )
    op.drop_table("scheduled_review_deliveries")
    op.drop_index(
        op.f("ix_scheduled_review_runs_window_end_at"),
        table_name="scheduled_review_runs",
    )
    op.drop_index(
        op.f("ix_scheduled_review_runs_window_start_at"),
        table_name="scheduled_review_runs",
    )
    op.drop_index(
        op.f("ix_scheduled_review_runs_template_id"),
        table_name="scheduled_review_runs",
    )
    op.drop_table("scheduled_review_runs")
