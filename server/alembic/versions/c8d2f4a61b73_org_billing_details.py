"""org billing details

Address, billing email, phone and GSTIN for the organisation — printed on every invoice
(§3.9). Real columns rather than settings JSON: a tax invoice needs them explicit and
queryable. Nullable, so existing orgs keep working until an admin fills them in.

Revision ID: c8d2f4a61b73
Revises: b3a7e5c19d40
Create Date: 2026-07-23 09:10:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = 'c8d2f4a61b73'
down_revision: str | Sequence[str] | None = 'b3a7e5c19d40'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('organisation', sa.Column('address', sa.Text(), nullable=True))
    op.add_column('organisation', sa.Column('billing_email', sa.Text(), nullable=True))
    op.add_column('organisation', sa.Column('phone', sa.Text(), nullable=True))
    op.add_column('organisation', sa.Column('gstin', sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('organisation', 'gstin')
    op.drop_column('organisation', 'phone')
    op.drop_column('organisation', 'billing_email')
    op.drop_column('organisation', 'address')
