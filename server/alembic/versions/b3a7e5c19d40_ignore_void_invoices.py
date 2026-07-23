"""ignore void invoices in generation

A voided invoice bills nothing, so generation now treats its period as unbilled and
re-issues it (§3.8). That means the replacement has to coexist with the voided row, so
the one-per-period uniqueness becomes a partial index excluding void — live invoices are
still one per period, which is what idempotency rests on.

Revision ID: b3a7e5c19d40
Revises: 9f1d2c7a4e88
Create Date: 2026-07-22 22:05:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = 'b3a7e5c19d40'
down_revision: str | Sequence[str] | None = '9f1d2c7a4e88'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_constraint('invoice_one_per_period', 'invoice', type_='unique')
    op.create_index(
        'invoice_one_per_period',
        'invoice',
        ['subscription_id', 'period_start'],
        unique=True,
        postgresql_where=sa.text("status <> 'void'"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Reverting needs live-only uniqueness to hold across every row again. If a period
    # was re-issued after a void, both rows exist and the plain constraint cannot be
    # recreated — void the duplicates or delete them first.
    op.drop_index('invoice_one_per_period', table_name='invoice')
    op.create_unique_constraint(
        'invoice_one_per_period', 'invoice', ['subscription_id', 'period_start']
    )
