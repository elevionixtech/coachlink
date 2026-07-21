from dataclasses import dataclass
from datetime import date
from typing import Annotated, Literal

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import AppUser, Organisation, Role
from app.security import decode_token

bearer = HTTPBearer(auto_error=False)

SessionDep = Annotated[AsyncSession, Depends(get_session)]

SubscriptionState = Literal["none", "active", "expired"]


def subscription_state(org: Organisation) -> SubscriptionState:
    if org.plan_id is None or org.subscription_ends_on is None:
        return "none"
    return "expired" if org.subscription_ends_on < date.today() else "active"


def ensure_org_not_expired(org: Organisation) -> None:
    """Shared expiry chokepoint (§5.7) — used at login, require_org_user and member mgmt."""
    if subscription_state(org) == "expired":
        assert org.subscription_ends_on is not None
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail=(
                f"Subscription for {org.name} expired on "
                f"{org.subscription_ends_on.strftime('%d %b %Y')}"
            ),
        )


async def get_current_user(
    session: SessionDep,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> AppUser:
    if credentials is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    user_id = decode_token(credentials.credentials, "access")
    if user_id is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    user = await session.get(AppUser, user_id)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    return user


CurrentUser = Annotated[AppUser, Depends(get_current_user)]


@dataclass
class OrgContext:
    user: AppUser
    org: Organisation


async def require_org_user(user: CurrentUser) -> OrgContext:
    """Every domain endpoint passes through this: rejects org-less (platform) users
    and yields the caller's org — never trusted from the client (§2, §5.6)."""
    if user.org_id is None or user.org is None:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, detail="Platform accounts cannot access domain APIs"
        )
    ensure_org_not_expired(user.org)
    return OrgContext(user=user, org=user.org)


OrgUser = Annotated[OrgContext, Depends(require_org_user)]


async def require_org_admin(ctx: OrgUser) -> OrgContext:
    if ctx.user.role != Role.admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Requires org admin")
    return ctx


OrgAdmin = Annotated[OrgContext, Depends(require_org_admin)]


async def require_superadmin(user: CurrentUser) -> AppUser:
    if user.role != Role.superadmin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Requires platform superadmin")
    return user


Superadmin = Annotated[AppUser, Depends(require_superadmin)]
