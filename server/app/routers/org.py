from fastapi import APIRouter

from app.deps import OrgAdmin, OrgUser, SessionDep
from app.schemas import OrgSettingsOut, OrgSettingsPatch

router = APIRouter(prefix="/org", tags=["org"])


@router.get("")
async def get_org(ctx: OrgUser) -> OrgSettingsOut:
    return OrgSettingsOut.model_validate(ctx.org)


@router.patch("")
async def update_org(
    body: OrgSettingsPatch, ctx: OrgAdmin, session: SessionDep
) -> OrgSettingsOut:
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(ctx.org, key, value)
    await session.commit()
    return OrgSettingsOut.model_validate(ctx.org)
