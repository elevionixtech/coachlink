import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

import sqlalchemy as sa
from fastapi import APIRouter

from app.deps import OrgUser, SessionDep
from app.models import Batch, Instructor
from app.routers.common import (
    PAGE_LIMIT_DEFAULT,
    clamp_limit,
    get_owned_or_404,
    next_cursor,
    not_archived,
)
from app.schemas import InstructorIn, InstructorOut, InstructorPatch, Page

router = APIRouter(prefix="/instructors", tags=["instructors"])


def instructor_out(instructor: Instructor, today: date | None = None) -> InstructorOut:
    """Age and current experience are derived, never stored (§3.3)."""
    today = today or date.today()
    out = InstructorOut.model_validate(instructor)
    if instructor.date_of_birth:
        dob = instructor.date_of_birth
        out.age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    if instructor.experience_at_joining is not None:
        extra = Decimal("0")
        if instructor.joining_date:
            extra = Decimal((today - instructor.joining_date).days) / Decimal(365)
        out.current_experience = (instructor.experience_at_joining + extra).quantize(
            Decimal("0.1")
        )
    return out


@router.get("")
async def list_instructors(
    ctx: OrgUser,
    session: SessionDep,
    q: str | None = None,
    cursor: int = 0,
    limit: int = PAGE_LIMIT_DEFAULT,
) -> Page[InstructorOut]:
    limit = clamp_limit(limit)
    stmt = (
        sa.select(Instructor)
        .where(Instructor.org_id == ctx.org.id, not_archived(Instructor))
        .order_by(Instructor.created_at.desc(), Instructor.id)
        .offset(cursor)
        .limit(limit + 1)
    )
    if q:
        stmt = stmt.where(Instructor.name.ilike(f"%{q}%"))
    rows = (await session.scalars(stmt)).all()
    return Page(
        items=[instructor_out(i) for i in rows[:limit]],
        next_cursor=next_cursor(cursor, limit, len(rows)),
    )


@router.post("", status_code=201)
async def create_instructor(
    body: InstructorIn, ctx: OrgUser, session: SessionDep
) -> InstructorOut:
    instructor = Instructor(org_id=ctx.org.id, **body.model_dump())
    session.add(instructor)
    await session.commit()
    return instructor_out(instructor)


@router.get("/{instructor_id}")
async def get_instructor(
    instructor_id: uuid.UUID, ctx: OrgUser, session: SessionDep
) -> InstructorOut:
    instructor = await get_owned_or_404(session, Instructor, instructor_id, ctx.org.id)
    return instructor_out(instructor)


@router.get("/{instructor_id}/batches")
async def batches_taught(
    instructor_id: uuid.UUID, ctx: OrgUser, session: SessionDep
) -> list[dict]:
    await get_owned_or_404(session, Instructor, instructor_id, ctx.org.id)
    batches = (
        await session.scalars(
            sa.select(Batch)
            .where(
                Batch.instructor_id == instructor_id,
                Batch.org_id == ctx.org.id,
                not_archived(Batch),
            )
            .order_by(Batch.start_date.desc().nulls_last())
        )
    ).all()
    return [
        {
            "id": str(b.id),
            "name": b.name,
            "code": b.code,
            "status": b.status.value,
            "start_date": b.start_date.isoformat() if b.start_date else None,
            "end_date": b.end_date.isoformat() if b.end_date else None,
            "location_name": b.location.name if b.location else None,
        }
        for b in batches
    ]


@router.patch("/{instructor_id}")
async def update_instructor(
    instructor_id: uuid.UUID, body: InstructorPatch, ctx: OrgUser, session: SessionDep
) -> InstructorOut:
    instructor = await get_owned_or_404(session, Instructor, instructor_id, ctx.org.id)
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(instructor, key, value)
    await session.commit()
    return instructor_out(instructor)


@router.delete("/{instructor_id}", status_code=204)
async def archive_instructor(
    instructor_id: uuid.UUID, ctx: OrgUser, session: SessionDep
) -> None:
    instructor = await get_owned_or_404(session, Instructor, instructor_id, ctx.org.id)
    instructor.archived_at = datetime.now(UTC)
    await session.commit()
