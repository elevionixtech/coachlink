"""invoice bill_to_gstin

GSTIN for a non-client ad-hoc invoice recipient (§3.8), so it prints on the invoice like
a client's GSTIN does.

Revision ID: e0a2c4d6f8b9
Revises: d8f0b2c4e6a7
Create Date: 2026-07-27 13:30:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = 'e0a2c4d6f8b9'
down_revision: str | Sequence[str] | None = 'd8f0b2c4e6a7'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('invoice', sa.Column('bill_to_gstin', sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('invoice', 'bill_to_gstin')
