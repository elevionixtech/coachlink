"""Organisation billing identity (§3.9) — admin-editable, printed on every invoice."""

from datetime import date

from tests.conftest import create_client_rec, create_service

DETAILS = {
    "address": "4th Floor, 22 Residency Road\nBengaluru 560025",
    "billing_email": "accounts@aura.example",
    "phone": "+91 80 4123 5566",
    "gstin": "29ABCDE1234F1Z5",
    "upi_id": "aura@okhdfcbank",
    "bank_account_name": "Aura Yoga Studio",
    "bank_account_number": "50100123456789",
    "bank_ifsc": "HDFC0001234",
    "bank_name": "HDFC Bank",
    "show_payment_qr": True,
}


async def test_admin_can_set_billing_details(client, headers_a):
    res = await client.patch("/api/org", json=DETAILS, headers=headers_a)
    assert res.status_code == 200, res.text
    body = res.json()
    for key, value in DETAILS.items():
        assert body[key] == value

    # And they persist on the next read.
    res = await client.get("/api/org", headers=headers_a)
    assert res.json()["gstin"] == DETAILS["gstin"]


async def test_staff_cannot_edit_billing_details(client, headers_a_staff):
    res = await client.patch("/api/org", json=DETAILS, headers=headers_a_staff)
    assert res.status_code == 403


async def test_billing_details_are_org_scoped(client, headers_a, headers_b):
    await client.patch("/api/org", json=DETAILS, headers=headers_a)
    other = await client.get("/api/org", headers=headers_b)
    assert other.json()["gstin"] is None


async def test_invoice_document_shows_the_billing_details(client, headers_a):
    await client.patch("/api/org", json=DETAILS, headers=headers_a)
    svc = await create_service(client, headers_a, sku="ORGB", rate="3000")
    rec = await create_client_rec(client, headers_a)
    await client.post(
        f"/api/clients/{rec['id']}/subscriptions",
        json={"service_id": svc["id"], "start_date": str(date(2026, 6, 1))},
        headers=headers_a,
    )
    await client.post("/api/invoices/generate-missing", json={}, headers=headers_a)
    inv = (await client.get("/api/invoices", headers=headers_a)).json()["items"][0]

    doc = (await client.get(f"/api/invoices/{inv['id']}", headers=headers_a)).json()
    assert doc["issued_by"]["address"] == DETAILS["address"]
    assert doc["issued_by"]["email"] == DETAILS["billing_email"]
    assert doc["issued_by"]["gstin"] == DETAILS["gstin"]
    assert doc["issued_by"]["phone"] == DETAILS["phone"]


async def test_invoice_document_carries_payment_details(client, headers_a):
    await client.patch("/api/org", json=DETAILS, headers=headers_a)
    svc = await create_service(client, headers_a, sku="PAYQR", rate="3000")
    rec = await create_client_rec(client, headers_a)
    await client.post(
        f"/api/clients/{rec['id']}/subscriptions",
        json={"service_id": svc["id"], "start_date": str(date(2026, 6, 1))},
        headers=headers_a,
    )
    await client.post("/api/invoices/generate-missing", json={}, headers=headers_a)
    inv = (await client.get("/api/invoices", headers=headers_a)).json()["items"][0]

    doc = (await client.get(f"/api/invoices/{inv['id']}", headers=headers_a)).json()
    pay = doc["payment"]
    assert pay["upi_id"] == "aura@okhdfcbank"
    assert pay["bank_account_number"] == "50100123456789"
    assert pay["bank_ifsc"] == "HDFC0001234"
    assert pay["show_qr"] is True


async def test_show_payment_qr_can_be_disabled(client, headers_a):
    res = await client.patch("/api/org", json={"show_payment_qr": False}, headers=headers_a)
    assert res.status_code == 200
    assert res.json()["show_payment_qr"] is False
