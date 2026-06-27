"""backfill strategy functional locations

Revision ID: e6f7a8b9c012
Revises: c5d6e7f8a901
Create Date: 2026-06-27 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "e6f7a8b9c012"
down_revision: Union[str, Sequence[str], None] = "c5d6e7f8a901"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Backfill strategy locations from linked equipment."""
    op.execute(
        """
        UPDATE maintenance_strategies AS strategy
        SET functional_location = equipment.functional_location
        FROM equipment
        WHERE strategy.equipment_id = equipment.id
          AND strategy.functional_location IS NULL
          AND equipment.functional_location IS NOT NULL
        """
    )


def downgrade() -> None:
    """Remove values that were backfilled from linked equipment."""
    op.execute(
        """
        UPDATE maintenance_strategies AS strategy
        SET functional_location = NULL
        FROM equipment
        WHERE strategy.equipment_id = equipment.id
          AND strategy.functional_location = equipment.functional_location
        """
    )
