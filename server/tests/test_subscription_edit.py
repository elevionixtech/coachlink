"""Editing a subscription's service, discount, or pricing option (§3.7)."""


from tests.conftest import create_client_rec, create_service


async def _create_sub(client, headers, cid, svc_id, **kw):
    body = {"service_id": svc_id, "start_date": "2026-06-01", **kw}
    res = await client.post(f"/api/clients/{cid}/subscriptions", json=body, headers=headers)
    assert res.status_code == 201, res.text
    return res.json()


async def test_edit_discount(client, headers_a):
    svc = await create_service(client, headers_a, sku="SE1", rate="3000")
    rec = await create_client_rec(client, headers_a)
    sub = await _create_sub(client, headers_a, rec["id"], svc["id"], discount_pct="0")
    assert sub["effective_rate"] == "3000"

    res = await client.put(
        f"/api/subscriptions/{sub['id']}",
        json={"service_id": svc["id"], "start_date": "2026-06-01", "discount_pct": "20"},
        headers=headers_a,
    )
    assert res.status_code == 200, res.text
    assert res.json()["discount_pct"] == "20.00"
    assert res.json()["effective_rate"] == "2400"  # 20% off 3000


async def test_edit_switch_service(client, headers_a):
    svc1 = await create_service(client, headers_a, sku="SE2A", rate="3000")
    svc2 = await create_service(client, headers_a, sku="SE2B", rate="5000")
    rec = await create_client_rec(client, headers_a)
    sub = await _create_sub(client, headers_a, rec["id"], svc1["id"])
    res = await client.put(
        f"/api/subscriptions/{sub['id']}",
        json={"service_id": svc2["id"], "start_date": "2026-06-01"},
        headers=headers_a,
    )
    assert res.status_code == 200
    assert res.json()["service_id"] == svc2["id"]
    assert res.json()["rate"] == "5000.00"


async def test_edit_only_affects_future_invoices(client, headers_a):
    """Already-issued invoices keep their amount; editing changes only what's generated next."""
    svc = await create_service(client, headers_a, sku="SE3", rate="3000")
    rec = await create_client_rec(client, headers_a)
    sub = await _create_sub(client, headers_a, rec["id"], svc["id"])
    await client.post("/api/invoices/generate-missing", json={}, headers=headers_a)
    before = (await client.get("/api/invoices", headers=headers_a)).json()["items"]
    assert all(i["amount"] == "3000.00" for i in before)

    # Apply a discount, then advance-bill a new period.
    await client.put(
        f"/api/subscriptions/{sub['id']}",
        json={"service_id": svc["id"], "start_date": "2026-06-01", "discount_pct": "50"},
        headers=headers_a,
    )
    await client.post(f"/api/clients/{rec['id']}/invoices/advance", json={"periods": 1}, headers=headers_a)
    after = (await client.get("/api/invoices", headers=headers_a)).json()["items"]
    # Old invoices unchanged at 3000; the new one is discounted to 1500.
    assert any(i["amount"] == "3000.00" for i in after)
    assert any(i["amount"] == "1500.00" for i in after)


async def test_edit_rejects_ineligible_option(client, headers_a):
    svc = await create_service(client, headers_a, sku="SE4", rate="3000")  # prices no options
    rec = await create_client_rec(client, headers_a)
    sub = await _create_sub(client, headers_a, rec["id"], svc["id"])
    opt = (await client.post("/api/pricing-options", json={"name": "Corp"}, headers=headers_a)).json()
    res = await client.put(
        f"/api/subscriptions/{sub['id']}",
        json={"service_id": svc["id"], "start_date": "2026-06-01", "pricing_option_id": opt["id"]},
        headers=headers_a,
    )
    assert res.status_code == 422  # service has no price for that option


async def test_edit_is_org_scoped(client, headers_a, headers_b):
    svc = await create_service(client, headers_b, sku="SE5", rate="3000")
    rec = await create_client_rec(client, headers_b)
    sub = await _create_sub(client, headers_b, rec["id"], svc["id"])
    res = await client.put(
        f"/api/subscriptions/{sub['id']}",
        json={"service_id": svc["id"], "start_date": "2026-06-01"},
        headers=headers_a,
    )
    assert res.status_code == 404
