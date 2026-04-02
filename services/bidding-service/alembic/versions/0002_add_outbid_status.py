"""add OUTBID to bid_status enum

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-01 00:02:00.000000
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
        "bids",
        "status",
        type_=sa.Enum("PENDING", "ACCEPTED", "REJECTED", "CANCELLED", "OUTBID", name="bid_status"),
        existing_type=sa.Enum("PENDING", "ACCEPTED", "REJECTED", "CANCELLED", name="bid_status"),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "bids",
        "status",
        type_=sa.Enum("PENDING", "ACCEPTED", "REJECTED", "CANCELLED", name="bid_status"),
        existing_type=sa.Enum("PENDING", "ACCEPTED", "REJECTED", "CANCELLED", "OUTBID", name="bid_status"),
        existing_nullable=True,
    )
