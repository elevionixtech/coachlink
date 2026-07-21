import uuid

from fastapi import APIRouter, HTTPException

from app.deps import OrgUser, SessionDep
from app.models import Subscription
from app.routers.clients import subscription_out
from app.schemas import SubscriptionOut, SubscriptionPatch

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
