"""Invoice generation (§5.2): idempotent walks, period labels, discounts, overdue."""

from datetime import date
from decimal import Decimal

from app.billing import effective_rate, missing_periods, period_label
from app.models import BillingInterval
from tests.conftest import create_client_rec, create_service


async def _subscribe(client, headers, service, client_rec, start_date, discount="0"):
    res = await client.post(
        f"/api/clients/{client_rec['id']}/subscriptions",
        json={
            "service_id": service["id"],
            "start_date": str(start_date),
            "discount_pct": discount,
        },
        headers=headers,
    )
    assert res.status_code == 201, res.text
    return res.json()


def test_period_labels():
    d = date(2026, 7, 14)
    assert period_label(d, BillingInterval.monthly) == "Jul 2026"
    assert period_label(d, BillingInterval.quarterly) == "Q3 2026"
    assert period_label(d, BillingInterval.weekly) == "Wk of 14 Jul 2026"
    assert period_label(d, BillingInterval.semi_annual) == "H2 2026"
    assert period_label(date(2026, 3, 1), BillingInterval.semi_annual) == "H1 2026"
    assert period_label(d, BillingInterval.annual) == "2026"
    assert period_label(d, BillingInterval.na) == "One-time"


def test_missing_periods_monthly_walk():
    periods = missing_periods(
        date(2026, 4, 10), BillingInterval.monthly, set(), date(2026, 7, 21)
    )
    assert [p[0] for p in periods] == ["Apr 2026", "May 2026", "Jun 2026", "Jul 2026"]
    # Existing labels are skipped — that's the idempotency.
    periods = missing_periods(
        date(2026, 4, 10), BillingInterval.monthly, {"May 2026"}, date(2026, 7, 21)
    )
    assert [p[0] for p in periods] == ["Apr 2026", "Jun 2026", "Jul 2026"]


def test_missing_periods_month_end_clamp():
    periods = missing_periods(
        date(2026, 1, 31), BillingInterval.monthly, set(), date(2026, 4, 30)
    )
    assert [p[1] for p in periods] == [
        date(2026, 1, 31),
        date(2026, 2, 28),
        date(2026, 3, 31),
        date(2026, 4, 30),
    ]


def test_future_start_produces_nothing():
    assert (
        missing_periods(date(2027, 1, 1), BillingInterval.monthly, set(), date(2026, 7, 21))
        == []
    )
    assert missing_periods(date(2027, 1, 1), BillingInterval.na, set(), date(2026, 7, 21)) == []


def test_effective_rate_rounds_to_rupee():
    assert effective_rate(Decimal("3000"), Decimal("10")) == Decimal("2700")
    assert effective_rate(Decimal("999"), Decimal("33.33")) == Decimal("666")  # 666.03
    assert effective_rate(Decimal("100"), Decimal("0.5")) == Decimal("100")  # 99.5 → 100


async def test_generate_missing_is_idempotent(client, headers_a):
    service = await create_service(client, headers_a)  # Monthly, rate 3000
    rec = await create_client_rec(client, headers_a)
    await _subscribe(client, headers_a, service, rec, date(2026, 5, 1), discount="10")

    res = await client.post("/api/invoices/generate-missing", json={}, headers=headers_a)
    assert res.status_code == 200
    first = res.json()["created"]
    assert first >= 3  # May, Jun, Jul at least

    res = await client.post("/api/invoices/generate-missing", json={}, headers=headers_a)
    assert res.json()["created"] == 0  # idempotent

    res = await client.get("/api/invoices", headers=headers_a)
    items = res.json()["items"]
    assert len(items) == first
    assert all(i["amount"] == "2700.00" or i["amount"] == "2700" for i in items)
    assert all(i["status"] == "due" for i in items)
    labels = {i["period_label"] for i in items}
    assert "May 2026" in labels and "Jun 2026" in labels
    # Org-sequential numbers with the org prefix.
    numbers = sorted(i["number"] for i in items)
    assert numbers[0].startswith("INV-2026-")


