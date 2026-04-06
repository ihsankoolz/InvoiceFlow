"""fix due_date column type from DATE to DATETIME

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-07 00:00:00.000000

The due_date column was originally created as DATE (date-only, no time component).
This caused the time portion of invoice due dates to be silently dropped on insert,
resulting in all due dates being stored as midnight UTC regardless of the actual time
entered by the user.

This migration changes the column to DATETIME so the full timestamp is preserved.
Existing rows will have their due_date unchanged (they remain at 00:00:00, which
reflects what was actually stored — the original time data was already lost).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "invoices",
        "due_date",
        existing_type=sa.Date(),
        type_=sa.DateTime(),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "invoices",
        "due_date",
        existing_type=sa.DateTime(),
        type_=sa.Date(),
        existing_nullable=False,
    )
