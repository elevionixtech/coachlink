import uuid
from datetime import date, timedelta
from decimal import Decimal

import sqlalchemy as sa
from fastapi import APIRouter, HTTPException

from app.billing import format_invoice_number, generate_missing, is_overdue
from app.deps import OrgUser, SessionDep
from app.models import Client, Invoice, InvoiceStatus, SubscriptionStatus
from app.routers.common import PAGE_LIMIT_DEFAULT, clamp_limit, get_owned_or_404, next_cursor
from app.schemas import (
    AdHocInvoiceIn,
    GenerateMissingIn,
    GenerateMissingOut,
    InvoiceDocumentOut,
    InvoiceOut,
    InvoicePage,
    InvoiceParty,
    InvoicePatch,
    PaymentInfo,
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
    out.client_name = invoice.client.name if invoice.client else invoice.bill_to_name
    out.service_name = (
        invoice.subscription.service.name
        if invoice.subscription and invoice.subscription.service
        else None
    )
    # An ad-hoc invoice has no service; its own description is the line shown instead.
    out.description = invoice.description
    out.overdue = is_overdue(invoice, grace_days)
    # Mirrors the PATCH guards, so the UI never offers an action the API would refuse.
    out.can_adjust_period = invoice.status is not InvoiceStatus.void and (
        latest_starts is not None
        and latest_starts.get(invoice.subscription_id) == invoice.period_start
    )
    # A difference can only be carried forward while the subscription still bills.
    out.can_carry_forward = bool(
        invoice.subscription
        and invoice.subscription.status is SubscriptionStatus.active
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
        .outerjoin(Client, Invoice.client_id == Client.id)
        .where(Invoice.org_id == ctx.org.id)
    )
    if client_id is not None:
        base = base.where(Invoice.client_id == client_id)
    if q:
        pattern = f"%{q}%"
        base = base.where(
            sa.or_(
                Invoice.number.ilike(pattern),
                Client.name.ilike(pattern),
                Invoice.bill_to_name.ilike(pattern),
            )
        )

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
        .where(Invoice.org_id == ctx.org.id, Invoice.status == InvoiceStatus.due)
    )

    return InvoicePage(
        items=[invoice_out(i, grace, latest) for i in rows[:limit]],
        next_cursor=next_cursor(cursor, limit, len(rows)),
        outstanding_total=Decimal(outstanding or 0),
    )


@router.post("", status_code=201)
async def create_invoice(
    body: AdHocInvoiceIn, ctx: OrgUser, session: SessionDep
) -> InvoiceOut:
    """Raise a one-off invoice against a client — amount and line entered by hand, with
    no subscription behind it (§3.8). Numbered from the org's invoice counter."""
    client = None
    if body.client_id is not None:
        client = await get_owned_or_404(session, Client, body.client_id, ctx.org.id)
    invoice = Invoice(
        number=format_invoice_number(
            ctx.org.invoice_prefix, body.issue_date.year, ctx.org.next_invoice_seq
        ),
        org_id=ctx.org.id,
        client_id=client.id if client else None,
        bill_to_name=None if client else body.bill_to_name,
        bill_to_email=None if client else body.bill_to_email,
        bill_to_phone=None if client else body.bill_to_phone,
        bill_to_address=None if client else body.bill_to_address,
        bill_to_gstin=None if client else body.bill_to_gstin,
        subscription_id=None,
        description=body.description,
        period_label="One-off",
        period_start=body.issue_date,
        period_end=body.issue_date,
        issue_date=body.issue_date,
        amount=body.amount,
        status=InvoiceStatus.due,
    )
    ctx.org.next_invoice_seq += 1
    session.add(invoice)
    await session.commit()
    await session.refresh(invoice)
    return invoice_out(invoice, ctx.org.invoice_grace_days)


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
    if invoice is None or invoice.org_id != ctx.org.id:
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

    if body.status is InvoiceStatus.paid:
        _record_payment(invoice, body)
    elif body.status is not None:
        invoice.status = body.status

    await session.commit()
    latest = await latest_period_starts(session, [invoice.subscription_id])
    return invoice_out(invoice, ctx.org.invoice_grace_days, latest)


