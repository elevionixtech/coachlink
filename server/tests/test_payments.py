"""Marking an invoice paid with an actual amount (§3.8): settle short/over, or carry
the difference onto the subscription's next invoice."""

from datetime import date

from tests.conftest import create_client_rec, create_service


async def _setup(client, headers, sku, rate="3000", start=date(2026, 5, 1)):
    svc = await create_service(client, headers, sku=sku, rate=rate)
    rec = await create_client_rec(client, headers)
    sub = await client.post(
        f"/api/clients/{rec['id']}/subscriptions",
        json={"service_id": svc["id"], "start_date": str(start)},
        headers=headers,
    )
    await client.post("/api/invoices/generate-missing", json={}, headers=headers)
    return rec, sub.json()


async def _invoices(client, headers):
    res = await client.get("/api/invoices", headers=headers)
    return sorted(res.json()["items"], key=lambda i: i["period_start"])


async def _carry_balance(client, headers, client_id):
    subs = (await client.get(f"/api/clients/{client_id}/subscriptions", headers=headers)).json()
    return subs[0]["carry_balance"]


async def test_paid_in_full_records_the_amount(client, headers_a):
    await _setup(client, headers_a, "PAY1")
    inv = (await _invoices(client, headers_a))[0]
    # No paid_amount given == paid in full.
    res = await client.patch(f"/api/invoices/{inv['id']}", json={"status": "paid"}, headers=headers_a)
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["status"] == "paid"
    assert body["paid_amount"] == inv["amount"]
    assert body["difference_carried"] is False


async def test_settle_short_closes_the_invoice(client, headers_a):
    """Underpay and settle: invoice is paid, shortfall forgiven, nothing carried."""
    rec, _ = await _setup(client, headers_a, "PAY2")
    inv = (await _invoices(client, headers_a))[0]
    res = await client.patch(
        f"/api/invoices/{inv['id']}",
        json={"status": "paid", "paid_amount": "2500", "carry_forward": False},
        headers=headers_a,
    )
    assert res.status_code == 200
    assert res.json()["status"] == "paid"
    assert res.json()["paid_amount"] == "2500.00"
    assert res.json()["difference_carried"] is False  # settled, not carried

    # Next generated invoice is unaffected — still the base rate.
    await client.post("/api/invoices/generate-missing", json={}, headers=headers_a)
    later = (await _invoices(client, headers_a))[-1]
    assert later["amount"] == "3000.00"


async def test_carry_short_adds_to_the_next_invoice(client, headers_a):
    """Underpay 2700 of 3000 and carry: the 300 shortfall lands on the next new invoice.
    A new invoice only appears when time advances or a period is re-issued, so void the
    latest to force a regeneration and watch the carry apply."""
    rec, _ = await _setup(client, headers_a, "PAY3")
    invs = await _invoices(client, headers_a)
    pay = await client.patch(
        f"/api/invoices/{invs[0]['id']}",
        json={"status": "paid", "paid_amount": "2700", "carry_forward": True},
        headers=headers_a,
    )
    assert pay.json()["difference_carried"] is True
    assert await _carry_balance(client, headers_a, rec["id"]) == "300.00"

    # Void the latest period and regenerate it — the fresh invoice absorbs the +300.
    await client.patch(f"/api/invoices/{invs[-1]['id']}", json={"status": "void"}, headers=headers_a)
    await client.post("/api/invoices/generate-missing", json={}, headers=headers_a)
    live = [i for i in await _invoices(client, headers_a) if i["status"] != "void"]
    assert any(i["amount"] == "3300.00" for i in live)
    assert await _carry_balance(client, headers_a, rec["id"]) == "0.00"


async def test_carry_over_credits_the_next_invoice(client, headers_a):
    """Overpay 3500 of 3000 and carry: the 500 credit reduces the next new invoice."""
    rec, _ = await _setup(client, headers_a, "PAY4")
    invs = await _invoices(client, headers_a)
    await client.patch(
        f"/api/invoices/{invs[0]['id']}",
        json={"status": "paid", "paid_amount": "3500", "carry_forward": True},
        headers=headers_a,
    )
    assert await _carry_balance(client, headers_a, rec["id"]) == "-500.00"

    await client.patch(f"/api/invoices/{invs[-1]['id']}", json={"status": "void"}, headers=headers_a)
    await client.post("/api/invoices/generate-missing", json={}, headers=headers_a)
    live = [i for i in await _invoices(client, headers_a) if i["status"] != "void"]
    assert any(i["amount"] == "2500.00" for i in live)


async def test_credit_larger_than_one_invoice_rolls_forward(client, headers_a):
    """A 7000 credit on a 3000 plan zeroes two invoices, remainder rolling forward."""
    rec, _ = await _setup(client, headers_a, "PAY5", start=date(2026, 4, 1))
    invs = await _invoices(client, headers_a)
    # Overpay the first by 7000 (pay 10000), carry the credit.
    await client.patch(
        f"/api/invoices/{invs[0]['id']}",
        json={"status": "paid", "paid_amount": "10000", "carry_forward": True},
        headers=headers_a,
    )
    assert await _carry_balance(client, headers_a, rec["id"]) == "-7000.00"

    # Free two later periods and regenerate — each absorbs credit down to zero.
    for i in invs[1:3]:
        await client.patch(f"/api/invoices/{i['id']}", json={"status": "void"}, headers=headers_a)
    await client.post("/api/invoices/generate-missing", json={}, headers=headers_a)
    live = [i for i in await _invoices(client, headers_a) if i["status"] != "void"]
    assert [i["amount"] for i in live].count("0.00") >= 2
    # 7000 - 3000 - 3000 = 1000 credit still parked.
    assert await _carry_balance(client, headers_a, rec["id"]) == "-1000.00"


async def test_carry_forbidden_when_subscription_ended(client, headers_a):
    """No future invoice to carry to — the API forces a settle."""
    rec, sub = await _setup(client, headers_a, "PAY6")
    await client.patch(f"/api/subscriptions/{sub['id']}", json={"status": "ended"}, headers=headers_a)
    inv = (await _invoices(client, headers_a))[0]
    res = await client.patch(
        f"/api/invoices/{inv['id']}",
        json={"status": "paid", "paid_amount": "2500", "carry_forward": True},
        headers=headers_a,
    )
    assert res.status_code == 422
    assert "settle it instead" in res.json()["detail"]


async def test_can_carry_forward_flag_tracks_subscription(client, headers_a):
    rec, sub = await _setup(client, headers_a, "PAY7")
    inv = (await _invoices(client, headers_a))[0]
    assert inv["can_carry_forward"] is True
    await client.patch(f"/api/subscriptions/{sub['id']}", json={"status": "ended"}, headers=headers_a)
    inv = (await _invoices(client, headers_a))[0]
    assert inv["can_carry_forward"] is False
