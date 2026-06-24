"""add message metadata

Revision ID: 9a1d2c3e4f50
Revises: 7b4f6d8c2a10
Create Date: 2026-06-24 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "9a1d2c3e4f50"
down_revision: Union[str, Sequence[str], None] = "7b4f6d8c2a10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("messages", sa.Column("metadata", sa.JSON(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("messages", "metadata")
