import uuid
from typing import TypeVar

import sqlalchemy as sa
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import Base

M = TypeVar("M", bound=Base)

PAGE_LIMIT_DEFAULT = 50
PAGE_LIMIT_MAX = 200


async def get_owned_or_404[M: Base](
    session: AsyncSession,
    model: type[M],
    obj_id: uuid.UUID,
    org_id: uuid.UUID,
    include_archived: bool = False,
) -> M:
    """Fetch-by-id with ownership check — a foreign tenant's id behaves as a 404,
    never a 403 (§5.6)."""
    obj = await session.get(model, obj_id)
    if (
        obj is None
        or getattr(obj, "org_id", None) != org_id
        or (not include_archived and getattr(obj, "archived_at", None) is not None)
    ):
        raise HTTPException(404, detail=f"{model.__name__} not found")
    return obj


def not_archived[M: Base](model: type[M]) -> sa.ColumnElement[bool]:
    return model.archived_at.is_(None)  # type: ignore[attr-defined]


def clamp_limit(limit: int) -> int:
    return max(1, min(limit, PAGE_LIMIT_MAX))


def next_cursor(offset: int, limit: int, fetched: int) -> int | None:
    return offset + limit if fetched > limit else None
