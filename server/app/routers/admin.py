import uuid
from datetime import date, timedelta

import sqlalchemy as sa
from fastapi import APIRouter, HTTPException

from app.deps import SessionDep, Superadmin, subscription_state
from app.models import AppUser, Client, Organisation, Role, SubscriptionPlan
from app.routers.auth import RESERVED_PLATFORM_CODE
from app.schemas import (
    AdminOrgIn,
    AdminOrgOut,
    AssignPlanIn,
    PlanIn,
    PlanOut,
    PlanPatch,
)
from app.security import hash_password

router = APIRouter(prefix="/admin", tags=["platform-admin"])


async def _org_out(session: SessionDep, org: Organisation) -> AdminOrgOut:
    member_count = await session.scalar(
        sa.select(sa.func.count()).where(AppUser.org_id == org.id)
    )
    client_count = await session.scalar(
        sa.select(sa.func.count()).where(Client.org_id == org.id, Client.archived_at.is_(None))
    )
    return AdminOrgOut(
        id=org.id,
        name=org.name,
        code=org.code,
        plan_id=org.plan_id,
        plan_name=org.plan.name if org.plan else None,
        subscription_starts_on=org.subscription_starts_on,
        subscription_ends_on=org.subscription_ends_on,
        subscription_state=subscription_state(org),
        member_count=member_count or 0,
        client_count=client_count or 0,
        created_at=org.created_at,
    )


@router.get("/organisations")
async def list_organisations(_: Superadmin, session: SessionDep) -> list[AdminOrgOut]:
    orgs = (
        (await session.scalars(sa.select(Organisation).order_by(Organisation.created_at)))
        .unique()
        .all()
    )
    return [await _org_out(session, org) for org in orgs]


@router.post("/organisations", status_code=201)
async def create_organisation(
    body: AdminOrgIn, _: Superadmin, session: SessionDep
) -> AdminOrgOut:
    code = body.code.strip().upper()
    if code == RESERVED_PLATFORM_CODE:
        raise HTTPException(422, detail='"PLATFORM" is reserved and cannot be claimed')
    conflict = await session.scalar(
        sa.select(Organisation.id).where(
            sa.or_(
                sa.func.upper(Organisation.code) == code,
                sa.func.lower(Organisation.name) == body.name.strip().lower(),
            )
        )
    )
    if conflict:
        raise HTTPException(409, detail="An organisation with that name or code exists")
    org = Organisation(name=body.name.strip(), code=code)
    session.add(org)
    await session.flush()
    # First user's role is forced admin (§7).
    session.add(
        AppUser(
            org_id=org.id,
            name=body.admin.name,
            username=body.admin.username,
            password_hash=hash_password(body.admin.password),
            role=Role.admin,
        )
    )
    await session.commit()
    return await _org_out(session, org)


@router.post("/organisations/{org_id}/plan")
async def assign_plan(
    org_id: uuid.UUID, body: AssignPlanIn, _: Superadmin, session: SessionDep
) -> AdminOrgOut:
    org = await session.get(Organisation, org_id)
    if org is None:
        raise HTTPException(404, detail="Organisation not found")
    plan = await session.get(SubscriptionPlan, body.plan_id)
    if plan is None:
        raise HTTPException(404, detail="Plan not found")
    # Assigning stamps starts_on (defaults to today) and ends_on = starts_on + days (§5.7).
    starts_on = body.starts_on or date.today()
    org.plan_id = plan.id
    org.subscription_starts_on = starts_on
    org.subscription_ends_on = starts_on + timedelta(days=plan.no_of_days)
    await session.commit()
    await session.refresh(org)
    return await _org_out(session, org)


# ---------------------------------------------------------------- plans


async def _plan_out(session: SessionDep, plan: SubscriptionPlan) -> PlanOut:
    in_use = await session.scalar(
        sa.select(sa.func.count()).where(Organisation.plan_id == plan.id)
    )
    out = PlanOut.model_validate(plan)
    out.orgs_in_use = in_use or 0
    return out


@router.get("/plans")
async def list_plans(_: Superadmin, session: SessionDep) -> list[PlanOut]:
    plans = (
        await session.scalars(sa.select(SubscriptionPlan).order_by(SubscriptionPlan.created_at))
    ).all()
    return [await _plan_out(session, p) for p in plans]


@router.post("/plans", status_code=201)
async def create_plan(body: PlanIn, _: Superadmin, session: SessionDep) -> PlanOut:
    conflict = await session.scalar(
        sa.select(SubscriptionPlan.id).where(
            sa.func.lower(SubscriptionPlan.name) == body.name.strip().lower()
        )
    )
    if conflict:
        raise HTTPException(409, detail=f"Plan '{body.name}' already exists")
    plan = SubscriptionPlan(**{**body.model_dump(), "name": body.name.strip()})
    session.add(plan)
    await session.commit()
    return await _plan_out(session, plan)


@router.patch("/plans/{plan_id}")
async def update_plan(
    plan_id: uuid.UUID, body: PlanPatch, _: Superadmin, session: SessionDep
) -> PlanOut:
    plan = await session.get(SubscriptionPlan, plan_id)
    if plan is None:
        raise HTTPException(404, detail="Plan not found")
    data = body.model_dump(exclude_unset=True)
    if "name" in data:
        conflict = await session.scalar(
            sa.select(SubscriptionPlan.id).where(
                sa.func.lower(SubscriptionPlan.name) == data["name"].strip().lower(),
                SubscriptionPlan.id != plan_id,
            )
        )
        if conflict:
            raise HTTPException(409, detail=f"Plan '{data['name']}' already exists")
    for key, value in data.items():
        setattr(plan, key, value)
    await session.commit()
    return await _plan_out(session, plan)


@router.delete("/plans/{plan_id}", status_code=204)
async def delete_plan(plan_id: uuid.UUID, _: Superadmin, session: SessionDep) -> None:
    plan = await session.get(SubscriptionPlan, plan_id)
    if plan is None:
        raise HTTPException(404, detail="Plan not found")
    in_use = await session.scalar(
        sa.select(sa.func.count()).where(Organisation.plan_id == plan_id)
    )
    if in_use:
        raise HTTPException(409, detail=f"In use by {in_use} organisation(s)")
    await session.delete(plan)
    await session.commit()
