"""invoice period dates

Gives an invoice explicit period_start/period_end so a period can be extended (§3.8),
and re-keys idempotency onto period_start: once end dates are editable a label like
"Jul 2026" can legitimately describe two different periods, so it can no longer be the
uniqueness key.

Backfill is exact rather than approximate: issue_date has always been the period start
(missing_periods emitted the period start as the issue date), so period_start = issue_date
and period_end is the day before the next period begins.

Revision ID: 9f1d2c7a4e88
Revises: 7c4e1a9d3b52
Create Date: 2026-07-22 21:20:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = '9f1d2c7a4e88'
down_revision: str | Sequence[str] | None = '7c4e1a9d3b52'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Period length per billing interval, as a Postgres interval expression.
STEP = {
    'Monthly': '1 month',
    'Weekly': '7 days',
    'Quarterly': '3 months',
    'Semi-Annual': '6 months',
    'Annual': '1 year',
}


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('invoice', sa.Column('period_start', sa.Date(), nullable=True))
    op.add_column('invoice', sa.Column('period_end', sa.Date(), nullable=True))
    op.add_column(
        'invoice',
        sa.Column('period_end_adjusted', sa.Boolean(), nullable=False,
                  server_default=sa.false()),
    )

    # period_start == the old issue_date, exactly.
    op.execute("UPDATE invoice SET period_start = issue_date")

    # period_end = next period start - 1 day, derived from the service's interval.
    for interval, step in STEP.items():
        op.execute(f"""
            UPDATE invoice i
            SET period_end = (i.issue_date + INTERVAL '{step}' - INTERVAL '1 day')::date
            FROM subscription s JOIN service sv ON sv.id = s.service_id
            WHERE s.id = i.subscription_id AND sv.billing_interval = '{interval}'
        """)
    # One-time services bill a single day.
    op.execute("UPDATE invoice SET period_end = period_start WHERE period_end IS NULL")

    op.alter_column('invoice', 'period_start', nullable=False)
    op.alter_column('invoice', 'period_end', nullable=False)
    op.alter_column('invoice', 'period_end_adjusted', server_default=None)

    op.drop_constraint('invoice_one_per_period', 'invoice', type_='unique')
    op.create_unique_constraint(
        'invoice_one_per_period', 'invoice', ['subscription_id', 'period_start']
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('invoice_one_per_period', 'invoice', type_='unique')
    op.create_unique_constraint(
        'invoice_one_per_period', 'invoice', ['subscription_id', 'period_label']
    )
    op.drop_column('invoice', 'period_end_adjusted')
    op.drop_column('invoice', 'period_end')
    op.drop_column('invoice', 'period_start')
