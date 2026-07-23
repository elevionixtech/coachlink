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
    InvoiceStatus,
    Organisation,
    PricingMode,
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


def subscription_amount(sub: Subscription) -> Decimal:
    """What one period of this subscription costs (§3.7).

    A pricing option wins outright — discount_pct applies only in its absence, so the
    two never compound. Routers force discount_pct to 0 whenever an option is set, so
    that is belt-and-braces rather than the only guard.

    A subscription pointing at an option the service no longer offers falls back to the
    base rate: pricing that silently disappears is better than an invoice that crashes
    the nightly run for every other client.
    """
    if sub.pricing_option_id is None:
        return effective_rate(sub.service.rate, sub.discount_pct)

    wanted = sub.pricing_option_id
    spo = next((p for p in sub.service.pricing_options if p.pricing_option_id == wanted), None)
    if spo is None:
        return effective_rate(sub.service.rate, sub.discount_pct)
    if spo.pricing_mode is PricingMode.fixed_rate:
        return spo.value.quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return effective_rate(sub.service.rate, spo.value)


def missing_periods(
    anchor: date,
    interval: BillingInterval,
    existing_starts: set[date],
    today: date,
    covered: list[tuple[date, date]] | None = None,
) -> list[tuple[str, date, date]]:
    """(label, period_start, period_end) for every period from the anchor to today
    that has no invoice yet.

    `anchor` is normally subscription.start_date, so periods stay anchored and a
    month-end start never drifts. When an invoice's end date has been extended by hand
    the caller passes the day after it instead, which shifts every later period by the
    same amount — that is the point of the extension.

    `covered` is every (start, end) range a live invoice already bills. It has to be the
    actual ranges rather than one high-water mark: a voided period leaves a hole that
    later invoices must not paper over, and only a real range test can tell a hole from
    a period genuinely swallowed by an extension.
    """
    if anchor > today:
        return []
    ranges = covered or []

    def unbilled(start: date) -> bool:
        if start in existing_starts:
            return False
        return not any(lo <= start <= hi for lo, hi in ranges)

    if interval == BillingInterval.na:
        if not unbilled(anchor):
            return []
        return [(period_label(anchor, interval), anchor, anchor)]

    out: list[tuple[str, date, date]] = []
    n = 0
    while (cursor := nth_period_start(anchor, interval, n)) <= today:
        end = nth_period_start(anchor, interval, n + 1) - timedelta(days=1)
        if unbilled(cursor):
            out.append((period_label(cursor, interval), cursor, end))
        n += 1
    return out


def live_invoices(invoices: list[Invoice]) -> list[Invoice]:
    """Voided invoices bill nothing, so generation ignores them entirely (§3.8) — their
    period counts as unbilled and gets re-issued."""
    return [i for i in invoices if i.status is not InvoiceStatus.void]


def billing_anchor(sub: Subscription, invoices: list[Invoice]) -> date:
    """Where the next period starts counting from.

    The subscription start, unless someone has extended an invoice — then the day after
    the latest such end date, so the shift carries forward instead of being reabsorbed.
    A voided extension is ignored along with the rest of the voided invoice.
    """
    adjusted = [i.period_end for i in live_invoices(invoices) if i.period_end_adjusted]
    return max(adjusted) + timedelta(days=1) if adjusted else sub.start_date


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
        invoices = list(
            (
                await session.scalars(
                    sa.select(Invoice).where(Invoice.subscription_id == sub.id)
                )
            ).all()
        )
        live = live_invoices(invoices)
        existing_starts = {i.period_start for i in live}
        covered = [(i.period_start, i.period_end) for i in live]
        amount = subscription_amount(sub)
        for label, issue_date, period_end in missing_periods(
            billing_anchor(sub, invoices),
            sub.service.billing_interval,
            existing_starts,
            today,
            covered,
        ):
            session.add(
                Invoice(
                    number=format_invoice_number(
                        org.invoice_prefix, issue_date.year, org.next_invoice_seq
                    ),
                    client_id=sub.client_id,
                    subscription_id=sub.id,
                    period_label=label,
                    period_start=issue_date,
                    period_end=period_end,
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
