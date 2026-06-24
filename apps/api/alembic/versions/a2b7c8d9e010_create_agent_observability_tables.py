"""create agent observability tables

Revision ID: a2b7c8d9e010
Revises: 9a1d2c3e4f50
Create Date: 2026-06-24 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a2b7c8d9e010"
down_revision: Union[str, Sequence[str], None] = "9a1d2c3e4f50"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "agent_runs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("conversation_id", sa.UUID(), nullable=False),
        sa.Column("user_message_id", sa.UUID(), nullable=True),
        sa.Column("assistant_message_id", sa.UUID(), nullable=True),
        sa.Column("provider", sa.Text(), nullable=False),
        sa.Column("model", sa.Text(), nullable=False),
        sa.Column(
            "status",
            sa.Text(),
            server_default=sa.text("'in_progress'"),
            nullable=False,
        ),
        sa.Column("total_latency_ms", sa.Integer(), nullable=True),
        sa.Column("input_tokens_estimate", sa.Integer(), nullable=True),
        sa.Column("output_tokens_estimate", sa.Integer(), nullable=True),
        sa.Column(
            "model_call_count",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "tool_call_count",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column("tool_metadata", sa.JSON(), nullable=True),
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
            name="ck_agent_runs_status",
        ),
        sa.ForeignKeyConstraint(
            ["assistant_message_id"],
            ["messages.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["conversations.id"],
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
        op.f("ix_agent_runs_assistant_message_id"),
        "agent_runs",
        ["assistant_message_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_agent_runs_conversation_id"),
        "agent_runs",
        ["conversation_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_agent_runs_user_message_id"),
        "agent_runs",
        ["user_message_id"],
        unique=False,
    )

    op.create_table(
        "model_calls",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("agent_run_id", sa.UUID(), nullable=False),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("call_type", sa.Text(), nullable=False),
        sa.Column("provider", sa.Text(), nullable=False),
        sa.Column("model", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("input_tokens_estimate", sa.Integer(), nullable=False),
        sa.Column("output_tokens_estimate", sa.Integer(), nullable=True),
        sa.Column("max_output_tokens", sa.Integer(), nullable=False),
        sa.Column("requested_tool_count", sa.Integer(), nullable=False),
        sa.Column("response_tool_call_count", sa.Integer(), nullable=True),
        sa.Column("error_type", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('completed', 'failed')",
            name="ck_model_calls_status",
        ),
        sa.ForeignKeyConstraint(
            ["agent_run_id"],
            ["agent_runs.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_model_calls_agent_run_id"),
        "model_calls",
        ["agent_run_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_model_calls_agent_run_id"), table_name="model_calls")
    op.drop_table("model_calls")
    op.drop_index(op.f("ix_agent_runs_user_message_id"), table_name="agent_runs")
    op.drop_index(
        op.f("ix_agent_runs_conversation_id"),
        table_name="agent_runs",
    )
    op.drop_index(
        op.f("ix_agent_runs_assistant_message_id"),
        table_name="agent_runs",
    )
    op.drop_table("agent_runs")
