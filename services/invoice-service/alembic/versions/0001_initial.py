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
        "invoices",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("invoice_token", sa.String(36), nullable=False),
        sa.Column("seller_id", sa.Integer(), nullable=False),
        sa.Column("debtor_name", sa.String(255), nullable=True),
        sa.Column("debtor_uen", sa.String(20), nullable=False),
        sa.Column("amount", sa.DECIMAL(12, 2), nullable=False),
        sa.Column("due_date", sa.DateTime(), nullable=False),
        sa.Column("currency", sa.String(3), server_default="SGD"),
        sa.Column("pdf_url", sa.String(500), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "DRAFT",
                "LISTED",
                "FINANCED",
                "REPAID",
                "DEFAULTED",
                "REJECTED",
                name="invoice_status",
            ),
            server_default="DRAFT",
        ),
        sa.Column("extracted_data", sa.JSON(), nullable=True),
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
    op.drop_table("invoices")
    sa.Enum(name="invoice_status").drop(op.get_bind())
