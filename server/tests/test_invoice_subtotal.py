"""Invoices store the pre-discount subtotal so the discount can be shown (§3.7)."""

from datetime import date

from tests.conftest import create_client_rec, create_service


async def test_discounted_invoice_records_subtotal(client, headers_a):
    svc = await create_service(client, headers_a, sku="DISC", rate="3000")
    rec = await create_client_rec(client, headers_a)
    await client.post(
        f"/api/clients/{rec['id']}/subscriptions",
        json={"service_id": svc["id"], "start_date": str(date(2026, 6, 1)), "discount_pct": "10"},
        headers=headers_a,
    )
    await client.post("/api/invoices/generate-missing", json={}, headers=headers_a)
    inv = (await client.get("/api/invoices", headers=headers_a)).json()["items"][0]
    assert inv["subtotal"] == "3000.00"   # undiscounted rate
    assert inv["amount"] == "2700.00"     # 10% off
    # discount is subtotal - amount = 300


async def test_undiscounted_invoice_subtotal_equals_amount(client, headers_a):
    svc = await create_service(client, headers_a, sku="FULL", rate="3000")
    rec = await create_client_rec(client, headers_a)
    await client.post(
        f"/api/clients/{rec['id']}/subscriptions",
        json={"service_id": svc["id"], "start_date": str(date(2026, 6, 1))},
        headers=headers_a,
    )
    await client.post("/api/invoices/generate-missing", json={}, headers=headers_a)
    inv = (await client.get("/api/invoices", headers=headers_a)).json()["items"][0]
    assert inv["subtotal"] == inv["amount"]  # no discount -> no reduction shown


async def test_adhoc_invoice_has_no_subtotal(client, headers_a):
    rec = await create_client_rec(client, headers_a)
    res = await client.post(
        "/api/invoices",
        json={"client_id": rec["id"], "description": "Workshop", "amount": "1500",
              "issue_date": "2026-07-27"},
        headers=headers_a,
    )
    assert res.json()["subtotal"] is None  # no discount concept for a one-off
