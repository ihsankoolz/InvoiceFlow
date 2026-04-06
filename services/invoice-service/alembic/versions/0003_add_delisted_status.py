"""add DELISTED to invoice_status enum

Revision ID: 0003
Revises: 0002
Create Date: 2026-04-07 00:00:00.000000

MySQL ENUM columns must be explicitly altered to add new values.
This adds DELISTED to the invoice_status enum so bulk-delisted invoices
can be marked with a distinct status from DRAFT.
"""

from typing import Sequence, Union

from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE invoices MODIFY COLUMN status ENUM("
        "'DRAFT','LISTED','FINANCED','REPAID','DEFAULTED','REJECTED','EXPIRED','DELISTED'"
        ") NOT NULL DEFAULT 'DRAFT'"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE invoices MODIFY COLUMN status ENUM("
        "'DRAFT','LISTED','FINANCED','REPAID','DEFAULTED','REJECTED','EXPIRED'"
        ") NOT NULL DEFAULT 'DRAFT'"
    )
