"""Marking paid captures payment date and method, defaulting to today by UPI (§3.8)."""

from datetime import date

from tests.conftest import create_client_rec, create_service


async def _due_invoice(client, headers):
    svc = await create_service(client, headers, sku="PC", rate="3000")
    rec = await create_client_rec(client, headers)
    await client.post(
        f"/api/clients/{rec['id']}/subscriptions",
        json={"service_id": svc["id"], "start_date": str(date(2026, 6, 1))},
        headers=headers,
    )
    await client.post("/api/invoices/generate-missing", json={}, headers=headers)
    return (await client.get("/api/invoices", headers=headers)).json()["items"][0]


async def test_defaults_today_and_upi(client, headers_a):
    inv = await _due_invoice(client, headers_a)
    res = await client.patch(f"/api/invoices/{inv['id']}", json={"status": "paid"}, headers=headers_a)
    assert res.status_code == 200
    body = res.json()
    assert body["payment_date"] == date.today().isoformat()
    assert body["payment_method"] == "UPI"


async def test_explicit_date_and_method(client, headers_a):
    inv = await _due_invoice(client, headers_a)
    res = await client.patch(
        f"/api/invoices/{inv['id']}",
        json={"status": "paid", "payment_date": "2026-07-15", "payment_method": "Cash"},
        headers=headers_a,
    )
    assert res.status_code == 200
    assert res.json()["payment_date"] == "2026-07-15"
    assert res.json()["payment_method"] == "Cash"


async def test_invalid_method_rejected(client, headers_a):
    inv = await _due_invoice(client, headers_a)
    res = await client.patch(
        f"/api/invoices/{inv['id']}",
        json={"status": "paid", "payment_method": "Bitcoin"},
        headers=headers_a,
    )
    assert res.status_code == 422


async def test_unpaid_invoice_has_no_payment_info(client, headers_a):
    inv = await _due_invoice(client, headers_a)
    assert inv["payment_date"] is None
    assert inv["payment_method"] is None
