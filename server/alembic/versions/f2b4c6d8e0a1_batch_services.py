"""batch services

A batch delivers a set of services (§5.5); enrolment then requires the client to hold an
active subscription to one of them. Join table batch_service; both sides are org-scoped
through their parents.

Revision ID: f2b4c6d8e0a1
Revises: e1a2b3c4d5e6
Create Date: 2026-07-26 11:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = 'f2b4c6d8e0a1'
down_revision: str | Sequence[str] | None = 'e1a2b3c4d5e6'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'batch_service',
        sa.Column('batch_id', sa.Uuid(), nullable=False),
        sa.Column('service_id', sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(['batch_id'], ['batch.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['service_id'], ['service.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('batch_id', 'service_id'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('batch_service')
