import uuid
from datetime import UTC, datetime

import sqlalchemy as sa
from fastapi import APIRouter, HTTPException

from app.billing import effective_rate
from app.deps import OrgUser, SessionDep
from app.models import (
    PricingMode,
    PricingOption,
    Service,
    ServiceDeliverable,
    ServicePricingOption,
)
from app.routers.common import (
    PAGE_LIMIT_DEFAULT,
    clamp_limit,
    get_owned_or_404,
    next_cursor,
    not_archived,
)
from app.schemas import Page, ServiceIn, ServiceOut, ServicePatch

router = APIRouter(prefix="/services", tags=["services"])


async def _check_options_owned(
    session: SessionDep, org_id: uuid.UUID, rows: list[dict]
) -> None:
    """Every referenced option must belong to the caller's org — a foreign id is a
    404, never a 403 (§5.6)."""
    for row in rows:
        await get_owned_or_404(session, PricingOption, row["pricing_option_id"], org_id)


def service_out(service: Service) -> ServiceOut:
    out = ServiceOut.model_validate(service)
    by_id = {p.pricing_option_id: p for p in service.pricing_options}
    for priced in out.pricing_options:
        spo = by_id[priced.pricing_option_id]
        priced.option_name = spo.option.name if spo.option else None
        priced.effective_rate = (
            spo.value
            if spo.pricing_mode is PricingMode.fixed_rate
            else effective_rate(service.rate, spo.value)
        )
    return out


async def _check_sku_free(
    session: SessionDep, org_id: uuid.UUID, sku: str, exclude_id: uuid.UUID | None = None
) -> None:
    stmt = sa.select(Service.id).where(Service.org_id == org_id, Service.sku == sku)
    if exclude_id:
        stmt = stmt.where(Service.id != exclude_id)
    if await session.scalar(stmt):
        raise HTTPException(409, detail=f"SKU '{sku}' already exists in this organisation")


@router.get("")
async def list_services(
    ctx: OrgUser,
    session: SessionDep,
    q: str | None = None,
    cursor: int = 0,
    limit: int = PAGE_LIMIT_DEFAULT,
) -> Page[ServiceOut]:
    limit = clamp_limit(limit)
    stmt = (
        sa.select(Service)
        .where(Service.org_id == ctx.org.id, not_archived(Service))
        .order_by(Service.created_at.desc(), Service.id)
        .offset(cursor)
        .limit(limit + 1)
    )
    if q:
        pattern = f"%{q}%"
        stmt = stmt.where(sa.or_(Service.name.ilike(pattern), Service.sku.ilike(pattern)))
    rows = (await session.scalars(stmt)).unique().all()
    return Page(
        items=[service_out(s) for s in rows[:limit]],
        next_cursor=next_cursor(cursor, limit, len(rows)),
    )


@router.post("", status_code=201)
async def create_service(body: ServiceIn, ctx: OrgUser, session: SessionDep) -> ServiceOut:
    await _check_sku_free(session, ctx.org.id, body.sku)
    priced = [p.model_dump() for p in body.pricing_options]
    await _check_options_owned(session, ctx.org.id, priced)
    service = Service(
        org_id=ctx.org.id,
        **body.model_dump(exclude={"deliverables", "pricing_options"}),
        deliverables=[ServiceDeliverable(**d.model_dump()) for d in body.deliverables],
        pricing_options=[ServicePricingOption(**p) for p in priced],
    )
    session.add(service)
    await session.commit()
    await session.refresh(service)
    return service_out(service)


@router.get("/{service_id}")
async def get_service(service_id: uuid.UUID, ctx: OrgUser, session: SessionDep) -> ServiceOut:
    service = await get_owned_or_404(session, Service, service_id, ctx.org.id)
    return service_out(service)


@router.patch("/{service_id}")
async def update_service(
    service_id: uuid.UUID, body: ServicePatch, ctx: OrgUser, session: SessionDep
) -> ServiceOut:
    service = await get_owned_or_404(session, Service, service_id, ctx.org.id)
    data = body.model_dump(exclude_unset=True)
    deliverables = data.pop("deliverables", None)
    priced = data.pop("pricing_options", None)
    if "sku" in data and data["sku"] != service.sku:
        await _check_sku_free(session, ctx.org.id, data["sku"], exclude_id=service.id)
    for key, value in data.items():
        setattr(service, key, value)
    if deliverables is not None:
        service.deliverables = [ServiceDeliverable(**d) for d in deliverables]
    if priced is not None:
        await _check_options_owned(session, ctx.org.id, priced)
        # Replacing the collection wholesale would INSERT the new rows before DELETEing
        # the old ones in the same flush, colliding with the (service_id,
        # pricing_option_id) unique constraint whenever an option is re-priced.
        # Deliverables get away with the same pattern only because they have no such
        # constraint. Flush the removals first so the slots are free.
        service.pricing_options = []
        await session.flush()
        service.pricing_options = [ServicePricingOption(**p) for p in priced]
    await session.commit()
    await session.refresh(service)
    return service_out(service)


@router.delete("/{service_id}", status_code=204)
async def archive_service(service_id: uuid.UUID, ctx: OrgUser, session: SessionDep) -> None:
    service = await get_owned_or_404(session, Service, service_id, ctx.org.id)
    service.archived_at = datetime.now(UTC)
    await session.commit()
