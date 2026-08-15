"""GSTIN and company fields are general client fields — available to any client
and shown on invoices."""

from datetime import date

from tests.conftest import create_client_rec, create_service


async def test_client_keeps_gstin(client, headers_a):
    rec = await create_client_rec(
        client, headers_a, name="Freelancer", gstin="29ABCDE1234F1Z5",
    )
    assert rec["gstin"] == "29ABCDE1234F1Z5"
    got = (await client.get(f"/api/clients/{rec['id']}", headers=headers_a)).json()
    assert got["gstin"] == "29ABCDE1234F1Z5"


async def test_client_gstin_appears_on_invoice(client, headers_a):
    rec = await create_client_rec(client, headers_a, gstin="29ABCDE1234F1Z5")
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


async def test_company_and_gstin_fields_persist(client, headers_a):
    """Company name/contact and GSTIN are plain fields any client can carry; an
    unrelated edit leaves them untouched."""
    rec = await create_client_rec(
        client, headers_a, company_name="Acme", gstin="29ABCDE1234F1Z5",
        company_contact="Ravi",
    )
    res = await client.patch(
        f"/api/clients/{rec['id']}", json={"work": "Analyst"}, headers=headers_a
    )
    assert res.status_code == 200
    body = res.json()
    assert body["gstin"] == "29ABCDE1234F1Z5"
    assert body["company_name"] == "Acme"
    assert body["company_contact"] == "Ravi"
