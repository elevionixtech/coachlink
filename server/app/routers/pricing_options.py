"""The org's pricing-option catalog (§3.7) — an open-ended list of tiers
("Corporate Plan", "Family Plan", "Student", ...) that services price individually."""

import uuid
from datetime import UTC, datetime

import sqlalchemy as sa
from fastapi import APIRouter, HTTPException

from app.deps import OrgUser, SessionDep
from app.models import PricingOption, ServicePricingOption, Subscription
from app.routers.common import get_owned_or_404, not_archived
from app.schemas import PricingOptionIn, PricingOptionOut, PricingOptionPatch

router = APIRouter(prefix="/pricing-options", tags=["pricing-options"])


async def _check_name_free(
    session: SessionDep, org_id: uuid.UUID, name: str, exclude_id: uuid.UUID | None = None
) -> None:
    """Names are unique per org — return a 409 with a message, not a bare IntegrityError."""
    stmt = sa.select(PricingOption.id).where(
        PricingOption.org_id == org_id, sa.func.lower(PricingOption.name) == name.lower()
    )
    if exclude_id:
        stmt = stmt.where(PricingOption.id != exclude_id)
    if await session.scalar(stmt):
        raise HTTPException(409, detail=f"Pricing option '{name}' already exists")


@router.get("")
async def list_pricing_options(ctx: OrgUser, session: SessionDep) -> list[PricingOptionOut]:
    rows = (
        await session.scalars(
            sa.select(PricingOption)
            .where(PricingOption.org_id == ctx.org.id, not_archived(PricingOption))
            .order_by(PricingOption.sort_order, PricingOption.name)
        )
    ).all()
    return [PricingOptionOut.model_validate(r) for r in rows]


@router.post("", status_code=201)
async def create_pricing_option(
    body: PricingOptionIn, ctx: OrgUser, session: SessionDep
) -> PricingOptionOut:
    await _check_name_free(session, ctx.org.id, body.name)
    option = PricingOption(org_id=ctx.org.id, **body.model_dump())
    session.add(option)
    await session.commit()
    return PricingOptionOut.model_validate(option)


@router.get("/{option_id}")
async def get_pricing_option(
    option_id: uuid.UUID, ctx: OrgUser, session: SessionDep
) -> PricingOptionOut:
    option = await get_owned_or_404(session, PricingOption, option_id, ctx.org.id)
    return PricingOptionOut.model_validate(option)


@router.patch("/{option_id}")
async def update_pricing_option(
    option_id: uuid.UUID, body: PricingOptionPatch, ctx: OrgUser, session: SessionDep
) -> PricingOptionOut:
    option = await get_owned_or_404(session, PricingOption, option_id, ctx.org.id)
    data = body.model_dump(exclude_unset=True)
    if "name" in data and data["name"].lower() != option.name.lower():
        await _check_name_free(session, ctx.org.id, data["name"], exclude_id=option.id)
    for key, value in data.items():
        setattr(option, key, value)
    await session.commit()
    return PricingOptionOut.model_validate(option)


@router.delete("/{option_id}", status_code=204)
async def archive_pricing_option(
    option_id: uuid.UUID, ctx: OrgUser, session: SessionDep
) -> None:
    """Soft-delete, and only once nothing references it.

    The FK is RESTRICT, so the database would reject this anyway — checking first
    turns an opaque IntegrityError into a message naming what still uses the option.
    """
    option = await get_owned_or_404(session, PricingOption, option_id, ctx.org.id)

    priced = await session.scalar(
        sa.select(sa.func.count())
        .select_from(ServicePricingOption)
        .where(ServicePricingOption.pricing_option_id == option.id)
    )
    if priced:
        raise HTTPException(
            409, detail=f"{priced} service(s) still price this option — remove those first"
        )
    subscribed = await session.scalar(
        sa.select(sa.func.count())
        .select_from(Subscription)
        .where(Subscription.pricing_option_id == option.id)
    )
    if subscribed:
        raise HTTPException(
            409, detail=f"{subscribed} subscription(s) are still on this option"
        )

    option.archived_at = datetime.now(UTC)
    await session.commit()
