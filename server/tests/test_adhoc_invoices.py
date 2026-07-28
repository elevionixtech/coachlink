"""Ad-hoc (one-off) invoices raised directly against a client (§3.8)."""

from tests.conftest import create_client_rec, create_service


async def _adhoc(client, headers, client_id, **kw):
    body = {
        "client_id": client_id,
        "description": kw.pop("description", "One-time workshop fee"),
        "amount": kw.pop("amount", "1500"),
        "issue_date": kw.pop("issue_date", "2026-07-27"),
        **kw,
    }
    return await client.post("/api/invoices", json=body, headers=headers)


async def test_create_adhoc_invoice(client, headers_a):
    rec = await create_client_rec(client, headers_a)
    res = await _adhoc(client, headers_a, rec["id"], description="Diwali workshop", amount="2000")
    assert res.status_code == 201, res.text
    inv = res.json()
    assert inv["description"] == "Diwali workshop"
    assert inv["amount"] == "2000.00"
    assert inv["status"] == "due"
    assert inv["client_id"] == rec["id"]
    assert inv["service_name"] is None  # no subscription behind it


async def test_adhoc_shows_in_client_invoices(client, headers_a):
    rec = await create_client_rec(client, headers_a)
    await _adhoc(client, headers_a, rec["id"])
    invs = (await client.get(f"/api/clients/{rec['id']}/invoices", headers=headers_a)).json()
    assert len(invs) == 1
    assert invs[0]["description"] == "One-time workshop fee"


async def test_adhoc_can_be_paid_and_voided(client, headers_a):
    rec = await create_client_rec(client, headers_a)
    inv = (await _adhoc(client, headers_a, rec["id"])).json()
    paid = await client.patch(f"/api/invoices/{inv['id']}", json={"status": "paid"}, headers=headers_a)
    assert paid.status_code == 200 and paid.json()["status"] == "paid"


async def test_adhoc_does_not_disturb_generation(client, headers_a):
    """An ad-hoc invoice has no subscription, so generate-missing ignores it entirely."""
    svc = await create_service(client, headers_a, sku="ADH", rate="3000")
    rec = await create_client_rec(client, headers_a)
    await client.post(
        f"/api/clients/{rec['id']}/subscriptions",
        json={"service_id": svc["id"], "start_date": "2026-06-01"},
        headers=headers_a,
    )
    await client.post("/api/invoices/generate-missing", json={}, headers=headers_a)
    before = len((await client.get("/api/invoices", headers=headers_a)).json()["items"])
    await _adhoc(client, headers_a, rec["id"])
    # Regeneration must not touch or duplicate anything because of the ad-hoc invoice.
    res = await client.post("/api/invoices/generate-missing", json={}, headers=headers_a)
    assert res.json()["created"] == 0
    after = len((await client.get("/api/invoices", headers=headers_a)).json()["items"])
    assert after == before + 1  # only the ad-hoc one was added


async def test_multiple_adhoc_invoices_do_not_collide(client, headers_a):
    """NULL subscription_id must not trip the one-per-period unique index."""
    rec = await create_client_rec(client, headers_a)
    for i in range(3):
        res = await _adhoc(client, headers_a, rec["id"], description=f"Item {i}", issue_date="2026-07-27")
        assert res.status_code == 201, res.text


async def test_adhoc_requires_positive_amount(client, headers_a):
    rec = await create_client_rec(client, headers_a)
    res = await _adhoc(client, headers_a, rec["id"], amount="0")
    assert res.status_code == 422


async def test_adhoc_client_must_be_owned(client, headers_a, headers_b):
    rec_b = await create_client_rec(client, headers_b)
    res = await _adhoc(client, headers_a, rec_b["id"])
    assert res.status_code == 404


# ---------------------------------------------------------------- non-client


async def test_adhoc_invoice_to_a_non_client(client, headers_a):
    """Raise an invoice against someone with no client record — a name is entered."""
    res = await client.post(
        "/api/invoices",
        json={
            "bill_to_name": "Walk-in Ravi",
            "bill_to_email": "ravi@example.com",
            "description": "Guest drop-in class",
            "amount": "500",
            "issue_date": "2026-07-27",
        },
        headers=headers_a,
    )
    assert res.status_code == 201, res.text
    inv = res.json()
    assert inv["client_id"] is None
    assert inv["client_name"] == "Walk-in Ravi"  # falls back to bill_to_name

    # It appears in the org's invoice list and the document names the recipient.
    listed = (await client.get("/api/invoices", headers=headers_a)).json()["items"]
    assert any(i["id"] == inv["id"] for i in listed)
    doc = (await client.get(f"/api/invoices/{inv['id']}", headers=headers_a)).json()
    assert doc["bill_to"]["name"] == "Walk-in Ravi"
    assert doc["bill_to"]["email"] == "ravi@example.com"


