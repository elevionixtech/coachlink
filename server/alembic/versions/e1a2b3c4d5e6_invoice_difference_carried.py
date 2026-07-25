"""invoice difference_carried flag

Records whether a payment difference was carried forward (vs settled), so the listing
can surface only the still-consequential ones (§3.8).

Revision ID: e1a2b3c4d5e6
Revises: d5e9b1f2a3c7
Create Date: 2026-07-26 09:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = 'e1a2b3c4d5e6'
down_revision: str | Sequence[str] | None = 'd5e9b1f2a3c7'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'invoice',
        sa.Column('difference_carried', sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.alter_column('invoice', 'difference_carried', server_default=None)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('invoice', 'difference_carried')
