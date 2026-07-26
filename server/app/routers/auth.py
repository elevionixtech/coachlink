import sqlalchemy as sa
from fastapi import APIRouter, HTTPException

from app.deps import CurrentUser, SessionDep, ensure_org_not_expired
from app.models import AppUser, Organisation
from app.schemas import LoginIn, PasswordChangeIn, RefreshIn, TokenPair, UserOut
from app.security import create_token, decode_token, hash_password, verify_password

router = APIRouter(tags=["auth"])

RESERVED_PLATFORM_CODE = "PLATFORM"
GENERIC_LOGIN_ERROR = "Invalid organisation code, username or password"


def _token_pair(user: AppUser) -> TokenPair:
    return TokenPair(
        access_token=create_token(user.id, "access"),
        refresh_token=create_token(user.id, "refresh"),
        user=UserOut.model_validate(user),
    )


@router.post("/login")
async def login(body: LoginIn, session: SessionDep) -> TokenPair:
    code = body.org_code.strip().upper()

    org: Organisation | None = None
    if code != RESERVED_PLATFORM_CODE:
        org = await session.scalar(
            sa.select(Organisation).where(sa.func.upper(Organisation.code) == code)
        )
        if org is None:
            raise HTTPException(401, detail=GENERIC_LOGIN_ERROR)

    user = await session.scalar(
        sa.select(AppUser).where(
            AppUser.username == body.username,
            AppUser.org_id == (org.id if org else None),
        )
    )
    if user is None or not verify_password(body.password, user.password_hash):
        # Always the same generic message — never reveal which part was wrong (§2).
        raise HTTPException(401, detail=GENERIC_LOGIN_ERROR)

    if org is not None:
        ensure_org_not_expired(org)

    return _token_pair(user)


@router.post("/refresh")
async def refresh(body: RefreshIn, session: SessionDep) -> TokenPair:
    user_id = decode_token(body.refresh_token, "refresh")
    if user_id is None:
        raise HTTPException(401, detail="Invalid or expired refresh token")
    user = await session.get(AppUser, user_id)
    if user is None:
        raise HTTPException(401, detail="Invalid or expired refresh token")
    return _token_pair(user)


@router.get("/me")
async def me(user: CurrentUser) -> UserOut:
    return UserOut.model_validate(user)


@router.post("/me/password", status_code=204)
async def change_password(
    body: PasswordChangeIn, user: CurrentUser, session: SessionDep
) -> None:
    """Change the signed-in user's own password. Requires the current password so a
    walk-up on an unlocked session can't hijack the account."""
    if not verify_password(body.current_password, user.password_hash):
        raise HTTPException(422, detail="Current password is incorrect")
    user.password_hash = hash_password(body.new_password)
    await session.commit()
