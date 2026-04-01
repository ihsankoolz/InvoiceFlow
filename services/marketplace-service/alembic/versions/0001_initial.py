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
        "listings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("invoice_token", sa.String(36), nullable=False),
        sa.Column("seller_id", sa.Integer(), nullable=False),
        sa.Column("debtor_uen", sa.String(20), nullable=False),
        sa.Column("amount", sa.DECIMAL(12, 2), nullable=False),
        sa.Column("minimum_bid", sa.DECIMAL(12, 2), nullable=False),
        sa.Column(
            "urgency_level",
            sa.Enum("LOW", "MEDIUM", "HIGH", "CRITICAL", name="urgency_level_enum"),
            nullable=False,
        ),
        sa.Column("deadline", sa.DateTime(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("ACTIVE", "CLOSED", "EXPIRED", name="status_enum"),
            server_default="ACTIVE",
        ),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            onupdate=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("invoice_token"),
    )


def downgrade() -> None:
    op.drop_table("listings")
    sa.Enum(name="urgency_level_enum").drop(op.get_bind())
    sa.Enum(name="status_enum").drop(op.get_bind())
