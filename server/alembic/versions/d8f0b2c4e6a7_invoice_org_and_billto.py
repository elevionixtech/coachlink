"""invoice org_id and non-client bill-to

Invoices carry org_id directly (so a client-less ad-hoc invoice is still tenant-scoped),
client_id becomes nullable, and bill_to_* hold a non-client recipient's details (§3.8).

Revision ID: d8f0b2c4e6a7
Revises: c6e8a0b2d4f5
Create Date: 2026-07-27 12:30:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = 'd8f0b2c4e6a7'
down_revision: str | Sequence[str] | None = 'c6e8a0b2d4f5'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('invoice', sa.Column('org_id', sa.Uuid(), nullable=True))
    op.add_column('invoice', sa.Column('bill_to_name', sa.Text(), nullable=True))
    op.add_column('invoice', sa.Column('bill_to_email', sa.Text(), nullable=True))
    op.add_column('invoice', sa.Column('bill_to_phone', sa.Text(), nullable=True))
    op.add_column('invoice', sa.Column('bill_to_address', sa.Text(), nullable=True))
    # Backfill org_id from each invoice's client, then lock it down.
    op.execute("UPDATE invoice i SET org_id = c.org_id FROM client c WHERE c.id = i.client_id")
    op.alter_column('invoice', 'org_id', existing_type=sa.Uuid(), nullable=False)
    op.create_index('ix_invoice_org_id', 'invoice', ['org_id'])
    op.create_foreign_key(
        'fk_invoice_org', 'invoice', 'organisation', ['org_id'], ['id'], ondelete='RESTRICT'
    )
    op.alter_column('invoice', 'client_id', existing_type=sa.Uuid(), nullable=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DELETE FROM invoice WHERE client_id IS NULL")
    op.alter_column('invoice', 'client_id', existing_type=sa.Uuid(), nullable=False)
    op.drop_constraint('fk_invoice_org', 'invoice', type_='foreignkey')
    op.drop_index('ix_invoice_org_id', table_name='invoice')
    for col in ('bill_to_address', 'bill_to_phone', 'bill_to_email', 'bill_to_name', 'org_id'):
        op.drop_column('invoice', col)
