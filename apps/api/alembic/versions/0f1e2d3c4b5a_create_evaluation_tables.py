"""create evaluation tables

Revision ID: 0f1e2d3c4b5a
Revises: f1a2b3c4d567
Create Date: 2026-06-27 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0f1e2d3c4b5a"
down_revision: Union[str, Sequence[str], None] = "f1a2b3c4d567"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "eval_suites",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
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
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_eval_suites_name"),
    )

    op.create_table(
        "eval_cases",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("suite_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("conversation_memory", sa.Text(), nullable=True),
        sa.Column("expectations", sa.JSON(), nullable=False),
        sa.Column("rubric", sa.JSON(), nullable=True),
        sa.Column("tags", sa.JSON(), nullable=True),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
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
            ["suite_id"],
            ["eval_suites.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "suite_id",
            "name",
            name="uq_eval_cases_suite_name",
        ),
    )
    op.create_index(
        op.f("ix_eval_cases_suite_id"),
        "eval_cases",
        ["suite_id"],
        unique=False,
    )

    op.create_table(
        "eval_runs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("suite_id", sa.UUID(), nullable=False),
        sa.Column("provider", sa.Text(), nullable=False),
        sa.Column("model", sa.Text(), nullable=False),
        sa.Column(
            "status",
            sa.Text(),
            server_default=sa.text("'in_progress'"),
            nullable=False,
        ),
        sa.Column("git_commit", sa.Text(), nullable=True),
        sa.Column("dataset_version", sa.Text(), nullable=True),
        sa.Column(
            "case_count",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "passed_count",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "failed_count",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column("aggregate_score", sa.Float(), nullable=True),
        sa.Column("run_metadata", sa.JSON(), nullable=True),
        sa.Column("reviewer_notes", sa.Text(), nullable=True),
        sa.Column("error_type", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('in_progress', 'completed', 'failed')",
            name="ck_eval_runs_status",
        ),
        sa.ForeignKeyConstraint(
            ["suite_id"],
            ["eval_suites.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_eval_runs_suite_id"),
        "eval_runs",
        ["suite_id"],
        unique=False,
    )

    op.create_table(
        "eval_case_results",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("eval_run_id", sa.UUID(), nullable=False),
        sa.Column("eval_case_id", sa.UUID(), nullable=False),
        sa.Column("conversation_id", sa.UUID(), nullable=True),
        sa.Column("user_message_id", sa.UUID(), nullable=True),
        sa.Column("assistant_message_id", sa.UUID(), nullable=True),
        sa.Column("agent_run_id", sa.UUID(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("scores", sa.JSON(), nullable=False),
        sa.Column("checks", sa.JSON(), nullable=False),
        sa.Column("trace", sa.JSON(), nullable=True),
        sa.Column("assistant_answer", sa.Text(), nullable=True),
        sa.Column("failure_category", sa.Text(), nullable=True),
        sa.Column(
            "review_status",
            sa.Text(),
            server_default=sa.text("'pending'"),
            nullable=False,
        ),
        sa.Column("reviewer_notes", sa.Text(), nullable=True),
        sa.Column("error_type", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('passed', 'failed', 'error')",
            name="ck_eval_case_results_status",
        ),
        sa.CheckConstraint(
            "review_status IN ('pending', 'accepted', 'rejected')",
            name="ck_eval_case_results_review_status",
        ),
        sa.ForeignKeyConstraint(
            ["agent_run_id"],
            ["agent_runs.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["assistant_message_id"],
            ["messages.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["conversations.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["eval_case_id"],
            ["eval_cases.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["eval_run_id"],
            ["eval_runs.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_message_id"],
            ["messages.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_eval_case_results_agent_run_id"),
        "eval_case_results",
        ["agent_run_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_eval_case_results_assistant_message_id"),
        "eval_case_results",
        ["assistant_message_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_eval_case_results_conversation_id"),
        "eval_case_results",
        ["conversation_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_eval_case_results_eval_case_id"),
        "eval_case_results",
        ["eval_case_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_eval_case_results_eval_run_id"),
        "eval_case_results",
        ["eval_run_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_eval_case_results_user_message_id"),
        "eval_case_results",
        ["user_message_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        op.f("ix_eval_case_results_user_message_id"),
        table_name="eval_case_results",
    )
    op.drop_index(
        op.f("ix_eval_case_results_eval_run_id"),
        table_name="eval_case_results",
    )
    op.drop_index(
        op.f("ix_eval_case_results_eval_case_id"),
        table_name="eval_case_results",
    )
    op.drop_index(
        op.f("ix_eval_case_results_conversation_id"),
        table_name="eval_case_results",
    )
    op.drop_index(
        op.f("ix_eval_case_results_assistant_message_id"),
        table_name="eval_case_results",
    )
    op.drop_index(
        op.f("ix_eval_case_results_agent_run_id"),
        table_name="eval_case_results",
    )
    op.drop_table("eval_case_results")
    op.drop_index(op.f("ix_eval_runs_suite_id"), table_name="eval_runs")
    op.drop_table("eval_runs")
    op.drop_index(op.f("ix_eval_cases_suite_id"), table_name="eval_cases")
    op.drop_table("eval_cases")
    op.drop_table("eval_suites")
