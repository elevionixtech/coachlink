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
    InvoiceDocumentOut,
    InvoiceOut,
    InvoicePage,
    InvoiceParty,
    InvoicePatch,
)

router = APIRouter(prefix="/invoices", tags=["invoices"])


async def latest_period_starts(
    session: SessionDep, subscription_ids: list[uuid.UUID]
) -> dict[uuid.UUID, date]:
    """Newest live period start per subscription — only that invoice may be adjusted."""
    if not subscription_ids:
        return {}
    rows = await session.execute(
        sa.select(Invoice.subscription_id, sa.func.max(Invoice.period_start))
        .where(
            Invoice.subscription_id.in_(subscription_ids),
            Invoice.status != InvoiceStatus.void,
        )
        .group_by(Invoice.subscription_id)
    )
    return {sub_id: start for sub_id, start in rows.all()}


def invoice_out(
    invoice: Invoice, grace_days: int, latest_starts: dict[uuid.UUID, date] | None = None
) -> InvoiceOut:
    out = InvoiceOut.model_validate(invoice)
    out.client_name = invoice.client.name if invoice.client else None
    out.service_name = (
        invoice.subscription.service.name
        if invoice.subscription and invoice.subscription.service
        else None
    )
    out.overdue = is_overdue(invoice, grace_days)
    # Mirrors the PATCH guards, so the UI never offers an action the API would refuse.
    out.can_adjust_period = invoice.status is not InvoiceStatus.void and (
        latest_starts is not None
        and latest_starts.get(invoice.subscription_id) == invoice.period_start
    )
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

    latest = await latest_period_starts(session, [i.subscription_id for i in rows[:limit]])

    outstanding = await session.scalar(
        sa.select(sa.func.coalesce(sa.func.sum(Invoice.amount), 0))
        .join(Client, Invoice.client_id == Client.id)
        .where(Client.org_id == ctx.org.id, Invoice.status == InvoiceStatus.due)
    )

    return InvoicePage(
        items=[invoice_out(i, grace, latest) for i in rows[:limit]],
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

    if body.period_end is not None:
        # The period moves in either direction: out, when a client pauses and the
        # extension is goodwill against money already taken; in, when a usage-based
        # plan's deliverables are all delivered and the period can close early. Paid
        # invoices qualify for both — the amount never changes, so nothing about the
        # payment is invalidated. A voided invoice bills nothing, so there is no
        # period to adjust.
        if invoice.status is InvoiceStatus.void:
            raise HTTPException(
                422, detail="A voided invoice bills nothing — its period cannot be adjusted"
            )
        if body.period_end < invoice.period_start:
            raise HTTPException(
                422, detail="The period cannot end before it starts"
            )
        # Only the newest period can move. Stretching an earlier one would overlap
        # invoices already issued for the periods that follow it (§3.8).
        latest = await latest_period_starts(session, [invoice.subscription_id])
        if invoice.period_start != latest.get(invoice.subscription_id):
            raise HTTPException(
                422,
                detail=(
                    "Only the latest invoice for a subscription can be adjusted — "
                    "changing an earlier one would overlap invoices already issued"
                ),
            )
        # Every later period shifts with it, in whichever direction (§3.8).
        invoice.period_end = body.period_end
        invoice.period_end_adjusted = True

    if body.status is not None:
        invoice.status = body.status

    await session.commit()
    latest = await latest_period_starts(session, [invoice.subscription_id])
    return invoice_out(invoice, ctx.org.invoice_grace_days, latest)


@router.get("/{invoice_id}")
async def get_invoice_document(
    invoice_id: uuid.UUID, ctx: OrgUser, session: SessionDep
) -> InvoiceDocumentOut:
    """The full invoice as a document — issuer, bill-to, and what the period covers.

    One request so the printable view renders in a single pass, which matters when the
    browser's print dialog snapshots the page.
    """
    invoice = await session.get(Invoice, invoice_id)
    if invoice is None or invoice.client.org_id != ctx.org.id:
        raise HTTPException(404, detail="Invoice not found")

    latest = await latest_period_starts(session, [invoice.subscription_id])
    base = invoice_out(invoice, ctx.org.invoice_grace_days, latest)

    client = invoice.client
    sub = invoice.subscription
    service = sub.service if sub else None

    return InvoiceDocumentOut(
        **base.model_dump(),
        currency=ctx.org.currency,
        billing_interval=service.billing_interval if service else None,
        service_description=service.description if service else None,
        pricing_option_name=(
            sub.pricing_option.name if sub and sub.pricing_option else None
        ),
        issued_by=InvoiceParty(
            name=ctx.org.name,
            address=ctx.org.address,
            email=ctx.org.billing_email,
            phone=ctx.org.phone,
            gstin=ctx.org.gstin,
        ),
        bill_to=InvoiceParty(
            name=client.name,
            company_name=client.company_name,
            address=client.address,
            email=client.email,
            phone=client.phone,
            gstin=client.gstin,
        ),
        includes=[
            f"{d.quantity} {d.unit} — {d.name}"
            for d in (service.deliverables if service else [])
        ],
    )
