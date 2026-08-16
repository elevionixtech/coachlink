import uuid
from datetime import UTC, datetime
from decimal import Decimal

import sqlalchemy as sa
from fastapi import APIRouter, HTTPException

from app.billing import subscription_amount
from app.deps import OrgAdmin, OrgUser, SessionDep
from app.models import (
    Batch,
    Client,
    ContactNote,
    Enrollment,
    Invoice,
    LifecycleStage,
    PricingOption,
    Service,
    Subscription,
    SubscriptionStatus,
    batch_service,
)
from app.routers.common import (
    PAGE_LIMIT_DEFAULT,
    clamp_limit,
    get_owned_or_404,
    next_cursor,
    not_archived,
)
from app.schemas import (
    AdvanceInvoiceIn,
    BatchOut,
    ClientIn,
    ClientOut,
    ClientPatch,
    ClientRef,
    EnrollmentOut,
    GenerateMissingOut,
    InvoiceOut,
    NoteIn,
    NoteOut,
    Page,
    SubscriptionIn,
    SubscriptionOut,
    SubscriptionTotalOut,
)

router = APIRouter(prefix="/clients", tags=["clients"])


async def _resolve_family_link(
    session: SessionDep, org_id: uuid.UUID, link_id: uuid.UUID, self_id: uuid.UUID | None
) -> Client:
    """Family links may only point to an existing client in the caller's org (§5.3)."""
    if self_id is not None and link_id == self_id:
        raise HTTPException(422, detail="A client cannot be family-linked to themselves")
    return await get_owned_or_404(session, Client, link_id, org_id)


async def _client_out(session: SessionDep, client: Client) -> ClientOut:
    out = ClientOut.model_validate(client)
    if client.family_link_id:
        linked = await session.get(Client, client.family_link_id)
        out.family_link_name = linked.name if linked else None
    linked_by = (
        await session.scalars(
            sa.select(Client).where(Client.family_link_id == client.id, not_archived(Client))
        )
    ).all()
    out.linked_by = [ClientRef.model_validate(c) for c in linked_by]
    return out


@router.get("")
async def list_clients(
    ctx: OrgUser,
    session: SessionDep,
    q: str | None = None,
    lifecycle_stage: LifecycleStage | None = None,
    active_subscribers: bool = False,
    cursor: int = 0,
    limit: int = PAGE_LIMIT_DEFAULT,
) -> Page[ClientOut]:
    limit = clamp_limit(limit)
    # One set of filters drives both the page query and its total count, so the count
    # always reflects exactly what is (or would be) shown.
    conditions = [Client.org_id == ctx.org.id, not_archived(Client)]
    if q:
        pattern = f"%{q}%"
        conditions.append(
            sa.or_(
                Client.name.ilike(pattern),
                Client.phone.ilike(pattern),
                Client.email.ilike(pattern),
            )
        )
    if lifecycle_stage:
        conditions.append(Client.lifecycle_stage == lifecycle_stage)
    if active_subscribers:
        with_active = sa.select(Subscription.client_id).where(
            Subscription.status == SubscriptionStatus.active
        )
        conditions.append(Client.id.in_(with_active))

    total = await session.scalar(
        sa.select(sa.func.count()).select_from(Client).where(*conditions)
    )
    stmt = (
        sa.select(Client)
        .where(*conditions)
        .order_by(Client.created_at.desc(), Client.id)
        .offset(cursor)
        .limit(limit + 1)
    )
    rows = (await session.scalars(stmt)).all()
    page = rows[:limit]
    services, batches = await _client_summaries(session, [c.id for c in page])
    items = []
    for c in page:
        out = ClientOut.model_validate(c)
        out.active_services = services.get(c.id, [])
        batch = batches.get(c.id)
        if batch:
            out.batch_name, out.batch_code = batch
        items.append(out)
    return Page(
        items=items, next_cursor=next_cursor(cursor, limit, len(rows)), total=total
    )


async def _client_summaries(
    session: SessionDep, client_ids: list[uuid.UUID]
) -> tuple[dict[uuid.UUID, list[str]], dict[uuid.UUID, tuple[str, str]]]:
    """Bulk-load, for a page of clients, the service names of their active
    subscriptions and the batch (name, code) each is enrolled in — one query each
    rather than per-row, for the clients list summary. A client is in at most one
    batch (§5.5)."""
    if not client_ids:
        return {}, {}
    sub_rows = await session.execute(
        sa.select(Subscription.client_id, Service.name)
        .join(Service, Service.id == Subscription.service_id)
        .where(
            Subscription.client_id.in_(client_ids),
            Subscription.status == SubscriptionStatus.active,
        )
        .order_by(Service.name)
    )
    services: dict[uuid.UUID, list[str]] = {}
    for cid, name in sub_rows.all():
        services.setdefault(cid, []).append(name)

    batch_rows = await session.execute(
        sa.select(Enrollment.client_id, Batch.name, Batch.code)
        .join(Batch, Batch.id == Enrollment.batch_id)
        .where(Enrollment.client_id.in_(client_ids))
    )
    batches = {cid: (name, code) for cid, name, code in batch_rows.all()}
    return services, batches


