"""Client joining_date and description round-trip through create/read/update."""

from tests.conftest import create_client_rec


async def test_joining_date_and_description_on_create(client, headers_a):
    rec = await create_client_rec(
        client, headers_a, name="Neha",
        joining_date="2026-01-15", description="Prefers morning batches.",
    )
    assert rec["joining_date"] == "2026-01-15"
    assert rec["description"] == "Prefers morning batches."

    got = (await client.get(f"/api/clients/{rec['id']}", headers=headers_a)).json()
    assert got["joining_date"] == "2026-01-15"
    assert got["description"] == "Prefers morning batches."


async def test_joining_date_optional(client, headers_a):
    rec = await create_client_rec(client, headers_a, name="No Join Date")
    assert rec["joining_date"] is None


async def test_update_joining_date(client, headers_a):
    rec = await create_client_rec(client, headers_a, name="Later")
    res = await client.patch(
        f"/api/clients/{rec['id']}", json={"joining_date": "2026-03-01"}, headers=headers_a
    )
    assert res.status_code == 200
    assert res.json()["joining_date"] == "2026-03-01"
