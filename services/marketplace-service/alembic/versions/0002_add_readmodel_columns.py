"""add read-model columns to listings

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-01 00:01:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("listings", sa.Column("face_value", sa.DECIMAL(12, 2), nullable=True))
    op.add_column("listings", sa.Column("debtor_name", sa.String(255), nullable=True))
    op.add_column("listings", sa.Column("current_bid", sa.DECIMAL(12, 2), nullable=True))
    op.add_column(
        "listings",
        sa.Column("bid_count", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("listings", "bid_count")
    op.drop_column("listings", "current_bid")
    op.drop_column("listings", "debtor_name")
    op.drop_column("listings", "face_value")
