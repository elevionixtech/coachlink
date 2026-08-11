"""batch days of week

Which days of the week a batch runs, e.g. ["Mon", "Wed", "Fri"] (§5.5).

Revision ID: b6d8f0a2c4e5
Revises: a4c6e8f0b2d3
Create Date: 2026-08-11 09:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = 'b6d8f0a2c4e5'
down_revision: str | Sequence[str] | None = 'a4c6e8f0b2d3'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

JSONVariant = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'batch',
        sa.Column('days_of_week', JSONVariant, nullable=False, server_default='[]'),
    )
    op.alter_column('batch', 'days_of_week', server_default=None)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('batch', 'days_of_week')
