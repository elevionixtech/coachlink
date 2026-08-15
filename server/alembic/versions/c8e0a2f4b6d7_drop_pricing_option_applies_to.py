"""drop pricing_option.applies_to

Pricing options are no longer gated by client account type — a service's options are all
available to any client, the operator chooses (§3.7). Removes the now-unused column.

Revision ID: c8e0a2f4b6d7
Revises: b6d8f0a2c4e5
Create Date: 2026-08-15 09:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = 'c8e0a2f4b6d7'
down_revision: str | Sequence[str] | None = 'b6d8f0a2c4e5'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

JSONVariant = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_column('pricing_option', 'applies_to')


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column(
        'pricing_option',
        sa.Column('applies_to', JSONVariant, nullable=False, server_default='[]'),
    )
    op.alter_column('pricing_option', 'applies_to', server_default=None)
