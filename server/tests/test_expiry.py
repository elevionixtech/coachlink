"""Platform subscription expiry (§5.7): enforced at login, per-request, member mgmt;
superadmin never blocked; renewal restores instantly; no plan ≠ blocked."""

from tests.conftest import auth_headers, login


async def _make_plan(client, headers_root, name="Basic", days=30):
    res = await client.post(
        "/api/admin/plans",
        json={"name": name, "amount": "999", "no_of_days": days},
        headers=headers_root,
    )
    assert res.status_code == 201, res.text
    return res.json()


async def _assign(client, headers_root, org_id, plan_id, starts_on=None):
    body = {"plan_id": plan_id}
    if starts_on:
        body["starts_on"] = starts_on
    res = await client.post(
        f"/api/admin/organisations/{org_id}/plan", json=body, headers=headers_root
    )
    assert res.status_code == 200, res.text
    return res.json()


async def test_no_plan_is_not_blocked(client, seed, headers_a):
    res = await client.get("/api/clients", headers=headers_a)
    assert res.status_code == 200


async def test_expired_org_blocks_login_and_existing_tokens(client, seed, headers_root):
    org_a_id = str(seed["org_a"].id)
    headers_a = await auth_headers(client, "ORGA", "admin-a")
    plan = await _make_plan(client, headers_root, days=30)

    # Assign a plan that already lapsed (started 60 days before a 30-day plan runs out).
    from datetime import date, timedelta

    starts = str(date.today() - timedelta(days=60))
    out = await _assign(client, headers_root, org_a_id, plan["id"], starts_on=starts)
    assert out["subscription_state"] == "expired"

    # (1) login blocked, naming the org and expiry date
    res = await login(client, "ORGA", "admin-a")
    assert res.status_code == 403
    assert "Studio A" in res.json()["detail"]

    # (2) tokens issued before the lapse stop working immediately
    res = await client.get("/api/clients", headers=headers_a)
    assert res.status_code == 403

    # (3) org's own admin blocked from member management
    res = await client.get(f"/api/organisations/{org_a_id}/members", headers=headers_a)
    assert res.status_code == 403

    # Superadmin is never blocked — that is how renewal happens.
    res = await client.get(f"/api/organisations/{org_a_id}/members", headers=headers_root)
    assert res.status_code == 200

    # Renewal restores access instantly with no re-login.
    await _assign(client, headers_root, org_a_id, plan["id"])
    assert (await client.get("/api/clients", headers=headers_a)).status_code == 200
    assert (await login(client, "ORGA", "admin-a")).status_code == 200

    # Other org untouched throughout.
    headers_b = await auth_headers(client, "ORGB", "admin-b")
    assert (await client.get("/api/clients", headers=headers_b)).status_code == 200


async def test_plan_delete_blocked_while_in_use(client, seed, headers_root):
    org_a_id = str(seed["org_a"].id)
    plan = await _make_plan(client, headers_root, name="Deletable")
    await _assign(client, headers_root, org_a_id, plan["id"])
    res = await client.delete(f"/api/admin/plans/{plan['id']}", headers=headers_root)
    assert res.status_code == 409
    assert "In use by 1" in res.json()["detail"]


async def test_plan_name_unique_case_insensitive(client, seed, headers_root):
    await _make_plan(client, headers_root, name="Gold")
    res = await client.post(
        "/api/admin/plans",
        json={"name": "gold", "amount": "1", "no_of_days": 1},
        headers=headers_root,
    )
    assert res.status_code == 409


async def test_create_org_flow(client, seed, headers_root):
    res = await client.post(
        "/api/admin/organisations",
        json={
            "name": "New Studio",
            "code": "newst",
            "admin": {
                "name": "First",
                "username": "first",
                "password": "pass1234",
                "role": "staff",
            },
        },
        headers=headers_root,
    )
    assert res.status_code == 201
    body = res.json()
    assert body["code"] == "NEWST"  # stored uppercase
    assert body["member_count"] == 1

    # First user's role is forced admin regardless of payload.
    headers_new = await auth_headers(client, "NEWST", "first")
    me = (await client.get("/api/me", headers=headers_new)).json()
    assert me["role"] == "admin"

    # Reserved code can never be claimed.
    res = await client.post(
        "/api/admin/organisations",
        json={
            "name": "Evil",
            "code": "PLATFORM",
            "admin": {"name": "E", "username": "e", "password": "pass1234", "role": "admin"},
        },
        headers=headers_root,
    )
    assert res.status_code == 422
