"""Login matrix (§5.6): wrong code fails, code case-insensitive, reserved code only
matches platform accounts, generic error never reveals which part was wrong."""

from tests.conftest import auth_headers, login

GENERIC = "Invalid organisation code, username or password"


async def test_valid_login_returns_tokens_and_user(client, seed):
    res = await login(client, "ORGA", "admin-a")
    assert res.status_code == 200
    body = res.json()
    assert body["access_token"] and body["refresh_token"]
    assert body["user"]["role"] == "admin"
    assert body["user"]["org"]["code"] == "ORGA"


async def test_org_code_case_insensitive(client, seed):
    assert (await login(client, "orga", "admin-a")).status_code == 200


async def test_wrong_code_wrong_user_wrong_password_all_generic(client, seed):
    for code, user, pw in [
        ("NOPE", "admin-a", "pass1234"),
        ("ORGA", "nobody", "pass1234"),
        ("ORGA", "admin-a", "wrong"),
        ("ORGB", "admin-a", "pass1234"),  # right user, wrong org
    ]:
        res = await client.post(
            "/api/login", json={"org_code": code, "username": user, "password": pw}
        )
        assert res.status_code == 401, (code, user)
        assert res.json()["detail"] == GENERIC


async def test_platform_code_only_matches_platform_accounts(client, seed):
    assert (await login(client, "PLATFORM", "root")).status_code == 200
    # An org user cannot log in through the reserved code.
    assert (await login(client, "PLATFORM", "admin-a")).status_code == 401


async def test_refresh_rotates_tokens(client, seed):
    body = (await login(client, "ORGA", "admin-a")).json()
    res = await client.post("/api/refresh", json={"refresh_token": body["refresh_token"]})
    assert res.status_code == 200
    assert res.json()["access_token"]
    # An access token is not accepted as a refresh token.
    res = await client.post("/api/refresh", json={"refresh_token": body["access_token"]})
    assert res.status_code == 401


async def test_me_returns_current_user(client, seed):
    headers = await auth_headers(client, "ORGA", "staff-a")
    res = await client.get("/api/me", headers=headers)
    assert res.status_code == 200
    assert res.json()["username"] == "staff-a"


async def test_domain_api_requires_auth(client, seed):
    assert (await client.get("/api/clients")).status_code == 401
    assert (
        await client.get("/api/clients", headers={"Authorization": "Bearer bogus"})
    ).status_code == 401
