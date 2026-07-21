import uuid
from datetime import date, timedelta
from decimal import Decimal

import sqlalchemy as sa
from fastapi import APIRouter, HTTPException

from app.billing import generate_missing, is_overdue
from app.deps import OrgUser, SessionDep
from app.models import Client, Invoice, InvoiceStatus
from app.routers.common import PAGE_LIMIT_DEFAULT, clamp_limit, get_owned_or_404, next_cursor
from app.schemas import (
    GenerateMissingIn,
    GenerateMissingOut,
    InvoiceOut,
    InvoicePage,
    InvoicePatch,
)

router = APIRouter(prefix="/invoices", tags=["invoices"])


def invoice_out(invoice: Invoice, grace_days: int) -> InvoiceOut:
    out = InvoiceOut.model_validate(invoice)
    out.client_name = invoice.client.name if invoice.client else None
    out.service_name = (
        invoice.subscription.service.name
        if invoice.subscription and invoice.subscription.service
        else None
    )
    out.overdue = is_overdue(invoice, grace_days)
    return out


@router.get("")
async def list_invoices(
    ctx: OrgUser,
    session: SessionDep,
    status: str | None = None,
    client_id: uuid.UUID | None = None,
    q: str | None = None,
    cursor: int = 0,
    limit: int = PAGE_LIMIT_DEFAULT,
) -> InvoicePage:
    limit = clamp_limit(limit)
    base = (
        sa.select(Invoice)
        .join(Client, Invoice.client_id == Client.id)
        .where(Client.org_id == ctx.org.id)
    )
    if client_id is not None:
        base = base.where(Invoice.client_id == client_id)
    if q:
        pattern = f"%{q}%"
        base = base.where(sa.or_(Invoice.number.ilike(pattern), Client.name.ilike(pattern)))

    grace = ctx.org.invoice_grace_days
    if status == "overdue":
        # issue_date + grace < today  ⟺  issue_date < today - grace
        cutoff = date.today() - timedelta(days=grace)
        base = base.where(Invoice.status == InvoiceStatus.due, Invoice.issue_date < cutoff)
    elif status in {"due", "paid", "void"}:
        base = base.where(Invoice.status == InvoiceStatus(status))

    rows = (
        (
            await session.scalars(
                base.order_by(Invoice.issue_date.desc(), Invoice.created_at.desc())
                .offset(cursor)
                .limit(limit + 1)
            )
        )
        .unique()
        .all()
    )

    outstanding = await session.scalar(
        sa.select(sa.func.coalesce(sa.func.sum(Invoice.amount), 0))
        .join(Client, Invoice.client_id == Client.id)
        .where(Client.org_id == ctx.org.id, Invoice.status == InvoiceStatus.due)
    )

    return InvoicePage(
        items=[invoice_out(i, grace) for i in rows[:limit]],
        next_cursor=next_cursor(cursor, limit, len(rows)),
        outstanding_total=Decimal(outstanding or 0),
    )


@router.post("/generate-missing")
async def generate_missing_invoices(
    body: GenerateMissingIn, ctx: OrgUser, session: SessionDep
) -> GenerateMissingOut:
    if body.client_id is not None:
        await get_owned_or_404(session, Client, body.client_id, ctx.org.id)
    created = await generate_missing(session, ctx.org, body.client_id)
    await session.commit()
    return GenerateMissingOut(created=created)


@router.patch("/{invoice_id}")
async def update_invoice(
    invoice_id: uuid.UUID, body: InvoicePatch, ctx: OrgUser, session: SessionDep
) -> InvoiceOut:
    invoice = await session.get(Invoice, invoice_id)
    if invoice is None or invoice.client.org_id != ctx.org.id:
        raise HTTPException(404, detail="Invoice not found")
    invoice.status = body.status
    await session.commit()
    return invoice_out(invoice, ctx.org.invoice_grace_days)