async def test_one_time_service_generates_single_invoice(client, headers_a):
    service = await create_service(
        client,
        headers_a,
        sku="OT-1",
        billing_interval="N/A",
        service_type="One Time",
        rate="5000",
    )
    rec = await create_client_rec(client, headers_a, name="One Timer")
    await _subscribe(client, headers_a, service, rec, date(2026, 6, 15))

    res = await client.post(
        "/api/invoices/generate-missing", json={"client_id": rec["id"]}, headers=headers_a
    )
    assert res.json()["created"] == 1
    res = await client.get(f"/api/clients/{rec['id']}/invoices", headers=headers_a)
    inv = res.json()[0]
    assert inv["period_label"] == "One-time"
    assert inv["issue_date"] == "2026-06-15"

    # Second run creates nothing.
    res = await client.post("/api/invoices/generate-missing", json={}, headers=headers_a)
    assert res.json()["created"] == 0


async def test_ended_subscription_not_billed(client, headers_a):
    service = await create_service(client, headers_a, sku="END-1")
    rec = await create_client_rec(client, headers_a, name="Ender")
    sub = await _subscribe(client, headers_a, service, rec, date(2026, 6, 1))
    res = await client.patch(
        f"/api/subscriptions/{sub['id']}", json={"status": "ended"}, headers=headers_a
    )
    assert res.status_code == 200
    res = await client.post("/api/invoices/generate-missing", json={}, headers=headers_a)
    assert res.json()["created"] == 0


async def test_mark_paid_void_and_overdue_filters(client, headers_a):
    service = await create_service(client, headers_a, sku="PAID-1")
    rec = await create_client_rec(client, headers_a, name="Payer")
    await _subscribe(client, headers_a, service, rec, date(2026, 5, 1))
    await client.post("/api/invoices/generate-missing", json={}, headers=headers_a)

    res = await client.get("/api/invoices", headers=headers_a)
    items = res.json()["items"]
    outstanding_before = Decimal(res.json()["outstanding_total"])
    assert outstanding_before > 0

    # Old invoices (issue_date + 7d grace < today) derive as overdue.
    may = next(i for i in items if i["period_label"] == "May 2026")
    assert may["overdue"] is True

    res = await client.patch(
        f"/api/invoices/{may['id']}", json={"status": "paid"}, headers=headers_a
    )
    assert res.status_code == 200 and res.json()["status"] == "paid"

    res = await client.get("/api/invoices?status=paid", headers=headers_a)
    assert {i["id"] for i in res.json()["items"]} == {may["id"]}
    res = await client.get("/api/invoices?status=overdue", headers=headers_a)
    assert may["id"] not in {i["id"] for i in res.json()["items"]}

    # Reverting to 'due' is rejected.
    res = await client.patch(
        f"/api/invoices/{may['id']}", json={"status": "due"}, headers=headers_a
    )
    assert res.status_code == 422


async def test_invoices_isolated_between_orgs(client, headers_a, headers_b):
    service = await create_service(client, headers_a, sku="ISO-1")
    rec = await create_client_rec(client, headers_a, name="Iso")
    await _subscribe(client, headers_a, service, rec, date(2026, 7, 1))
    await client.post("/api/invoices/generate-missing", json={}, headers=headers_a)

    res = await client.get("/api/invoices", headers=headers_b)
    assert res.json()["items"] == []
    # generate-missing scoped to a foreign client → 404
    res = await client.post(
        "/api/invoices/generate-missing", json={"client_id": rec["id"]}, headers=headers_b
    )
    assert res.status_code == 404

    inv = (await client.get("/api/invoices", headers=headers_a)).json()["items"][0]
    res = await client.patch(
        f"/api/invoices/{inv['id']}", json={"status": "paid"}, headers=headers_b
    )
    assert res.status_code == 404


async def test_subscription_promotes_lifecycle_to_customer(client, headers_a):
    service = await create_service(client, headers_a, sku="LIFE-1")
    rec = await create_client_rec(client, headers_a, name="Leader")
    assert rec["lifecycle_stage"] == "Lead"
    await _subscribe(client, headers_a, service, rec, date(2026, 7, 1))
    res = await client.get(f"/api/clients/{rec['id']}", headers=headers_a)
    assert res.json()["lifecycle_stage"] == "Customer"
