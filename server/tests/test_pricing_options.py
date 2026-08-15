"""Configurable pricing options (§3.7): catalog CRUD, per-service pricing,
eligibility, and how an option resolves against subscription.discount_pct."""

from datetime import date

from tests.conftest import (
    create_client_rec,
    create_pricing_option,
    create_service,
)


async def _priced_service(client, headers, option_id, mode, value, rate="3000", sku="SKU-P"):
    return await create_service(
        client,
        headers,
        sku=sku,
        rate=rate,
        pricing_options=[
            {"pricing_option_id": option_id, "pricing_mode": mode, "value": value}
        ],
    )


async def _subscribe(client, headers, service, client_rec, option_id=None, discount="0"):
    body = {
        "service_id": service["id"],
        "start_date": str(date.today()),
        "discount_pct": discount,
    }
    if option_id:
        body["pricing_option_id"] = option_id
    return await client.post(
        f"/api/clients/{client_rec['id']}/subscriptions", json=body, headers=headers
    )


# ---------------------------------------------------------------- catalog


async def test_catalog_is_open_ended(client, headers_a):
    """The whole point: an org configures N options, not a fixed three."""
    for i, name in enumerate(["Corporate Plan", "Family Plan", "Student", "NGO", "Early Bird"]):
        await create_pricing_option(client, headers_a, name=name, sort_order=i)
    res = await client.get("/api/pricing-options", headers=headers_a)
    assert res.status_code == 200
    assert [o["name"] for o in res.json()] == [
        "Corporate Plan", "Family Plan", "Student", "NGO", "Early Bird"
    ]


async def test_duplicate_name_409(client, headers_a):
    await create_pricing_option(client, headers_a, name="Corporate Plan")
    res = await client.post(
        "/api/pricing-options", json={"name": "corporate plan"}, headers=headers_a
    )
    assert res.status_code == 409
    assert "already exists" in res.json()["detail"]


async def test_option_in_use_cannot_be_archived(client, headers_a):
    opt = await create_pricing_option(client, headers_a)
    await _priced_service(client, headers_a, opt["id"], "discount_pct", "20")
    res = await client.delete(f"/api/pricing-options/{opt['id']}", headers=headers_a)
    assert res.status_code == 409
    assert "still price this option" in res.json()["detail"]


# ---------------------------------------------------------------- per-service pricing


async def test_service_prices_each_option_once(client, headers_a):
    opt = await create_pricing_option(client, headers_a)
    res = await client.post(
        "/api/services",
        json={
            "name": "Dup", "sku": "SKU-DUP", "service_type": "Subscription",
            "delivery_mode": "Offline", "billing_interval": "Monthly", "rate": "3000",
            "pricing_options": [
                {"pricing_option_id": opt["id"], "pricing_mode": "discount_pct", "value": "10"},
                {"pricing_option_id": opt["id"], "pricing_mode": "discount_pct", "value": "20"},
            ],
        },
        headers=headers_a,
    )
    assert res.status_code == 422


async def test_discount_pct_over_100_rejected(client, headers_a):
    opt = await create_pricing_option(client, headers_a)
    res = await client.post(
        "/api/services",
        json={
            "name": "Bad", "sku": "SKU-BAD", "service_type": "Subscription",
            "delivery_mode": "Offline", "billing_interval": "Monthly", "rate": "3000",
            "pricing_options": [
                {"pricing_option_id": opt["id"], "pricing_mode": "discount_pct", "value": "150"}
            ],
        },
        headers=headers_a,
    )
    assert res.status_code == 422


async def test_repricing_the_same_option_succeeds(client, headers_a):
    """Regression: replacing the collection re-inserts before deleting, which trips the
    (service_id, pricing_option_id) unique constraint unless the removals flush first."""
    opt = await create_pricing_option(client, headers_a)
    svc = await _priced_service(client, headers_a, opt["id"], "discount_pct", "10")

    res = await client.patch(
        f"/api/services/{svc['id']}",
        json={"pricing_options": [
            {"pricing_option_id": opt["id"], "pricing_mode": "discount_pct", "value": "25"}
        ]},
        headers=headers_a,
    )
    assert res.status_code == 200, res.text
    priced = res.json()["pricing_options"]
    assert len(priced) == 1
    assert priced[0]["value"] == "25.00"


