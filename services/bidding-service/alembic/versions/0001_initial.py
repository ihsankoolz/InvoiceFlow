"""initial

Revision ID: 0001
Revises:
Create Date: 2026-04-01 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "bids",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("invoice_token", sa.String(36), nullable=False),
        sa.Column("investor_id", sa.Integer(), nullable=False),
        sa.Column("bid_amount", sa.DECIMAL(12, 2), nullable=False),
        sa.Column(
            "status",
            sa.Enum("PENDING", "ACCEPTED", "REJECTED", "CANCELLED", name="bid_status"),
            server_default="PENDING",
        ),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            onupdate=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("invoice_token", "investor_id", name="unique_bid"),
    )


def downgrade() -> None:
    op.drop_table("bids")
    sa.Enum(name="bid_status").drop(op.get_bind())
