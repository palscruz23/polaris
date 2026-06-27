"""drop equipment parent equipment number

Revision ID: f1a2b3c4d567
Revises: e6f7a8b9c012
Create Date: 2026-06-27 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "f1a2b3c4d567"
down_revision: Union[str, Sequence[str], None] = "e6f7a8b9c012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Remove the unused equipment parent-number column."""
    op.drop_column("equipment", "parent_equipment_number")


def downgrade() -> None:
    """Restore the parent-number column."""
    op.add_column(
        "equipment",
        sa.Column("parent_equipment_number", sa.Text(), nullable=True),
    )
