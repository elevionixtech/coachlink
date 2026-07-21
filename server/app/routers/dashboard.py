from datetime import date, timedelta
from decimal import Decimal

import sqlalchemy as sa
from fastapi import APIRouter

from app.deps import OrgUser, SessionDep
from app.models import (
    Batch,
    BatchStatus,
    Client,
    Enrollment,
    Invoice,
    InvoiceStatus,
    LifecycleStage,
)
from app.routers.batches import enrolled_counts
from app.routers.common import not_archived
from app.routers.enrollments import enrollment_out
from app.schemas import DashboardBatch, DashboardOut

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard")
async def dashboard(ctx: OrgUser, session: SessionDep) -> DashboardOut:
    org_id = ctx.org.id
    today = date.today()

    active_clients = await session.scalar(
        sa.select(sa.func.count()).where(
            Client.org_id == org_id,
            not_archived(Client),
            Client.lifecycle_stage == LifecycleStage.customer,
        )
    )
    active_batches = await session.scalar(
        sa.select(sa.func.count()).where(
            Batch.org_id == org_id, not_archived(Batch), Batch.status == BatchStatus.active
        )
    )
    month_start = today.replace(day=1)
    billed_this_month = await session.scalar(
        sa.select(sa.func.coalesce(sa.func.sum(Invoice.amount), 0))
        .join(Client, Invoice.client_id == Client.id)
        .where(
            Client.org_id == org_id,
            Invoice.status != InvoiceStatus.void,
            Invoice.issue_date >= month_start,
            Invoice.issue_date <= today,
        )
    )
    overdue_cutoff = today - timedelta(days=ctx.org.invoice_grace_days)
    overdue_count = await session.scalar(
        sa.select(sa.func.count())
        .select_from(Invoice)
        .join(Client, Invoice.client_id == Client.id)
        .where(
            Client.org_id == org_id,
            Invoice.status == InvoiceStatus.due,
            Invoice.issue_date < overdue_cutoff,
        )
    )

    todays = (
        (
            await session.scalars(
                sa.select(Batch)
                .where(
                    Batch.org_id == org_id,
                    not_archived(Batch),
                    Batch.status == BatchStatus.active,
                    sa.or_(Batch.start_date.is_(None), Batch.start_date <= today),
                    sa.or_(Batch.end_date.is_(None), Batch.end_date >= today),
                )
                .order_by(Batch.start_time.asc().nulls_last())
            )
        )
        .unique()
        .all()
    )
    counts = await enrolled_counts(session, [b.id for b in todays])

    recent = (
        (
            await session.scalars(
                sa.select(Enrollment)
                .join(Client, Enrollment.client_id == Client.id)
                .where(Client.org_id == org_id)
                .order_by(Enrollment.created_at.desc())
                .limit(5)
            )
        )
        .unique()
        .all()
    )

    return DashboardOut(
        active_clients=active_clients or 0,
        active_batches=active_batches or 0,
        billed_this_month=Decimal(billed_this_month or 0),
        overdue_count=overdue_count or 0,
        todays_batches=[
            DashboardBatch(
                id=b.id,
                name=b.name,
                code=b.code,
                start_time=b.start_time,
                end_time=b.end_time,
                instructor_name=b.instructor.name if b.instructor else None,
                location_name=b.location.name if b.location else None,
                enrolled_count=counts.get(b.id, 0),
                capacity=b.location.capacity_per_batch if b.location else None,
            )
            for b in todays
        ],
        recent_enrollments=[enrollment_out(e) for e in recent],
    )
