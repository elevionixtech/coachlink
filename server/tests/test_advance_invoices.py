"""Advance billing (§5.2): generate the next upcoming invoice(s) for a client's active
subscriptions, ahead of the automatic schedule."""

from datetime import date

from tests.conftest import create_client_rec, create_service


async def _sub(client, headers, cid, svc_id, start, discount="0"):
    res = await client.post(
        f"/api/clients/{cid}/subscriptions",
        json={"service_id": svc_id, "start_date": str(start), "discount_pct": discount},
        headers=headers,
    )
    assert res.status_code == 201, res.text


async def _invoices(client, headers, cid):
    return (await client.get(f"/api/clients/{cid}/invoices", headers=headers)).json()


async def _advance(client, headers, cid, periods=1):
    return await client.post(
        f"/api/clients/{cid}/invoices/advance", json={"periods": periods}, headers=headers
    )


async def test_advance_generates_next_future_period(client, headers_a):
    svc = await create_service(client, headers_a, sku="ADV", rate="3000")
    rec = await create_client_rec(client, headers_a)
    await _sub(client, headers_a, rec["id"], svc["id"], date(2026, 6, 1))
    await client.post("/api/invoices/generate-missing", json={}, headers=headers_a)
    before = await _invoices(client, headers_a, rec["id"])
    latest_start = max(i["period_start"] for i in before)

    res = await _advance(client, headers_a, rec["id"], 1)
    assert res.status_code == 200
    assert res.json()["created"] == 1
    after = await _invoices(client, headers_a, rec["id"])
    assert len(after) == len(before) + 1
    assert max(i["period_start"] for i in after) > latest_start  # a future period


async def test_advance_multiple_periods(client, headers_a):
    svc = await create_service(client, headers_a, sku="ADV3", rate="3000")
    rec = await create_client_rec(client, headers_a)
    await _sub(client, headers_a, rec["id"], svc["id"], date(2026, 6, 1))
    await client.post("/api/invoices/generate-missing", json={}, headers=headers_a)
    before = len(await _invoices(client, headers_a, rec["id"]))

    assert (await _advance(client, headers_a, rec["id"], 3)).json()["created"] == 3
    assert len(await _invoices(client, headers_a, rec["id"])) == before + 3


async def test_advance_then_generate_missing_does_not_duplicate(client, headers_a):
    svc = await create_service(client, headers_a, sku="ADVN", rate="3000")
    rec = await create_client_rec(client, headers_a)
    await _sub(client, headers_a, rec["id"], svc["id"], date(2026, 6, 1))
    await client.post("/api/invoices/generate-missing", json={}, headers=headers_a)
    await _advance(client, headers_a, rec["id"], 2)
    n = len(await _invoices(client, headers_a, rec["id"]))

    res = await client.post("/api/invoices/generate-missing", json={}, headers=headers_a)
    assert res.json()["created"] == 0  # advanced future periods aren't re-created
    assert len(await _invoices(client, headers_a, rec["id"])) == n


async def test_advance_applies_the_discount(client, headers_a):
    svc = await create_service(client, headers_a, sku="ADVD", rate="4000")
    rec = await create_client_rec(client, headers_a)
    await _sub(client, headers_a, rec["id"], svc["id"], date(2026, 6, 1), discount="25")
    await client.post("/api/invoices/generate-missing", json={}, headers=headers_a)
    await _advance(client, headers_a, rec["id"], 1)
    fut = max(await _invoices(client, headers_a, rec["id"]), key=lambda i: i["period_start"])
    assert fut["amount"] == "3000.00"    # 25% off 4000
    assert fut["subtotal"] == "4000.00"  # discount is visible on the advance invoice too


async def test_advance_on_one_time_service_creates_nothing(client, headers_a):
    svc = await create_service(client, headers_a, sku="ADV1T", rate="3000", billing_interval="N/A")
    rec = await create_client_rec(client, headers_a)
    await _sub(client, headers_a, rec["id"], svc["id"], date(2026, 6, 1))
    await client.post("/api/invoices/generate-missing", json={}, headers=headers_a)
    res = await _advance(client, headers_a, rec["id"], 2)
    assert res.json()["created"] == 0  # a one-time service has no upcoming period


async def test_advance_is_org_scoped(client, headers_a, headers_b):
    rec_b = await create_client_rec(client, headers_b)
    assert (await _advance(client, headers_a, rec_b["id"], 1)).status_code == 404
