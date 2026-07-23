"""configurable pricing options

Replaces service.pricing_options (a JSON list of bare strings) with a per-org catalog
table and a per-service priced child table, plus subscription.pricing_option_id (§3.7).

The old strings carried no price, so nothing can be inferred: each converted row lands
as discount_pct/0, meaning "offered, at base rate". That preserves which options a
service offers without inventing numbers the org never entered.

Revision ID: 7c4e1a9d3b52
Revises: 2b022badd088
Create Date: 2026-07-22 20:41:00.000000

"""
import json
import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = '7c4e1a9d3b52'
down_revision: str | Sequence[str] | None = '2b022badd088'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Seeded for every org so the catalog is never empty on first open. applies_to mirrors
# the account types these tiers have always implied.
DEFAULT_OPTIONS = [
    ("Corporate Plan", ["Corporate"], 0),
    ("Family Plan", ["Family"], 1),
    ("Other", [], 2),
]

JSONVariant = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'pricing_option',
        sa.Column('name', sa.Text(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('applies_to', JSONVariant, nullable=False),
        sa.Column('sort_order', sa.Integer(), nullable=False),
        sa.Column('org_id', sa.Uuid(), nullable=False),
        sa.Column('archived_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['org_id'], ['organisation.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('org_id', 'name', name='pricing_option_name_per_org'),
    )
    op.create_index(op.f('ix_pricing_option_org_id'), 'pricing_option', ['org_id'])

    op.create_table(
        'service_pricing_option',
        sa.Column('service_id', sa.Uuid(), nullable=False),
        sa.Column('pricing_option_id', sa.Uuid(), nullable=False),
        sa.Column('pricing_mode',
                  sa.Enum('fixed_rate', 'discount_pct', name='pricing_mode',
                          native_enum=False, length=30),
                  nullable=False),
        sa.Column('value', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['service_id'], ['service.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['pricing_option_id'], ['pricing_option.id'],
                                ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('service_id', 'pricing_option_id',
                            name='service_pricing_option_once'),
    )
    op.create_index(op.f('ix_service_pricing_option_service_id'),
                    'service_pricing_option', ['service_id'])
    op.create_index(op.f('ix_service_pricing_option_pricing_option_id'),
                    'service_pricing_option', ['pricing_option_id'])

    op.add_column('subscription', sa.Column('pricing_option_id', sa.Uuid(), nullable=True))
    op.create_index(op.f('ix_subscription_pricing_option_id'),
                    'subscription', ['pricing_option_id'])
    op.create_foreign_key('fk_subscription_pricing_option', 'subscription', 'pricing_option',
                          ['pricing_option_id'], ['id'], ondelete='RESTRICT')

    _convert_existing_options()

    op.drop_column('service', 'pricing_options')


def _convert_existing_options() -> None:
    """Build the catalog from whatever strings the orgs are already using."""
    bind = op.get_bind()
    orgs = bind.execute(sa.text("SELECT id FROM organisation")).scalars().all()
    services = bind.execute(
        sa.text("SELECT id, org_id, pricing_options FROM service")
    ).mappings().all()

    used_by_org: dict[uuid.UUID, set[str]] = {org_id: set() for org_id in orgs}
    for svc in services:
        for name in svc["pricing_options"] or []:
            used_by_org.setdefault(svc["org_id"], set()).add(name)

    # name -> id, per org, so the service rows below can resolve their references.
    option_ids: dict[tuple[uuid.UUID, str], uuid.UUID] = {}
    for org_id in orgs:
        seeded = {name for name, _, _ in DEFAULT_OPTIONS}
        extras = sorted(used_by_org.get(org_id, set()) - seeded)
        rows = list(DEFAULT_OPTIONS) + [
            (name, [], i + len(DEFAULT_OPTIONS)) for i, name in enumerate(extras)
        ]
        for name, applies_to, sort_order in rows:
            new_id = uuid.uuid4()
            option_ids[(org_id, name)] = new_id
            bind.execute(
                sa.text(
                    "INSERT INTO pricing_option "
                    "(id, org_id, name, description, applies_to, sort_order,"
                    " created_at, updated_at) "
                    "VALUES (:id, :org_id, :name, NULL, CAST(:applies_to AS JSONB),"
                    " :sort_order, now(), now())"
                ),
                {
                    "id": new_id,
                    "org_id": org_id,
                    "name": name,
                    "applies_to": json.dumps(applies_to),
                    "sort_order": sort_order,
                },
            )

    for svc in services:
        for name in svc["pricing_options"] or []:
            option_id = option_ids.get((svc["org_id"], name))
            if option_id is None:  # defensive: an org-less service should not exist
                continue
            bind.execute(
                sa.text(
                    "INSERT INTO service_pricing_option "
                    "(id, service_id, pricing_option_id, pricing_mode, value,"
                    " created_at, updated_at) "
                    "VALUES (:id, :service_id, :option_id, 'discount_pct', 0,"
                    " now(), now())"
                ),
                {"id": uuid.uuid4(), "service_id": svc["id"], "option_id": option_id},
            )


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column('service', sa.Column('pricing_options', JSONVariant, nullable=True))
    bind = op.get_bind()
    # Rebuild the string list from the child rows so a round trip loses nothing but price.
    bind.execute(sa.text("""
        UPDATE service s SET pricing_options = COALESCE((
            SELECT jsonb_agg(po.name ORDER BY po.sort_order, po.name)
            FROM service_pricing_option spo
            JOIN pricing_option po ON po.id = spo.pricing_option_id
            WHERE spo.service_id = s.id
        ), '[]'::jsonb)
    """))
    op.alter_column('service', 'pricing_options', nullable=False)

    op.drop_constraint('fk_subscription_pricing_option', 'subscription', type_='foreignkey')
    op.drop_index(op.f('ix_subscription_pricing_option_id'), table_name='subscription')
    op.drop_column('subscription', 'pricing_option_id')
    op.drop_table('service_pricing_option')
    op.drop_index(op.f('ix_pricing_option_org_id'), table_name='pricing_option')
    op.drop_table('pricing_option')
