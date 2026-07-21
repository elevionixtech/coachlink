import uuid
from datetime import UTC, datetime

import sqlalchemy as sa
from fastapi import APIRouter, HTTPException

from app.billing import effective_rate
from app.deps import OrgUser, SessionDep
from app.models import (
    AccountType,
    Client,
    ContactNote,
    Enrollment,
    Invoice,
    LifecycleStage,
    Service,
    Subscription,
)
from app.routers.common import (
    PAGE_LIMIT_DEFAULT,
    clamp_limit,
    get_owned_or_404,
    next_cursor,
    not_archived,
)
from app.schemas import (
    ClientIn,
    ClientOut,
    ClientPatch,
    ClientRef,
    EnrollmentOut,
    InvoiceOut,
    NoteIn,
    NoteOut,
    Page,
    SubscriptionIn,
    SubscriptionOut,
)

router = APIRouter(prefix="/clients", tags=["clients"])


async def _resolve_family_link(
    session: SessionDep, org_id: uuid.UUID, link_id: uuid.UUID, self_id: uuid.UUID | None
) -> Client:
    """Family links may only point to an existing client in the caller's org (§5.3)."""
    if self_id is not None and link_id == self_id:
        raise HTTPException(422, detail="A client cannot be family-linked to themselves")
    return await get_owned_or_404(session, Client, link_id, org_id)


def _apply_account_type_rules(data: dict) -> dict:
    """Company fields exist only on Corporate; the family link only on Family (§5.3)."""
    if data.get("account_type") != AccountType.corporate:
        data["company_name"] = None
        data["gstin"] = None
        data["company_contact"] = None
    if data.get("account_type") != AccountType.family:
        data["family_link_id"] = None
    return data


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
    cursor: int = 0,
    limit: int = PAGE_LIMIT_DEFAULT,
) -> Page[ClientOut]:
    limit = clamp_limit(limit)
    stmt = (
        sa.select(Client)
        .where(Client.org_id == ctx.org.id, not_archived(Client))
        .order_by(Client.created_at.desc(), Client.id)
        .offset(cursor)
        .limit(limit + 1)
    )
    if q:
        pattern = f"%{q}%"
        stmt = stmt.where(
            sa.or_(
                Client.name.ilike(pattern),
                Client.phone.ilike(pattern),
                Client.email.ilike(pattern),
            )
        )
    if lifecycle_stage:
        stmt = stmt.where(Client.lifecycle_stage == lifecycle_stage)
    rows = (await session.scalars(stmt)).all()
    return Page(
        items=[ClientOut.model_validate(c) for c in rows[:limit]],
        next_cursor=next_cursor(cursor, limit, len(rows)),
    )


@router.post("", status_code=201)
async def create_client(body: ClientIn, ctx: OrgUser, session: SessionDep) -> ClientOut:
    data = _apply_account_type_rules(body.model_dump())
    if data.get("family_link_id"):
        await _resolve_family_link(session, ctx.org.id, data["family_link_id"], None)
    client = Client(org_id=ctx.org.id, **data)
    session.add(client)
    await session.commit()
    return await _client_out(session, client)


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
    effective_type = data.get("account_type", client.account_type)
    if effective_type != AccountType.corporate:
        data["company_name"] = None
        data["gstin"] = None
        data["company_contact"] = None
    if effective_type != AccountType.family and "account_type" in data:
        data["family_link_id"] = None
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


def subscription_out(sub: Subscription) -> SubscriptionOut:
    out = SubscriptionOut.model_validate(sub)
    out.client_name = sub.client.name
    out.service_name = sub.service.name
    out.billing_interval = sub.service.billing_interval
    out.rate = sub.service.rate
    out.effective_rate = effective_rate(sub.service.rate, sub.discount_pct)
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
    await get_owned_or_404(session, Service, body.service_id, ctx.org.id)
    sub = Subscription(client_id=client_id, **body.model_dump())
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
    from app.routers.invoices import invoice_out

    await get_owned_or_404(session, Client, client_id, ctx.org.id)
    invoices = (
        await session.scalars(
            sa.select(Invoice)
            .where(Invoice.client_id == client_id)
            .order_by(Invoice.issue_date.desc(), Invoice.created_at.desc())
        )
    ).all()
    return [invoice_out(i, ctx.org.invoice_grace_days) for i in invoices]


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
