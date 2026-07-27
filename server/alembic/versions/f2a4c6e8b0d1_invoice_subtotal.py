"""invoice subtotal

The pre-discount rate, stored so an invoice can show its discount even after the service
rate changes (§3.7). Backfilled from each subscription invoice's service rate; ad-hoc
invoices have none.

Revision ID: f2a4c6e8b0d1
Revises: e0a2c4d6f8b9
Create Date: 2026-07-27 15:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = 'f2a4c6e8b0d1'
down_revision: str | Sequence[str] | None = 'e0a2c4d6f8b9'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('invoice', sa.Column('subtotal', sa.Numeric(12, 2), nullable=True))
    op.execute("""
        UPDATE invoice i SET subtotal = s.rate
        FROM subscription sub JOIN service s ON s.id = sub.service_id
        WHERE sub.id = i.subscription_id
    """)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('invoice', 'subtotal')