async def test_dropping_an_option_from_a_service(client, headers_a):
    opt = await create_pricing_option(client, headers_a)
    svc = await _priced_service(client, headers_a, opt["id"], "discount_pct", "10")
    res = await client.patch(
        f"/api/services/{svc['id']}", json={"pricing_options": []}, headers=headers_a
    )
    assert res.status_code == 200, res.text
    assert res.json()["pricing_options"] == []


async def test_service_out_shows_resolved_price(client, headers_a):
    opt = await create_pricing_option(client, headers_a)
    svc = await _priced_service(client, headers_a, opt["id"], "discount_pct", "20", rate="3000")
    priced = svc["pricing_options"][0]
    assert priced["option_name"] == "Corporate Plan"
    assert priced["effective_rate"] == "2400"


# ---------------------------------------------------------------- eligibility


async def test_any_client_can_use_any_priced_option(client, headers_a):
    """Options are open to any client — a service's options are available to everyone;
    the operator chooses."""
    opt = await create_pricing_option(client, headers_a)
    svc = await _priced_service(client, headers_a, opt["id"], "discount_pct", "20")

    for name in ("Asha", "Ravi", "Meera"):
        rec = await create_client_rec(client, headers_a, name=name)
        res = await _subscribe(client, headers_a, svc, rec, option_id=opt["id"])
        assert res.status_code == 201, res.text
        assert res.json()["effective_rate"] == "2400"  # 20% off 3000


async def test_option_not_priced_by_service_rejected(client, headers_a):
    opt = await create_pricing_option(client, headers_a)
    plain = await create_service(client, headers_a, sku="SKU-PLAIN")
    rec = await create_client_rec(client, headers_a)
    res = await _subscribe(client, headers_a, plain, rec, option_id=opt["id"])
    assert res.status_code == 422
    assert "no price for" in res.json()["detail"]


# ---------------------------------------------------------------- resolution


async def test_option_wins_over_subscription_discount(client, headers_a):
    """The decision that drives the engine: an option's price wins outright and the
    subscription discount is zeroed, so the two can never silently compound."""
    opt = await create_pricing_option(client, headers_a)
    svc = await _priced_service(client, headers_a, opt["id"], "discount_pct", "20", rate="3000")
    rec = await create_client_rec(client, headers_a)

    res = await _subscribe(client, headers_a, svc, rec, option_id=opt["id"], discount="50")
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["effective_rate"] == "2400"  # 20% off, not 50%, and not both
    assert body["discount_pct"] == "0.00"  # zeroed, never stored-but-ignored


async def test_fixed_rate_ignores_service_rate(client, headers_a):
    opt = await create_pricing_option(client, headers_a, name="Corp Block")
    svc = await _priced_service(client, headers_a, opt["id"], "fixed_rate", "45000", rate="3000")
    rec = await create_client_rec(client, headers_a)
    res = await _subscribe(client, headers_a, svc, rec, option_id=opt["id"])
    assert res.json()["effective_rate"] == "45000"


async def test_no_option_still_uses_discount_pct(client, headers_a):
    """Regression: subscriptions without an option bill exactly as before."""
    svc = await create_service(client, headers_a, sku="SKU-OLD", rate="3000")
    rec = await create_client_rec(client, headers_a)
    res = await _subscribe(client, headers_a, svc, rec, discount="10")
    assert res.json()["effective_rate"] == "2700"


async def test_invoice_uses_option_price(client, headers_a):
    """The resolved price must reach the actual invoice, not just the API response."""
    opt = await create_pricing_option(client, headers_a)
    svc = await _priced_service(client, headers_a, opt["id"], "discount_pct", "20", rate="3000")
    rec = await create_client_rec(client, headers_a)
    await _subscribe(client, headers_a, svc, rec, option_id=opt["id"])

    res = await client.post("/api/invoices/generate-missing", json={}, headers=headers_a)
    assert res.status_code == 200, res.text
    invoices = (await client.get("/api/invoices", headers=headers_a)).json()["items"]
    assert invoices
    assert all(inv["amount"] in ("2400", "2400.00") for inv in invoices)
