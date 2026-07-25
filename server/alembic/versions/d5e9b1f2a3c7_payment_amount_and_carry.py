"""payment amount and carry-forward balance

invoice.paid_amount records what was actually received; subscription.carry_balance is a
signed running total of under/overpayments carried into the next generated invoice (§3.8).

Revision ID: d5e9b1f2a3c7
Revises: c8d2f4a61b73
Create Date: 2026-07-25 10:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = 'd5e9b1f2a3c7'
down_revision: str | Sequence[str] | None = 'c8d2f4a61b73'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('invoice', sa.Column('paid_amount', sa.Numeric(12, 2), nullable=True))
    op.add_column(
        'subscription',
        sa.Column('carry_balance', sa.Numeric(12, 2), nullable=False, server_default='0'),
    )
    op.alter_column('subscription', 'carry_balance', server_default=None)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('subscription', 'carry_balance')
    op.drop_column('invoice', 'paid_amount')