def _record_payment(invoice: Invoice, body: InvoicePatch) -> None:
    """Mark an invoice paid, recording what was received and handling any difference.

    Settle (the default) closes the invoice at whatever was paid — a shortfall is
    forgiven, an overpayment kept. Carry-forward instead moves the difference onto the
    subscription's running balance, where the next generated invoice absorbs it: a
    shortfall adds to it, an overpayment credits it (§3.8).
    """
    # No amount given means paid in full — the common case, one click.
    paid = body.paid_amount if body.paid_amount is not None else invoice.amount
    difference = invoice.amount - paid  # positive = shortfall, negative = overpayment

    if difference != 0 and body.carry_forward:
        sub = invoice.subscription
        if sub is None or sub.status is not SubscriptionStatus.active:
            raise HTTPException(
                422,
                detail=(
                    "This subscription has no future invoice to carry the difference to "
                    "— settle it instead."
                ),
            )
        sub.carry_balance += difference
        invoice.difference_carried = True

    invoice.paid_amount = paid.quantize(Decimal("0.01"))
    invoice.status = InvoiceStatus.paid


@router.get("/{invoice_id}")
async def get_invoice_document(
    invoice_id: uuid.UUID, ctx: OrgUser, session: SessionDep
) -> InvoiceDocumentOut:
    """The full invoice as a document — issuer, bill-to, and what the period covers.

    One request so the printable view renders in a single pass, which matters when the
    browser's print dialog snapshots the page.
    """
    invoice = await session.get(Invoice, invoice_id)
    if invoice is None or invoice.org_id != ctx.org.id:
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
        bill_to=(
            InvoiceParty(
                name=client.name,
                company_name=client.company_name,
                address=client.address,
                email=client.email,
                phone=client.phone,
                gstin=client.gstin,
            )
            if client
            else InvoiceParty(
                name=invoice.bill_to_name or "—",
                address=invoice.bill_to_address,
                email=invoice.bill_to_email,
                phone=invoice.bill_to_phone,
                gstin=invoice.bill_to_gstin,
            )
        ),
        payment=PaymentInfo(
            upi_id=ctx.org.upi_id,
            bank_account_name=ctx.org.bank_account_name,
            bank_account_number=ctx.org.bank_account_number,
            bank_ifsc=ctx.org.bank_ifsc,
            bank_name=ctx.org.bank_name,
            show_qr=ctx.org.show_payment_qr,
        ),
        includes=[
            f"{d.quantity} {d.unit} — {d.name}"
            for d in (service.deliverables if service else [])
        ],
    )


@router.delete("/{invoice_id}", status_code=204)
async def delete_invoice(
    invoice_id: uuid.UUID, ctx: OrgUser, session: SessionDep
) -> None:
    """Permanently remove an invoice — only ever a voided one.

    A voided invoice bills nothing and generation already ignores it, so deleting it
    changes no billing coverage; it just clears the audit row from the list. A due
    invoice would only regenerate on the next run (void it first to cancel it), and a
    paid invoice is a record of money received and is never destroyed. Deletion is the
    deliberate second step after a void — cancel, then, if you want it gone, delete.
    """
    invoice = await session.get(Invoice, invoice_id)
    if invoice is None or invoice.org_id != ctx.org.id:
        raise HTTPException(404, detail="Invoice not found")

    if invoice.status is not InvoiceStatus.void:
        raise HTTPException(
            422,
            detail=(
                f"Only a voided invoice can be deleted — this one is {invoice.status}. "
                "Void it first to cancel it."
            ),
        )

    await session.delete(invoice)
    await session.commit()
