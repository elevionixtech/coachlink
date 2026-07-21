import uuid
from datetime import UTC, datetime

import sqlalchemy as sa
from fastapi import APIRouter, HTTPException

from app.deps import OrgUser, SessionDep
from app.models import Service, ServiceDeliverable
from app.routers.common import (
    PAGE_LIMIT_DEFAULT,
    clamp_limit,
    get_owned_or_404,
    next_cursor,
    not_archived,
)
from app.schemas import Page, ServiceIn, ServiceOut, ServicePatch

router = APIRouter(prefix="/services", tags=["services"])


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
        items=[ServiceOut.model_validate(s) for s in rows[:limit]],
        next_cursor=next_cursor(cursor, limit, len(rows)),
    )


@router.post("", status_code=201)
async def create_service(body: ServiceIn, ctx: OrgUser, session: SessionDep) -> ServiceOut:
    await _check_sku_free(session, ctx.org.id, body.sku)
    service = Service(
        org_id=ctx.org.id,
        **body.model_dump(exclude={"deliverables"}),
        deliverables=[ServiceDeliverable(**d.model_dump()) for d in body.deliverables],
    )
    session.add(service)
    await session.commit()
    return ServiceOut.model_validate(service)


@router.get("/{service_id}")
async def get_service(service_id: uuid.UUID, ctx: OrgUser, session: SessionDep) -> ServiceOut:
    service = await get_owned_or_404(session, Service, service_id, ctx.org.id)
    return ServiceOut.model_validate(service)


@router.patch("/{service_id}")
async def update_service(
    service_id: uuid.UUID, body: ServicePatch, ctx: OrgUser, session: SessionDep
) -> ServiceOut:
    service = await get_owned_or_404(session, Service, service_id, ctx.org.id)
    data = body.model_dump(exclude_unset=True)
    deliverables = data.pop("deliverables", None)
    if "sku" in data and data["sku"] != service.sku:
        await _check_sku_free(session, ctx.org.id, data["sku"], exclude_id=service.id)
    for key, value in data.items():
        setattr(service, key, value)
    if deliverables is not None:
        service.deliverables = [ServiceDeliverable(**d) for d in deliverables]
    await session.commit()
    return ServiceOut.model_validate(service)


@router.delete("/{service_id}", status_code=204)
async def archive_service(service_id: uuid.UUID, ctx: OrgUser, session: SessionDep) -> None:
    service = await get_owned_or_404(session, Service, service_id, ctx.org.id)
    service.archived_at = datetime.now(UTC)
    await session.commit()
