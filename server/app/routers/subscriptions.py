import uuid
from decimal import Decimal

from fastapi import APIRouter, HTTPException

from app.deps import OrgUser, SessionDep
from app.models import Service, Subscription
from app.routers.clients import _check_option_allowed, subscription_out
from app.routers.common import get_owned_or_404
from app.schemas import SubscriptionIn, SubscriptionOut, SubscriptionPatch

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])


@router.patch("/{subscription_id}")
async def update_subscription(
    subscription_id: uuid.UUID, body: SubscriptionPatch, ctx: OrgUser, session: SessionDep
) -> SubscriptionOut:
    sub = await session.get(Subscription, subscription_id)
    # Tenancy walks up through the client (child tables carry no org_id, §5.6).
    if sub is None or sub.client.org_id != ctx.org.id:
        raise HTTPException(404, detail="Subscription not found")
    sub.status = body.status
    await session.commit()
    return subscription_out(sub)


@router.put("/{subscription_id}")
async def edit_subscription(
    subscription_id: uuid.UUID, body: SubscriptionIn, ctx: OrgUser, session: SessionDep
) -> SubscriptionOut:
    """Edit a subscription's service, start date, pricing option or discount. Affects
    future invoice generation only — already-issued invoices keep their stored amount
    (§3.7). Same option-eligibility rule as creating one."""
    sub = await session.get(Subscription, subscription_id)
    if sub is None or sub.client.org_id != ctx.org.id:
        raise HTTPException(404, detail="Subscription not found")

    service = await get_owned_or_404(session, Service, body.service_id, ctx.org.id)
    data = body.model_dump()
    if body.pricing_option_id is not None:
        await _check_option_allowed(
            session, ctx.org.id, sub.client, service, body.pricing_option_id
        )
        # The option sets the price outright, so never store a discount that is ignored.
        data["discount_pct"] = Decimal("0")

    for key, value in data.items():
        setattr(sub, key, value)
    await session.commit()
    await session.refresh(sub)
    return subscription_out(sub)
