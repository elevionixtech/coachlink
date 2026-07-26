"""client joining date

Adds client.joining_date — when the client joined the organisation. Nullable, so
existing clients are unaffected.

Revision ID: a3c5e7f9b1d2
Revises: f2b4c6d8e0a1
Create Date: 2026-07-26 13:30:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = 'a3c5e7f9b1d2'
down_revision: str | Sequence[str] | None = 'f2b4c6d8e0a1'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('client', sa.Column('joining_date', sa.Date(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('client', 'joining_date')