@router.post("", status_code=201)
async def create_client(body: ClientIn, ctx: OrgUser, session: SessionDep) -> ClientOut:
    data = body.model_dump()
    if data.get("family_link_id"):
        await _resolve_family_link(session, ctx.org.id, data["family_link_id"], None)
    client = Client(org_id=ctx.org.id, **data)
    session.add(client)
    await session.commit()
    return await _client_out(session, client)


# Declared before /{client_id} so the literal path is not swallowed by the UUID route.
@router.get("/subscription-total")
async def clients_subscription_total(
    ctx: OrgAdmin, session: SessionDep
) -> SubscriptionTotalOut:
    """Org-wide sum of every active subscription's per-period amount, across all clients.
    Admin only (OrgAdmin dependency 403s staff)."""
    subs = (
        await session.scalars(
            sa.select(Subscription)
            .join(Client, Client.id == Subscription.client_id)
            .where(
                Client.org_id == ctx.org.id,
                not_archived(Client),
                Subscription.status == SubscriptionStatus.active,
            )
        )
    ).all()
    total = sum((subscription_amount(s) for s in subs), Decimal("0"))
    return SubscriptionTotalOut(total=total, active_subscriptions=len(subs))


@router.get("/{client_id}")
async def get_client(client_id: uuid.UUID, ctx: OrgUser, session: SessionDep) -> ClientOut:
    client = await get_owned_or_404(session, Client, client_id, ctx.org.id)
    return await _client_out(session, client)


@router.patch("/{client_id}")
async def update_client(
    client_id: uuid.UUID, body: ClientPatch, ctx: OrgUser, session: SessionDep
) -> ClientOut:
    client = await get_owned_or_404(session, Client, client_id, ctx.org.id)
    data = body.model_dump(exclude_unset=True)
    if data.get("family_link_id"):
        await _resolve_family_link(session, ctx.org.id, data["family_link_id"], client.id)
    for key, value in data.items():
        setattr(client, key, value)
    await session.commit()
    return await _client_out(session, client)


@router.delete("/{client_id}", status_code=204)
async def archive_client(client_id: uuid.UUID, ctx: OrgUser, session: SessionDep) -> None:
    client = await get_owned_or_404(session, Client, client_id, ctx.org.id)
    client.archived_at = datetime.now(UTC)
    await session.commit()


# ---------------------------------------------------------------- notes


@router.get("/{client_id}/notes")
async def list_notes(client_id: uuid.UUID, ctx: OrgUser, session: SessionDep) -> list[NoteOut]:
    await get_owned_or_404(session, Client, client_id, ctx.org.id)
    notes = (
        await session.scalars(
            sa.select(ContactNote)
            .where(ContactNote.client_id == client_id)
            .order_by(ContactNote.date.desc(), ContactNote.created_at.desc())
        )
    ).all()
    return [
        NoteOut(
            id=n.id,
            date=n.date,
            channel=n.channel,
            text=n.text,
            author_name=n.author.name,
            created_at=n.created_at,
        )
        for n in notes
    ]


@router.post("/{client_id}/notes", status_code=201)
async def add_note(
    client_id: uuid.UUID, body: NoteIn, ctx: OrgUser, session: SessionDep
) -> NoteOut:
    await get_owned_or_404(session, Client, client_id, ctx.org.id)
    note = ContactNote(client_id=client_id, author_id=ctx.user.id, **body.model_dump())
    session.add(note)
    await session.commit()
    return NoteOut(
        id=note.id,
        date=note.date,
        channel=note.channel,
        text=note.text,
        author_name=ctx.user.name,
        created_at=note.created_at,
    )


# ---------------------------------------------------------------- subscriptions


async def _check_option_priced(
    session: SessionDep,
    org_id: uuid.UUID,
    service: Service,
    option_id: uuid.UUID,
) -> None:
    """A subscription may only use a pricing option the service actually prices (§3.7).
    Any option a service offers is available to any client — the operator chooses."""
    option = await get_owned_or_404(session, PricingOption, option_id, org_id)
    if not any(p.pricing_option_id == option_id for p in service.pricing_options):
        raise HTTPException(
            422, detail=f"Service '{service.name}' has no price for '{option.name}'"
        )


def subscription_out(sub: Subscription) -> SubscriptionOut:
    out = SubscriptionOut.model_validate(sub)
    out.client_name = sub.client.name
    out.service_name = sub.service.name
    out.billing_interval = sub.service.billing_interval
    out.rate = sub.service.rate
    out.effective_rate = subscription_amount(sub)
    out.pricing_option_name = sub.pricing_option.name if sub.pricing_option else None
    return out


@router.get("/{client_id}/subscriptions")
async def list_client_subscriptions(
    client_id: uuid.UUID, ctx: OrgUser, session: SessionDep
) -> list[SubscriptionOut]:
    await get_owned_or_404(session, Client, client_id, ctx.org.id)
    subs = (
        await session.scalars(
            sa.select(Subscription)
            .where(Subscription.client_id == client_id)
            .order_by(Subscription.created_at.desc())
        )
    ).all()
    return [subscription_out(s) for s in subs]


