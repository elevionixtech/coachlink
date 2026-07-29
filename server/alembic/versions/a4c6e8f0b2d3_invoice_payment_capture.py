"""invoice payment date and method

Capture when a payment was received and how (UPI, Cash, ...) when an invoice is marked
paid (§3.8). Nullable — unset for unpaid invoices and for those paid before this change.

Revision ID: a4c6e8f0b2d3
Revises: f2a4c6e8b0d1
Create Date: 2026-07-29 09:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = 'a4c6e8f0b2d3'
down_revision: str | Sequence[str] | None = 'f2a4c6e8b0d1'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('invoice', sa.Column('payment_date', sa.Date(), nullable=True))
    op.add_column(
        'invoice',
        sa.Column(
            'payment_method',
            sa.Enum('UPI', 'Cash', 'Bank Transfer', 'Card', 'Cheque', 'Other',
                    name='payment_method', native_enum=False, length=30),
            nullable=True,
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('invoice', 'payment_method')
    op.drop_column('invoice', 'payment_date')
