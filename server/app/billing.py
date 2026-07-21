"""Invoice generation (§5.2): walk billing periods per active subscription from
start_date to today; create a `due` invoice for each (subscription, period_label)
that has none. Idempotent by the unique constraint on that pair."""

import calendar
import uuid
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    BillingInterval,
    Client,
    Invoice,
    Organisation,
    Subscription,
    SubscriptionStatus,
)


def add_months(d: date, months: int) -> date:
    month_index = d.month - 1 + months
    year = d.year + month_index // 12
    month = month_index % 12 + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def nth_period_start(start: date, interval: BillingInterval, n: int) -> date:
    """Period n's start, always anchored to the subscription start so a month-end
    start date (e.g. Jan 31) doesn't drift after clamping (Feb 28 → Mar 28)."""
    match interval:
        case BillingInterval.weekly:
            return start + timedelta(days=7 * n)
        case BillingInterval.monthly:
            return add_months(start, n)
        case BillingInterval.quarterly:
            return add_months(start, 3 * n)
        case BillingInterval.semi_annual:
            return add_months(start, 6 * n)
        case BillingInterval.annual:
            return add_months(start, 12 * n)
    raise ValueError(f"interval {interval} does not step")


def period_label(d: date, interval: BillingInterval) -> str:
    match interval:
        case BillingInterval.na:
            return "One-time"
        case BillingInterval.weekly:
            return f"Wk of {d.day} {d.strftime('%b %Y')}"
        case BillingInterval.monthly:
            return d.strftime("%b %Y")
        case BillingInterval.quarterly:
            return f"Q{(d.month - 1) // 3 + 1} {d.year}"
        case BillingInterval.semi_annual:
            return f"H{1 if d.month <= 6 else 2} {d.year}"
        case BillingInterval.annual:
            return str(d.year)


def effective_rate(rate: Decimal, discount_pct: Decimal) -> Decimal:
    """service.rate × (1 − discount/100), rounded to the rupee (§3.7)."""
    return (rate * (Decimal(100) - discount_pct) / Decimal(100)).quantize(
        Decimal("1"), rounding=ROUND_HALF_UP
    )


def missing_periods(
    start_date: date, interval: BillingInterval, existing_labels: set[str], today: date
) -> list[tuple[str, date]]:
    """(label, issue_date) for every period from start_date to today without an invoice."""
    if start_date > today:
        return []
    if interval == BillingInterval.na:
        label = period_label(start_date, interval)
        return [] if label in existing_labels else [(label, start_date)]
    out: list[tuple[str, date]] = []
    n = 0
    while (cursor := nth_period_start(start_date, interval, n)) <= today:
        label = period_label(cursor, interval)
        if label not in existing_labels:
            out.append((label, cursor))
        n += 1
    return out


def format_invoice_number(prefix: str, year: int, seq: int) -> str:
    return f"{prefix}-{year}-{seq:04d}"


async def generate_missing(
    session: AsyncSession, org: Organisation, client_id: uuid.UUID | None = None
) -> int:
    """Create missing invoices for the org's active subscriptions. Returns count created."""
    stmt = (
        sa.select(Subscription)
        .join(Client, Subscription.client_id == Client.id)
        .where(Client.org_id == org.id, Subscription.status == SubscriptionStatus.active)
    )
    if client_id is not None:
        stmt = stmt.where(Subscription.client_id == client_id)
    subs = (await session.scalars(stmt)).all()

    today = date.today()
    created = 0
    for sub in subs:
        existing = set(
            (
                await session.scalars(
                    sa.select(Invoice.period_label).where(Invoice.subscription_id == sub.id)
                )
            ).all()
        )
        amount = effective_rate(sub.service.rate, sub.discount_pct)
        for label, issue_date in missing_periods(
            sub.start_date, sub.service.billing_interval, existing, today
        ):
            session.add(
                Invoice(
                    number=format_invoice_number(
                        org.invoice_prefix, issue_date.year, org.next_invoice_seq
                    ),
                    client_id=sub.client_id,
                    subscription_id=sub.id,
                    period_label=label,
                    issue_date=issue_date,
                    amount=amount,
                )
            )
            org.next_invoice_seq += 1
            created += 1
    await session.flush()
    return created


def is_overdue(invoice: Invoice, grace_days: int, today: date | None = None) -> bool:
    """Overdue is derived, never stored: due AND issue_date + grace < today (§3.8)."""
    from app.models import InvoiceStatus

    today = today or date.today()
    return (
        invoice.status == InvoiceStatus.due
        and invoice.issue_date + timedelta(days=grace_days) < today
    )