@router.post("/{client_id}/subscriptions", status_code=201)
async def create_subscription(
    client_id: uuid.UUID, body: SubscriptionIn, ctx: OrgUser, session: SessionDep
) -> SubscriptionOut:
    client = await get_owned_or_404(session, Client, client_id, ctx.org.id)
    service = await get_owned_or_404(session, Service, body.service_id, ctx.org.id)
    data = body.model_dump()
    if body.pricing_option_id is not None:
        await _check_option_priced(session, ctx.org.id, service, body.pricing_option_id)
        # The option sets the price outright, so never store a discount that is ignored
        # at invoice time (§3.7) — same normalisation idiom as _normalise_account_fields.
        data["discount_pct"] = Decimal("0")
    sub = Subscription(client_id=client_id, **data)
    session.add(sub)
    # Creating a subscription promotes the client to Customer if not already (§5.1).
    if client.lifecycle_stage != LifecycleStage.customer:
        client.lifecycle_stage = LifecycleStage.customer
    await session.commit()
    await session.refresh(sub)
    return subscription_out(sub)


# ---------------------------------------------------------------- tabs


@router.get("/{client_id}/invoices")
async def list_client_invoices(
    client_id: uuid.UUID, ctx: OrgUser, session: SessionDep
) -> list[InvoiceOut]:
    from app.routers.invoices import invoice_out, latest_period_starts

    await get_owned_or_404(session, Client, client_id, ctx.org.id)
    invoices = (
        await session.scalars(
            sa.select(Invoice)
            .where(Invoice.client_id == client_id)
            .order_by(Invoice.issue_date.desc(), Invoice.created_at.desc())
        )
    ).all()
    latest = await latest_period_starts(session, [i.subscription_id for i in invoices])
    return [invoice_out(i, ctx.org.invoice_grace_days, latest) for i in invoices]


@router.post("/{client_id}/invoices/advance")
async def bill_client_in_advance(
    client_id: uuid.UUID, body: AdvanceInvoiceIn, ctx: OrgUser, session: SessionDep
) -> GenerateMissingOut:
    """Generate the next upcoming invoice(s) for this client's active subscriptions,
    ahead of the automatic schedule — for a client who wants to pay early (§5.2)."""
    from app.billing import generate_advance

    await get_owned_or_404(session, Client, client_id, ctx.org.id)
    created = await generate_advance(session, ctx.org, client_id, body.periods)
    await session.commit()
    return GenerateMissingOut(created=created)


@router.get("/{client_id}/enrollments")
async def list_client_enrollments(
    client_id: uuid.UUID, ctx: OrgUser, session: SessionDep
) -> list[EnrollmentOut]:
    await get_owned_or_404(session, Client, client_id, ctx.org.id)
    enrollments = (
        await session.scalars(
            sa.select(Enrollment)
            .where(Enrollment.client_id == client_id)
            .order_by(Enrollment.created_at.desc())
        )
    ).all()
    return [
        EnrollmentOut(
            id=e.id,
            client_id=e.client_id,
            batch_id=e.batch_id,
            client_name=e.client.name,
            batch_name=e.batch.name,
            batch_code=e.batch.code,
            start_date=e.start_date,
            created_at=e.created_at,
        )
        for e in enrollments
    ]


@router.get("/{client_id}/eligible-batches")
async def list_eligible_batches(
    client_id: uuid.UUID, ctx: OrgUser, session: SessionDep
) -> list[BatchOut]:
    """Batches this client may enrol in (§5.5): those whose services include one of the
    client's active subscriptions, plus serviceless (open-to-all) batches — ordered by
    schedule, earliest first. A client may be in only one batch, so once enrolled
    anywhere this returns nothing."""
    from app.routers.batches import batch_out, enrolled_counts, schedule_order

    await get_owned_or_404(session, Client, client_id, ctx.org.id)
    already_enrolled = await session.scalar(
        sa.select(sa.func.count())
        .select_from(Enrollment)
        .where(Enrollment.client_id == client_id)
    )
    if already_enrolled:
        return []

    active_services = sa.select(Subscription.service_id).where(
        Subscription.client_id == client_id,
        Subscription.status == SubscriptionStatus.active,
    )
    # Open batches list no service; otherwise the client must subscribe to one of them.
    open_batch = ~sa.exists().where(batch_service.c.batch_id == Batch.id)
    matched = sa.exists().where(
        batch_service.c.batch_id == Batch.id,
        batch_service.c.service_id.in_(active_services),
    )
    stmt = (
        sa.select(Batch)
        .where(
            Batch.org_id == ctx.org.id,
            not_archived(Batch),
            sa.or_(open_batch, matched),
        )
        .order_by(*schedule_order())
    )
    rows = (await session.scalars(stmt)).unique().all()
    counts = await enrolled_counts(session, [b.id for b in rows])
    return [batch_out(b, counts.get(b.id, 0)) for b in rows]
