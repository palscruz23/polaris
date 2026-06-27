"""create feedback responses

Revision ID: c5d6e7f8a901
Revises: b4c3d2e1f090
Create Date: 2026-06-27 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c5d6e7f8a901"
down_revision: Union[str, Sequence[str], None] = "b4c3d2e1f090"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "feedback_responses",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("conversation_id", sa.UUID(), nullable=True),
        sa.Column("usefulness_rating", sa.Integer(), nullable=True),
        sa.Column("confidence_rating", sa.Integer(), nullable=True),
        sa.Column("most_useful", sa.Text(), nullable=True),
        sa.Column("improvement_priority", sa.Text(), nullable=True),
        sa.Column("future_feature_interest", sa.JSON(), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "usefulness_rating IS NULL OR "
            "(usefulness_rating >= 1 AND usefulness_rating <= 5)",
            name="ck_feedback_responses_usefulness_rating",
        ),
        sa.CheckConstraint(
            "confidence_rating IS NULL OR "
            "(confidence_rating >= 1 AND confidence_rating <= 5)",
            name="ck_feedback_responses_confidence_rating",
        ),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["conversations.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_feedback_responses_conversation_id"),
        "feedback_responses",
        ["conversation_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_feedback_responses_user_id"),
        "feedback_responses",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        op.f("ix_feedback_responses_user_id"),
        table_name="feedback_responses",
    )
    op.drop_index(
        op.f("ix_feedback_responses_conversation_id"),
        table_name="feedback_responses",
    )
    op.drop_table("feedback_responses")
