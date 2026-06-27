"""create user login events

Revision ID: 8d2f4a6b7c90
Revises: 0f1e2d3c4b5a
Create Date: 2026-06-27 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "8d2f4a6b7c90"
down_revision: Union[str, Sequence[str], None] = "0f1e2d3c4b5a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "user_login_events",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_user_login_events_created_at"),
        "user_login_events",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_user_login_events_user_id"),
        "user_login_events",
        ["user_id"],
        unique=False,
    )

    op.execute(
        """
        INSERT INTO user_login_events (id, user_id, created_at)
        SELECT id, user_id, created_at
        FROM user_sessions
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        op.f("ix_user_login_events_user_id"),
        table_name="user_login_events",
    )
    op.drop_index(
        op.f("ix_user_login_events_created_at"),
        table_name="user_login_events",
    )
    op.drop_table("user_login_events")
