"""org payment details

UPI id and bank-transfer details on the organisation, printed on invoices so a client
can pay online (§3.9); show_payment_qr toggles the scannable UPI QR.

Revision ID: b4d6f8a0c2e3
Revises: a3c5e7f9b1d2
Create Date: 2026-07-27 09:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = 'b4d6f8a0c2e3'
down_revision: str | Sequence[str] | None = 'a3c5e7f9b1d2'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('organisation', sa.Column('upi_id', sa.Text(), nullable=True))
    op.add_column('organisation', sa.Column('bank_account_name', sa.Text(), nullable=True))
    op.add_column('organisation', sa.Column('bank_account_number', sa.Text(), nullable=True))
    op.add_column('organisation', sa.Column('bank_ifsc', sa.Text(), nullable=True))
    op.add_column('organisation', sa.Column('bank_name', sa.Text(), nullable=True))
    op.add_column(
        'organisation',
        sa.Column('show_payment_qr', sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.alter_column('organisation', 'show_payment_qr', server_default=None)


def downgrade() -> None:
    """Downgrade schema."""
    for col in ('show_payment_qr', 'bank_name', 'bank_ifsc', 'bank_account_number',
                'bank_account_name', 'upi_id'):
        op.drop_column('organisation', col)
