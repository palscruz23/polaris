"""merge login and scheduled review heads

Revision ID: c9d0e1f2a345
Revises: 8d2f4a6b7c90, b8c9d0e1f234
Create Date: 2026-07-01 00:00:00.000000

"""
from typing import Sequence, Union


revision: str = "c9d0e1f2a345"
down_revision: Union[str, Sequence[str], None] = (
    "8d2f4a6b7c90",
    "b8c9d0e1f234",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