async def test_adhoc_requires_exactly_one_recipient(client, headers_a):
    rec = await create_client_rec(client, headers_a)
    # both client and name -> rejected
    both = await client.post(
        "/api/invoices",
        json={"client_id": rec["id"], "bill_to_name": "X", "description": "d",
              "amount": "1", "issue_date": "2026-07-27"},
        headers=headers_a,
    )
    assert both.status_code == 422
    # neither -> rejected
    neither = await client.post(
        "/api/invoices",
        json={"description": "d", "amount": "1", "issue_date": "2026-07-27"},
        headers=headers_a,
    )
    assert neither.status_code == 422


async def test_non_client_invoice_is_org_scoped(client, headers_a, headers_b):
    res = await client.post(
        "/api/invoices",
        json={"bill_to_name": "A's Guest", "description": "d", "amount": "100",
              "issue_date": "2026-07-27"},
        headers=headers_a,
    )
    inv_id = res.json()["id"]
    # Org B must not see or touch it.
    assert (await client.get(f"/api/invoices/{inv_id}", headers=headers_b)).status_code == 404
    b_list = (await client.get("/api/invoices", headers=headers_b)).json()["items"]
    assert all(i["id"] != inv_id for i in b_list)


async def test_non_client_invoice_carries_gstin(client, headers_a):
    res = await client.post(
        "/api/invoices",
        json={
            "bill_to_name": "Acme Corp", "bill_to_gstin": "29ABCDE1234F1Z5",
            "description": "Corporate workshop", "amount": "10000", "issue_date": "2026-07-27",
        },
        headers=headers_a,
    )
    assert res.status_code == 201, res.text
    doc = (await client.get(f"/api/invoices/{res.json()['id']}", headers=headers_a)).json()
    assert doc["bill_to"]["name"] == "Acme Corp"
    assert doc["bill_to"]["gstin"] == "29ABCDE1234F1Z5"


# ---------------------------------------------------------------- editing


async def test_edit_adhoc_invoice(client, headers_a):
    rec = await create_client_rec(client, headers_a)
    inv = (await _adhoc(client, headers_a, rec["id"], description="Old", amount="500")).json()
    res = await client.put(
        f"/api/invoices/{inv['id']}",
        json={"client_id": rec["id"], "description": "Corrected", "amount": "750",
              "issue_date": "2026-08-01"},
        headers=headers_a,
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["description"] == "Corrected"
    assert body["amount"] == "750.00"
    assert body["issue_date"] == "2026-08-01"


async def test_edit_can_switch_to_non_client(client, headers_a):
    rec = await create_client_rec(client, headers_a)
    inv = (await _adhoc(client, headers_a, rec["id"])).json()
    res = await client.put(
        f"/api/invoices/{inv['id']}",
        json={"bill_to_name": "Walk-in", "bill_to_gstin": "29ABCDE1234F1Z5",
              "description": "Guest", "amount": "300", "issue_date": "2026-07-27"},
        headers=headers_a,
    )
    assert res.status_code == 200
    assert res.json()["client_id"] is None
    assert res.json()["client_name"] == "Walk-in"


async def test_cannot_edit_a_subscription_invoice(client, headers_a):
    svc = await create_service(client, headers_a, sku="ADH-SUB", rate="3000")
    rec = await create_client_rec(client, headers_a)
    await client.post(
        f"/api/clients/{rec['id']}/subscriptions",
        json={"service_id": svc["id"], "start_date": "2026-06-01"},
        headers=headers_a,
    )
    await client.post("/api/invoices/generate-missing", json={}, headers=headers_a)
    inv = (await client.get("/api/invoices", headers=headers_a)).json()["items"][0]
    res = await client.put(
        f"/api/invoices/{inv['id']}",
        json={"client_id": rec["id"], "description": "hack", "amount": "1",
              "issue_date": "2026-07-27"},
        headers=headers_a,
    )
    assert res.status_code == 422
    assert "subscription invoice" in res.json()["detail"]


async def test_cannot_edit_a_paid_invoice(client, headers_a):
    rec = await create_client_rec(client, headers_a)
    inv = (await _adhoc(client, headers_a, rec["id"])).json()
    await client.patch(f"/api/invoices/{inv['id']}", json={"status": "paid"}, headers=headers_a)
    res = await client.put(
        f"/api/invoices/{inv['id']}",
        json={"client_id": rec["id"], "description": "x", "amount": "1",
              "issue_date": "2026-07-27"},
        headers=headers_a,
    )
    assert res.status_code == 422


async def test_edit_invoice_is_org_scoped(client, headers_a, headers_b):
    rec = await create_client_rec(client, headers_a)
    inv = (await _adhoc(client, headers_a, rec["id"])).json()
    res = await client.put(
        f"/api/invoices/{inv['id']}",
        json={"bill_to_name": "X", "description": "x", "amount": "1", "issue_date": "2026-07-27"},
        headers=headers_b,
    )
    assert res.status_code == 404
