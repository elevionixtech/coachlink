import uuid

import sqlalchemy as sa
from fastapi import APIRouter, HTTPException

from app.deps import CurrentUser, SessionDep, ensure_org_not_expired
from app.models import AppUser, Organisation, Role
from app.schemas import MemberIn, MemberOut
from app.security import hash_password

router = APIRouter(prefix="/organisations", tags=["members"])


async def _resolve_org_for_member_mgmt(
    org_id: uuid.UUID, user: CurrentUser, session: SessionDep
) -> Organisation:
    """Own admin or superadmin; staff → 403, foreign org → 404 (§7). The org's own
    admin is blocked while the org subscription is lapsed; the superadmin never is (§5.7)."""
    if user.role == Role.superadmin:
        org = await session.get(Organisation, org_id)
        if org is None:
            raise HTTPException(404, detail="Organisation not found")
        return org
    if user.role != Role.admin:
        raise HTTPException(403, detail="Requires org admin")
    if user.org_id != org_id or user.org is None:
        raise HTTPException(404, detail="Organisation not found")
    ensure_org_not_expired(user.org)
    return user.org


@router.get("/{org_id}/members")
async def list_members(
    org_id: uuid.UUID, user: CurrentUser, session: SessionDep
) -> list[MemberOut]:
    org = await _resolve_org_for_member_mgmt(org_id, user, session)
    members = (
        await session.scalars(
            sa.select(AppUser).where(AppUser.org_id == org.id).order_by(AppUser.created_at)
        )
    ).all()
    return [MemberOut.model_validate(m) for m in members]


@router.post("/{org_id}/members", status_code=201)
async def add_member(
    org_id: uuid.UUID, body: MemberIn, user: CurrentUser, session: SessionDep
) -> MemberOut:
    org = await _resolve_org_for_member_mgmt(org_id, user, session)
    duplicate = await session.scalar(
        sa.select(AppUser.id).where(AppUser.org_id == org.id, AppUser.username == body.username)
    )
    if duplicate:
        raise HTTPException(409, detail=f"Username '{body.username}' already exists")
    member = AppUser(
        org_id=org.id,
        name=body.name,
        username=body.username,
        password_hash=hash_password(body.password),
        role=body.role,
    )
    session.add(member)
    await session.commit()
    return MemberOut.model_validate(member)
