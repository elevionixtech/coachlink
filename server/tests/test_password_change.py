"""Self-service password change (§2)."""

from tests.conftest import PASSWORD, login


async def test_change_password_then_login_with_it(client, headers_a):
    res = await client.post(
        "/api/me/password",
        json={"current_password": PASSWORD, "new_password": "brand-new-pass-9"},
        headers=headers_a,
    )
    assert res.status_code == 204, res.text

    # Old password no longer works, new one does.
    assert (await login(client, "ORGA", "admin-a", PASSWORD)).status_code == 401
    assert (await login(client, "ORGA", "admin-a", "brand-new-pass-9")).status_code == 200


async def test_wrong_current_password_refused(client, headers_a):
    res = await client.post(
        "/api/me/password",
        json={"current_password": "not-it", "new_password": "brand-new-pass-9"},
        headers=headers_a,
    )
    assert res.status_code == 422
    assert "Current password is incorrect" in res.json()["detail"]


async def test_new_password_too_short_refused(client, headers_a):
    res = await client.post(
        "/api/me/password",
        json={"current_password": PASSWORD, "new_password": "short"},
        headers=headers_a,
    )
    assert res.status_code == 422


async def test_new_password_must_differ(client, headers_a):
    res = await client.post(
        "/api/me/password",
        json={"current_password": PASSWORD, "new_password": PASSWORD},
        headers=headers_a,
    )
    assert res.status_code == 422


async def test_requires_authentication(client, seed):
    res = await client.post(
        "/api/me/password",
        json={"current_password": PASSWORD, "new_password": "brand-new-pass-9"},
    )
    assert res.status_code == 401


async def test_superadmin_can_change_own_password(client, headers_root):
    res = await client.post(
        "/api/me/password",
        json={"current_password": PASSWORD, "new_password": "root-new-pass-9"},
        headers=headers_root,
    )
    assert res.status_code == 204, res.text
    assert (await login(client, "PLATFORM", "root", "root-new-pass-9")).status_code == 200
