import uuid
from collections.abc import AsyncIterator
from datetime import date

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db import Base, get_session
from app.main import app
from app.models import AppUser, Organisation, Role
from app.security import hash_password

PASSWORD = "pass1234"
PASSWORD_HASH = hash_password(PASSWORD)  # hash once — bcrypt is slow


@pytest_asyncio.fixture
async def db_sessionmaker():
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


@pytest_asyncio.fixture
async def session(db_sessionmaker):
    async with db_sessionmaker() as s:
        yield s


@pytest_asyncio.fixture
async def client(db_sessionmaker) -> AsyncIterator[AsyncClient]:
    async def override() -> AsyncIterator:
        async with db_sessionmaker() as s:
            yield s

    app.dependency_overrides[get_session] = override
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


def make_user(org_id: uuid.UUID | None, username: str, role: Role, name: str = "") -> AppUser:
    return AppUser(
        org_id=org_id,
        name=name or username.title(),
        username=username,
        password_hash=PASSWORD_HASH,
        role=role,
    )


@pytest_asyncio.fixture
async def seed(session):
    """Two orgs (A, B) with admin+staff each, plus a platform superadmin."""
    org_a = Organisation(name="Studio A", code="ORGA")
    org_b = Organisation(name="Studio B", code="ORGB")
    session.add_all([org_a, org_b])
    await session.flush()
    users = [
        make_user(None, "root", Role.superadmin, "Platform Root"),
        make_user(org_a.id, "admin-a", Role.admin),
        make_user(org_a.id, "staff-a", Role.staff),
        make_user(org_b.id, "admin-b", Role.admin),
        make_user(org_b.id, "staff-b", Role.staff),
    ]
    session.add_all(users)
    await session.commit()
    return {"org_a": org_a, "org_b": org_b}


async def login(client: AsyncClient, org_code: str, username: str, password: str = PASSWORD):
    return await client.post(
        "/api/login",
        json={"org_code": org_code, "username": username, "password": password},
    )


async def auth_headers(client: AsyncClient, org_code: str, username: str) -> dict[str, str]:
    res = await login(client, org_code, username)
    assert res.status_code == 200, res.text
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


@pytest_asyncio.fixture
async def headers_a(client, seed):
    return await auth_headers(client, "ORGA", "admin-a")


@pytest_asyncio.fixture
async def headers_a_staff(client, seed):
    return await auth_headers(client, "ORGA", "staff-a")


@pytest_asyncio.fixture
async def headers_b(client, seed):
    return await auth_headers(client, "ORGB", "admin-b")


@pytest_asyncio.fixture
async def headers_root(client, seed):
    return await auth_headers(client, "PLATFORM", "root")


# ---------------------------------------------------------------- domain helpers


async def create_service(client: AsyncClient, headers: dict, sku: str = "SKU-1", **kw):
    body = {
        "name": kw.pop("name", "Hatha Yoga — Monthly"),
        "sku": sku,
        "service_type": "Subscription",
        "delivery_mode": "Offline",
        "billing_interval": "Monthly",
        "rate": "3000",
        "deliverables": [{"name": "Classes", "quantity": 12, "unit": "classes"}],
        **kw,
    }
    res = await client.post("/api/services", json=body, headers=headers)
    assert res.status_code == 201, res.text
    return res.json()


async def create_client_rec(client: AsyncClient, headers: dict, name: str = "Asha Rao", **kw):
    res = await client.post("/api/clients", json={"name": name, **kw}, headers=headers)
    assert res.status_code == 201, res.text
    return res.json()


async def create_instructor(client: AsyncClient, headers: dict, name: str = "Meera", **kw):
    res = await client.post("/api/instructors", json={"name": name, **kw}, headers=headers)
    assert res.status_code == 201, res.text
    return res.json()


async def create_location(client: AsyncClient, headers: dict, code: str = "LOC-1", **kw):
    body = {"name": "Main Studio", "code": code, "capacity_per_batch": 10, **kw}
    res = await client.post("/api/locations", json=body, headers=headers)
    assert res.status_code == 201, res.text
    return res.json()


async def create_batch(
    client: AsyncClient,
    headers: dict,
    location_id: str,
    instructor_id: str,
    code: str = "B-1",
    **kw,
):
    body = {
        "name": "Morning Batch",
        "code": code,
        "status": "active",
        "location_id": location_id,
        "instructor_id": instructor_id,
        "start_date": str(date.today()),
        **kw,
    }
    res = await client.post("/api/batches", json=body, headers=headers)
    assert res.status_code == 201, res.text
    return res.json()
