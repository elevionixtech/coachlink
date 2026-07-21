import sqlalchemy as sa
from fastapi import APIRouter, HTTPException

from app.deps import OrgUser, SessionDep
from app.models import Batch, CapacityPolicy, Client, Enrollment
from app.routers.common import (
    PAGE_LIMIT_DEFAULT,
    clamp_limit,
    get_owned_or_404,
    next_cursor,
)
from app.schemas import EnrollmentIn, EnrollmentOut, Page

router = APIRouter(prefix="/enrollments", tags=["enrollments"])


def enrollment_out(e: Enrollment, capacity_warning: str | None = None) -> EnrollmentOut:
    return EnrollmentOut(
        id=e.id,
        client_id=e.client_id,
        batch_id=e.batch_id,
        client_name=e.client.name if e.client else None,
        batch_name=e.batch.name if e.batch else None,
        batch_code=e.batch.code if e.batch else None,
        start_date=e.start_date,
        capacity_warning=capacity_warning,
        created_at=e.created_at,
    )


@router.get("")
async def list_enrollments(
    ctx: OrgUser,
    session: SessionDep,
    cursor: int = 0,
    limit: int = PAGE_LIMIT_DEFAULT,
) -> Page[EnrollmentOut]:
    limit = clamp_limit(limit)
    stmt = (
        sa.select(Enrollment)
        .join(Client, Enrollment.client_id == Client.id)
        .where(Client.org_id == ctx.org.id)
        .order_by(Enrollment.created_at.desc(), Enrollment.id)
        .offset(cursor)
        .limit(limit + 1)
    )
    rows = (await session.scalars(stmt)).unique().all()
    return Page(
        items=[enrollment_out(e) for e in rows[:limit]],
        next_cursor=next_cursor(cursor, limit, len(rows)),
    )


@router.post("", status_code=201)
async def create_enrollment(
    body: EnrollmentIn, ctx: OrgUser, session: SessionDep
) -> EnrollmentOut:
    await get_owned_or_404(session, Client, body.client_id, ctx.org.id)
    batch = await get_owned_or_404(session, Batch, body.batch_id, ctx.org.id)

    duplicate = await session.scalar(
        sa.select(Enrollment.id).where(
            Enrollment.batch_id == body.batch_id, Enrollment.client_id == body.client_id
        )
    )
    if duplicate:
        raise HTTPException(409, detail="Client is already enrolled in this batch")

    # Capacity comes from the batch's location; behavior follows the org policy (§5.5).
    capacity = batch.location.capacity_per_batch if batch.location else None
    capacity_warning: str | None = None
    if capacity is not None:
        enrolled = (
            await session.scalar(
                sa.select(sa.func.count()).where(Enrollment.batch_id == batch.id)
            )
            or 0
        )
        if enrolled >= capacity:
            if ctx.org.capacity_policy == CapacityPolicy.block:
                raise HTTPException(409, detail=f"Batch is at capacity ({enrolled}/{capacity})")
            capacity_warning = f"Batch is over capacity ({enrolled + 1}/{capacity})"

    enrollment = Enrollment(**body.model_dump())
    session.add(enrollment)
    await session.commit()
    await session.refresh(enrollment)
    return enrollment_out(enrollment, capacity_warning)
