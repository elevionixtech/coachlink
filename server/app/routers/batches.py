import uuid
from datetime import UTC, datetime

import sqlalchemy as sa
from fastapi import APIRouter, HTTPException

from app.deps import OrgUser, SessionDep
from app.models import Batch, Enrollment, Instructor, Location
from app.routers.common import (
    PAGE_LIMIT_DEFAULT,
    clamp_limit,
    get_owned_or_404,
    next_cursor,
    not_archived,
)
from app.schemas import BatchIn, BatchOut, BatchPatch, EnrollmentOut, Page

router = APIRouter(prefix="/batches", tags=["batches"])


async def _check_code_free(
    session: SessionDep, org_id: uuid.UUID, code: str, exclude_id: uuid.UUID | None = None
) -> None:
    stmt = sa.select(Batch.id).where(Batch.org_id == org_id, Batch.code == code)
    if exclude_id:
        stmt = stmt.where(Batch.id != exclude_id)
    if await session.scalar(stmt):
        raise HTTPException(409, detail=f"Batch code '{code}' already exists")


def _validate_windows(body: BatchIn | BatchPatch, existing: Batch | None = None) -> None:
    start_date = (
        body.start_date
        if body.start_date is not None
        else getattr(existing, "start_date", None)
    )
    end_date = (
        body.end_date if body.end_date is not None else getattr(existing, "end_date", None)
    )
    start_time = (
        body.start_time
        if body.start_time is not None
        else getattr(existing, "start_time", None)
    )
    end_time = (
        body.end_time if body.end_time is not None else getattr(existing, "end_time", None)
    )
    if start_date and end_date and end_date < start_date:
        raise HTTPException(422, detail="end_date must be on or after start_date")
    if start_time and end_time and end_time <= start_time:
        raise HTTPException(422, detail="end_time must be after start_time")


async def enrolled_counts(
    session: SessionDep, batch_ids: list[uuid.UUID]
) -> dict[uuid.UUID, int]:
    if not batch_ids:
        return {}
    rows = await session.execute(
        sa.select(Enrollment.batch_id, sa.func.count())
        .where(Enrollment.batch_id.in_(batch_ids))
        .group_by(Enrollment.batch_id)
    )
    return dict(rows.all())


def batch_out(batch: Batch, enrolled: int = 0) -> BatchOut:
    out = BatchOut.model_validate(batch)
    out.location_name = batch.location.name if batch.location else None
    out.instructor_name = batch.instructor.name if batch.instructor else None
    out.enrolled_count = enrolled
    # A batch's capacity is its location's capacity_per_batch (§5.5).
    out.capacity = batch.location.capacity_per_batch if batch.location else None
    return out


@router.get("")
async def list_batches(
    ctx: OrgUser,
    session: SessionDep,
    q: str | None = None,
    cursor: int = 0,
    limit: int = PAGE_LIMIT_DEFAULT,
) -> Page[BatchOut]:
    limit = clamp_limit(limit)
    stmt = (
        sa.select(Batch)
        .where(Batch.org_id == ctx.org.id, not_archived(Batch))
        .order_by(Batch.created_at.desc(), Batch.id)
        .offset(cursor)
        .limit(limit + 1)
    )
    if q:
        pattern = f"%{q}%"
        stmt = stmt.where(sa.or_(Batch.name.ilike(pattern), Batch.code.ilike(pattern)))
    rows = (await session.scalars(stmt)).unique().all()
    counts = await enrolled_counts(session, [b.id for b in rows])
    return Page(
        items=[batch_out(b, counts.get(b.id, 0)) for b in rows[:limit]],
        next_cursor=next_cursor(cursor, limit, len(rows)),
    )


@router.post("", status_code=201)
async def create_batch(body: BatchIn, ctx: OrgUser, session: SessionDep) -> BatchOut:
    await _check_code_free(session, ctx.org.id, body.code)
    # FK ids arriving in the body are verified to belong to the caller's org (§5.6).
    await get_owned_or_404(session, Location, body.location_id, ctx.org.id)
    await get_owned_or_404(session, Instructor, body.instructor_id, ctx.org.id)
    _validate_windows(body)
    batch = Batch(org_id=ctx.org.id, **body.model_dump())
    session.add(batch)
    await session.commit()
    await session.refresh(batch)
    return batch_out(batch)


@router.get("/{batch_id}")
async def get_batch(batch_id: uuid.UUID, ctx: OrgUser, session: SessionDep) -> BatchOut:
    batch = await get_owned_or_404(session, Batch, batch_id, ctx.org.id)
    counts = await enrolled_counts(session, [batch.id])
    return batch_out(batch, counts.get(batch.id, 0))


@router.get("/{batch_id}/roster")
async def batch_roster(
    batch_id: uuid.UUID, ctx: OrgUser, session: SessionDep
) -> list[EnrollmentOut]:
    batch = await get_owned_or_404(session, Batch, batch_id, ctx.org.id)
    enrollments = (
        await session.scalars(
            sa.select(Enrollment)
            .where(Enrollment.batch_id == batch.id)
            .order_by(Enrollment.created_at.desc())
        )
    ).all()
    return [
        EnrollmentOut(
            id=e.id,
            client_id=e.client_id,
            batch_id=e.batch_id,
            client_name=e.client.name,
            batch_name=batch.name,
            batch_code=batch.code,
            start_date=e.start_date,
            created_at=e.created_at,
        )
        for e in enrollments
    ]


@router.patch("/{batch_id}")
async def update_batch(
    batch_id: uuid.UUID, body: BatchPatch, ctx: OrgUser, session: SessionDep
) -> BatchOut:
    batch = await get_owned_or_404(session, Batch, batch_id, ctx.org.id)
    data = body.model_dump(exclude_unset=True)
    if "code" in data and data["code"] != batch.code:
        await _check_code_free(session, ctx.org.id, data["code"], exclude_id=batch.id)
    if "location_id" in data:
        await get_owned_or_404(session, Location, data["location_id"], ctx.org.id)
    if "instructor_id" in data:
        await get_owned_or_404(session, Instructor, data["instructor_id"], ctx.org.id)
    _validate_windows(body, batch)
    for key, value in data.items():
        setattr(batch, key, value)
    await session.commit()
    await session.refresh(batch)
    counts = await enrolled_counts(session, [batch.id])
    return batch_out(batch, counts.get(batch.id, 0))


@router.delete("/{batch_id}", status_code=204)
async def archive_batch(batch_id: uuid.UUID, ctx: OrgUser, session: SessionDep) -> None:
    batch = await get_owned_or_404(session, Batch, batch_id, ctx.org.id)
    batch.archived_at = datetime.now(UTC)
    await session.commit()
