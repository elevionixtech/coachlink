import uuid
from datetime import UTC, datetime

import sqlalchemy as sa
from fastapi import APIRouter, HTTPException

from app.deps import OrgUser, SessionDep
from app.models import Location
from app.routers.common import (
    PAGE_LIMIT_DEFAULT,
    clamp_limit,
    get_owned_or_404,
    next_cursor,
    not_archived,
)
from app.schemas import LocationIn, LocationOut, LocationPatch, Page

router = APIRouter(prefix="/locations", tags=["locations"])


async def _check_code_free(
    session: SessionDep, org_id: uuid.UUID, code: str, exclude_id: uuid.UUID | None = None
) -> None:
    stmt = sa.select(Location.id).where(Location.org_id == org_id, Location.code == code)
    if exclude_id:
        stmt = stmt.where(Location.id != exclude_id)
    if await session.scalar(stmt):
        raise HTTPException(409, detail=f"Location code '{code}' already exists")


@router.get("")
async def list_locations(
    ctx: OrgUser,
    session: SessionDep,
    q: str | None = None,
    cursor: int = 0,
    limit: int = PAGE_LIMIT_DEFAULT,
) -> Page[LocationOut]:
    limit = clamp_limit(limit)
    stmt = (
        sa.select(Location)
        .where(Location.org_id == ctx.org.id, not_archived(Location))
        .order_by(Location.created_at.desc(), Location.id)
        .offset(cursor)
        .limit(limit + 1)
    )
    if q:
        pattern = f"%{q}%"
        stmt = stmt.where(sa.or_(Location.name.ilike(pattern), Location.code.ilike(pattern)))
    rows = (await session.scalars(stmt)).all()
    return Page(
        items=[LocationOut.model_validate(loc) for loc in rows[:limit]],
        next_cursor=next_cursor(cursor, limit, len(rows)),
    )


@router.post("", status_code=201)
async def create_location(body: LocationIn, ctx: OrgUser, session: SessionDep) -> LocationOut:
    await _check_code_free(session, ctx.org.id, body.code)
    location = Location(org_id=ctx.org.id, **body.model_dump())
    session.add(location)
    await session.commit()
    return LocationOut.model_validate(location)


@router.get("/{location_id}")
async def get_location(
    location_id: uuid.UUID, ctx: OrgUser, session: SessionDep
) -> LocationOut:
    location = await get_owned_or_404(session, Location, location_id, ctx.org.id)
    return LocationOut.model_validate(location)


@router.patch("/{location_id}")
async def update_location(
    location_id: uuid.UUID, body: LocationPatch, ctx: OrgUser, session: SessionDep
) -> LocationOut:
    location = await get_owned_or_404(session, Location, location_id, ctx.org.id)
    data = body.model_dump(exclude_unset=True)
    if "code" in data and data["code"] != location.code:
        await _check_code_free(session, ctx.org.id, data["code"], exclude_id=location.id)
    for key, value in data.items():
        setattr(location, key, value)
    await session.commit()
    return LocationOut.model_validate(location)


@router.delete("/{location_id}", status_code=204)
async def archive_location(location_id: uuid.UUID, ctx: OrgUser, session: SessionDep) -> None:
    location = await get_owned_or_404(session, Location, location_id, ctx.org.id)
    location.archived_at = datetime.now(UTC)
    await session.commit()
