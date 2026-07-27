"""GSTIN is a general client field — kept for any account type and shown on invoices."""

from datetime import date

from tests.conftest import create_client_rec, create_service


async def test_individual_client_keeps_gstin(client, headers_a):
    rec = await create_client_rec(
        client, headers_a, name="Freelancer", account_type="Individual",
        gstin="29ABCDE1234F1Z5",
    )
    assert rec["gstin"] == "29ABCDE1234F1Z5"  # not cleared for non-corporate
    got = (await client.get(f"/api/clients/{rec['id']}", headers=headers_a)).json()
    assert got["gstin"] == "29ABCDE1234F1Z5"


async def test_client_gstin_appears_on_invoice(client, headers_a):
    rec = await create_client_rec(
        client, headers_a, account_type="Individual", gstin="29ABCDE1234F1Z5",
    )
    svc = await create_service(client, headers_a, sku="GST", rate="3000")
    await client.post(
        f"/api/clients/{rec['id']}/subscriptions",
        json={"service_id": svc["id"], "start_date": str(date(2026, 6, 1))},
        headers=headers_a,
    )
    await client.post("/api/invoices/generate-missing", json={}, headers=headers_a)
    inv = (await client.get("/api/invoices", headers=headers_a)).json()["items"][0]
    doc = (await client.get(f"/api/invoices/{inv['id']}", headers=headers_a)).json()
    assert doc["bill_to"]["gstin"] == "29ABCDE1234F1Z5"


async def test_switching_away_from_corporate_keeps_gstin_but_clears_company(client, headers_a):
    rec = await create_client_rec(
        client, headers_a, account_type="Corporate",
        company_name="Acme", gstin="29ABCDE1234F1Z5",
    )
    res = await client.patch(
        f"/api/clients/{rec['id']}", json={"account_type": "Individual"}, headers=headers_a
    )
    assert res.status_code == 200
    body = res.json()
    assert body["gstin"] == "29ABCDE1234F1Z5"  # kept
    assert body["company_name"] is None        # company field cleared
