"""ad-hoc invoices

Allow one-off invoices raised directly against a client: invoice.subscription_id becomes
nullable and invoice.description holds the hand-entered line (§3.8).

Revision ID: c6e8a0b2d4f5
Revises: b4d6f8a0c2e3
Create Date: 2026-07-27 11:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = 'c6e8a0b2d4f5'
down_revision: str | Sequence[str] | None = 'b4d6f8a0c2e3'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('invoice', sa.Column('description', sa.Text(), nullable=True))
    op.alter_column('invoice', 'subscription_id', existing_type=sa.Uuid(), nullable=True)


def downgrade() -> None:
    """Downgrade schema."""
    # Ad-hoc invoices (NULL subscription_id) must be cleared before restoring NOT NULL.
    op.execute("DELETE FROM invoice WHERE subscription_id IS NULL")
    op.alter_column('invoice', 'subscription_id', existing_type=sa.Uuid(), nullable=False)
    op.drop_column('invoice', 'description')
