"""Editable invoice period end (§3.8): extending shifts every later period, and an
untouched subscription keeps its month-end anchor."""

from datetime import date, timedelta

from app.billing import missing_periods
from app.models import BillingInterval
from tests.conftest import create_client_rec, create_service


async def _subscribe(client, headers, service, rec, start):
    res = await client.post(
        f"/api/clients/{rec['id']}/subscriptions",
        json={"service_id": service["id"], "start_date": str(start)},
        headers=headers,
    )
    assert res.status_code == 201, res.text
    return res.json()


async def _invoices(client, headers):
    res = await client.get("/api/invoices", headers=headers)
    return sorted(res.json()["items"], key=lambda i: i["period_start"])


# ---------------------------------------------------------------- unit


def test_periods_carry_start_and_end():
    got = missing_periods(date(2026, 1, 1), BillingInterval.monthly, set(), date(2026, 3, 15))
    assert [(s, e) for _, s, e in got] == [
        (date(2026, 1, 1), date(2026, 1, 31)),
        (date(2026, 2, 1), date(2026, 2, 28)),
        (date(2026, 3, 1), date(2026, 3, 31)),
    ]


def test_month_end_anchor_still_does_not_drift():
    """The bug the anchoring was written for: Jan 31 must not decay to the 28th."""
    got = missing_periods(date(2026, 1, 31), BillingInterval.monthly, set(), date(2026, 5, 1))
    assert [s for _, s, _ in got] == [
        date(2026, 1, 31), date(2026, 2, 28), date(2026, 3, 31), date(2026, 4, 30),
    ]


def test_covered_ranges_suppress_swallowed_periods():
    """An extension reaching into March must not re-bill February or March."""
    got = missing_periods(
        date(2026, 1, 1), BillingInterval.monthly, set(), date(2026, 4, 15),
        covered=[(date(2026, 1, 1), date(2026, 3, 31))],
    )
    assert [s for _, s, _ in got] == [date(2026, 4, 1)]


def test_a_hole_left_by_a_void_is_refilled():
    """A gap between live invoices must be re-billed, not hidden by a later one."""
    got = missing_periods(
        date(2026, 1, 1), BillingInterval.monthly, {date(2026, 3, 1)}, date(2026, 3, 15),
        covered=[(date(2026, 1, 1), date(2026, 1, 31)), (date(2026, 3, 1), date(2026, 3, 31))],
    )
    assert [s for _, s, _ in got] == [date(2026, 2, 1)]


# ---------------------------------------------------------------- API


async def test_extending_shifts_every_later_period(client, headers_a):
    svc = await create_service(client, headers_a, sku="EXT", rate="3000")
    rec = await create_client_rec(client, headers_a)
    await _subscribe(client, headers_a, svc, rec, date(2026, 5, 1))
    await client.post("/api/invoices/generate-missing", json={}, headers=headers_a)

    issued = await _invoices(client, headers_a)
    assert (issued[0]["period_start"], issued[0]["period_end"]) == ("2026-05-01", "2026-05-31")

    # Give this client two extra weeks on their current period.
    latest = issued[-1]
    extended_to = "2026-08-14"
    res = await client.patch(
        f"/api/invoices/{latest['id']}", json={"period_end": extended_to}, headers=headers_a
    )
    assert res.status_code == 200, res.text
    assert res.json()["period_end"] == extended_to
    assert res.json()["period_end_adjusted"] is True

    # The next period picks up the day after, rather than the old anchor.
    await client.post("/api/invoices/generate-missing", json={}, headers=headers_a)
    periods = [(i["period_start"], i["period_end"]) for i in await _invoices(client, headers_a)]
    assert periods[-1] == (latest["period_start"], extended_to)
    # Nothing new yet: the extension already covers past today.
    assert len(periods) == len(issued)


async def test_only_the_latest_period_can_be_extended(client, headers_a):
    svc = await create_service(client, headers_a, sku="EXT-L", rate="3000")
    rec = await create_client_rec(client, headers_a)
    await _subscribe(client, headers_a, svc, rec, date(2026, 5, 1))
    await client.post("/api/invoices/generate-missing", json={}, headers=headers_a)
    issued = await _invoices(client, headers_a)
    assert len(issued) > 1

    res = await client.patch(
        f"/api/invoices/{issued[0]['id']}",
        json={"period_end": "2026-06-14"},
        headers=headers_a,
    )
    assert res.status_code == 422
    assert "Only the latest invoice" in res.json()["detail"]


async def test_extension_does_not_change_the_amount(client, headers_a):
    """An extension is goodwill, not a longer bill — the amount is untouched."""
    svc = await create_service(client, headers_a, sku="EXT2", rate="3000")
    rec = await create_client_rec(client, headers_a)
    await _subscribe(client, headers_a, svc, rec, date(2026, 6, 1))
    await client.post("/api/invoices/generate-missing", json={}, headers=headers_a)
    inv = (await _invoices(client, headers_a))[-1]

    res = await client.patch(
        f"/api/invoices/{inv['id']}", json={"period_end": "2026-09-15"}, headers=headers_a
    )
    assert res.status_code == 200, res.text
    assert res.json()["amount"] == inv["amount"]


async def test_generation_is_still_idempotent_after_an_extension(client, headers_a):
    svc = await create_service(client, headers_a, sku="EXT3", rate="3000")
    rec = await create_client_rec(client, headers_a)
    await _subscribe(client, headers_a, svc, rec, date(2026, 5, 1))
    await client.post("/api/invoices/generate-missing", json={}, headers=headers_a)
    inv = (await _invoices(client, headers_a))[-1]
    res = await client.patch(
        f"/api/invoices/{inv['id']}", json={"period_end": "2026-09-14"}, headers=headers_a
    )
    assert res.status_code == 200, res.text
    await client.post("/api/invoices/generate-missing", json={}, headers=headers_a)
    before = len(await _invoices(client, headers_a))

    res = await client.post("/api/invoices/generate-missing", json={}, headers=headers_a)
    assert res.json()["created"] == 0
    assert len(await _invoices(client, headers_a)) == before


async def test_paid_invoice_can_be_extended(client, headers_a):
    """The common case: the client paid, then paused, so the paid period stretches.
    The amount is untouched, so nothing about the payment is invalidated."""
    svc = await create_service(client, headers_a, sku="EXT4", rate="3000")
    rec = await create_client_rec(client, headers_a)
    await _subscribe(client, headers_a, svc, rec, date(2026, 6, 1))
    await client.post("/api/invoices/generate-missing", json={}, headers=headers_a)
    inv = (await _invoices(client, headers_a))[-1]
    await client.patch(f"/api/invoices/{inv['id']}", json={"status": "paid"}, headers=headers_a)

    res = await client.patch(
        f"/api/invoices/{inv['id']}", json={"period_end": "2026-09-15"}, headers=headers_a
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["period_end"] == "2026-09-15"
    assert body["status"] == "paid"          # still paid
    assert body["amount"] == inv["amount"]   # and still the same money
    assert body["can_adjust_period"] is True


async def test_voided_invoice_cannot_be_extended(client, headers_a):
    svc = await create_service(client, headers_a, sku="EXT4V", rate="3000")
    rec = await create_client_rec(client, headers_a)
    await _subscribe(client, headers_a, svc, rec, date(2026, 6, 1))
    await client.post("/api/invoices/generate-missing", json={}, headers=headers_a)
    inv = (await _invoices(client, headers_a))[-1]
    await client.patch(f"/api/invoices/{inv['id']}", json={"status": "void"}, headers=headers_a)

    res = await client.patch(
        f"/api/invoices/{inv['id']}", json={"period_end": "2026-09-15"}, headers=headers_a
    )
    assert res.status_code == 422
    assert "voided invoice" in res.json()["detail"]


async def test_extending_a_paid_period_shifts_the_next_one(client, headers_a):
    """The shift must work off a paid invoice too, not just a due one."""
    svc = await create_service(client, headers_a, sku="EXT4S", rate="3000")
    rec = await create_client_rec(client, headers_a)
    await _subscribe(client, headers_a, svc, rec, date(2026, 6, 1))
    await client.post("/api/invoices/generate-missing", json={}, headers=headers_a)
    inv = (await _invoices(client, headers_a))[-1]
    await client.patch(f"/api/invoices/{inv['id']}", json={"status": "paid"}, headers=headers_a)
    # Adjust the period end, relative to the period so the test doesn't rot as time passes.
    early = date.fromisoformat(inv["period_start"]) + timedelta(days=14)
    await client.patch(
        f"/api/invoices/{inv['id']}", json={"period_end": str(early)}, headers=headers_a
    )

    # Advance-bill the next period (independent of today's date) — it must pick up the day
    # after the adjusted end, proving the shift works off a paid invoice.
    res = await client.post(
        f"/api/clients/{rec['id']}/invoices/advance", json={"periods": 1}, headers=headers_a
    )
    assert res.json()["created"] == 1
    after = await _invoices(client, headers_a)
    extended = next(i for i in after if i["id"] == inv["id"])
    assert extended["period_end"] == str(early)
    assert any(i["period_start"] == str(early + timedelta(days=1)) for i in after)


async def test_period_cannot_end_before_it_starts(client, headers_a):
    svc = await create_service(client, headers_a, sku="EXT5", rate="3000")
    rec = await create_client_rec(client, headers_a)
    await _subscribe(client, headers_a, svc, rec, date(2026, 6, 1))
    await client.post("/api/invoices/generate-missing", json={}, headers=headers_a)
    inv = (await _invoices(client, headers_a))[-1]

    res = await client.patch(
        f"/api/invoices/{inv['id']}", json={"period_end": "2026-05-01"}, headers=headers_a
    )
    assert res.status_code == 422


async def test_status_patch_still_works(client, headers_a):
    """Regression: the existing paid/void flow must be untouched."""
    svc = await create_service(client, headers_a, sku="EXT6", rate="3000")
    rec = await create_client_rec(client, headers_a)
    await _subscribe(client, headers_a, svc, rec, date(2026, 6, 1))
    await client.post("/api/invoices/generate-missing", json={}, headers=headers_a)
    inv = (await _invoices(client, headers_a))[0]
    res = await client.patch(
        f"/api/invoices/{inv['id']}", json={"status": "void"}, headers=headers_a
    )
    assert res.status_code == 200
    assert res.json()["status"] == "void"


# ---------------------------------------------------------------- voiding


async def test_voided_period_is_regenerated(client, headers_a):
    """Void means "this invoice bills nothing", so the period is unbilled again and the
    next run re-issues it — with a fresh number, alongside the voided row."""
    svc = await create_service(client, headers_a, sku="VOID1", rate="3000")
    rec = await create_client_rec(client, headers_a)
    await _subscribe(client, headers_a, svc, rec, date(2026, 6, 1))
    await client.post("/api/invoices/generate-missing", json={}, headers=headers_a)
    issued = await _invoices(client, headers_a)
    victim = issued[0]

    await client.patch(
        f"/api/invoices/{victim['id']}", json={"status": "void"}, headers=headers_a
    )
    res = await client.post("/api/invoices/generate-missing", json={}, headers=headers_a)
    assert res.json()["created"] == 1

    after = await _invoices(client, headers_a)
    same_period = [i for i in after if i["period_start"] == victim["period_start"]]
    assert len(same_period) == 2  # the voided one and its replacement
    assert {i["status"] for i in same_period} == {"void", "due"}
    replacement = next(i for i in same_period if i["status"] == "due")
    assert replacement["number"] != victim["number"]


async def test_voiding_a_reissued_invoice_does_not_collide(client, headers_a):
    """The partial index must tolerate several voids on one period."""
    svc = await create_service(client, headers_a, sku="VOID2", rate="3000")
    rec = await create_client_rec(client, headers_a)
    await _subscribe(client, headers_a, svc, rec, date(2026, 6, 1))
    await client.post("/api/invoices/generate-missing", json={}, headers=headers_a)

    for _ in range(3):
        live = [i for i in await _invoices(client, headers_a) if i["status"] == "due"]
        target = live[0]
        res = await client.patch(
            f"/api/invoices/{target['id']}", json={"status": "void"}, headers=headers_a
        )
        assert res.status_code == 200
        res = await client.post("/api/invoices/generate-missing", json={}, headers=headers_a)
        assert res.status_code == 200, res.text

    # Exactly one live invoice per period survives, however many voids preceded it.
    live = [i for i in await _invoices(client, headers_a) if i["status"] != "void"]
    starts = [i["period_start"] for i in live]
    assert len(starts) == len(set(starts))


async def test_void_does_not_shadow_the_latest_for_extension(client, headers_a):
    """A voided newest invoice must not block extending the newest live one."""
    svc = await create_service(client, headers_a, sku="VOID3", rate="3000")
    rec = await create_client_rec(client, headers_a)
    await _subscribe(client, headers_a, svc, rec, date(2026, 5, 1))
    await client.post("/api/invoices/generate-missing", json={}, headers=headers_a)
    issued = await _invoices(client, headers_a)
    newest = issued[-1]
    await client.patch(
        f"/api/invoices/{newest['id']}", json={"status": "void"}, headers=headers_a
    )

    # The one before it is now the newest live invoice, so it becomes extendable.
    prior = issued[-2]
    fresh = [i for i in await _invoices(client, headers_a) if i["id"] == prior["id"]][0]
    assert fresh["can_adjust_period"] is True
    res = await client.patch(
        f"/api/invoices/{prior['id']}", json={"period_end": "2026-10-01"}, headers=headers_a
    )
    assert res.status_code == 200, res.text


async def test_closing_a_period_early_starts_the_next_one_sooner(client, headers_a):
    """A usage-based plan whose deliverables are all delivered can close early — the
    next period then begins the following day rather than at the original end."""
    svc = await create_service(client, headers_a, sku="EARLY", rate="3000")
    rec = await create_client_rec(client, headers_a)
    await _subscribe(client, headers_a, svc, rec, date(2026, 5, 1))
    await client.post("/api/invoices/generate-missing", json={}, headers=headers_a)
    issued = await _invoices(client, headers_a)
    latest = issued[-1]

    # Everything delivered nine days in — close the current period there.
    start = date.fromisoformat(latest["period_start"])
    early_end = start + timedelta(days=9)
    res = await client.patch(
        f"/api/invoices/{latest['id']}",
        json={"period_end": str(early_end)},
        headers=headers_a,
    )
    assert res.status_code == 200, res.text
    assert res.json()["period_end"] == str(early_end)

    # The next period picks up the very next day. Advance-bill it so the assertion doesn't
    # depend on where today falls relative to the period.
    res = await client.post(
        f"/api/clients/{rec['id']}/invoices/advance", json={"periods": 1}, headers=headers_a
    )
    assert res.json()["created"] == 1
    periods = [(i["period_start"], i["period_end"]) for i in await _invoices(client, headers_a)]
    assert (latest["period_start"], str(early_end)) in periods
    assert any(s == str(early_end + timedelta(days=1)) for s, _ in periods)


async def test_closing_early_is_still_idempotent(client, headers_a):
    svc = await create_service(client, headers_a, sku="EARLY2", rate="3000")
    rec = await create_client_rec(client, headers_a)
    await _subscribe(client, headers_a, svc, rec, date(2026, 5, 1))
    await client.post("/api/invoices/generate-missing", json={}, headers=headers_a)
    latest = (await _invoices(client, headers_a))[-1]
    early_end = date.fromisoformat(latest["period_start"]) + timedelta(days=9)
    res = await client.patch(
        f"/api/invoices/{latest['id']}",
        json={"period_end": str(early_end)},
        headers=headers_a,
    )
    assert res.status_code == 200, res.text
    await client.post("/api/invoices/generate-missing", json={}, headers=headers_a)
    before = len(await _invoices(client, headers_a))

    res = await client.post("/api/invoices/generate-missing", json={}, headers=headers_a)
    assert res.json()["created"] == 0
    assert len(await _invoices(client, headers_a)) == before


# ---------------------------------------------------------------- document view


async def test_invoice_document_carries_everything_a_pdf_needs(client, headers_a):
    svc = await create_service(client, headers_a, sku="DOC1", rate="3000")
    rec = await create_client_rec(
        client, headers_a, name="Asha Rao", email="asha@example.com",
        address="12 MG Road, Bengaluru",
    )
    await _subscribe(client, headers_a, svc, rec, date(2026, 6, 1))
    await client.post("/api/invoices/generate-missing", json={}, headers=headers_a)
    inv = (await _invoices(client, headers_a))[0]

    res = await client.get(f"/api/invoices/{inv['id']}", headers=headers_a)
    assert res.status_code == 200, res.text
    doc = res.json()
    assert doc["number"] == inv["number"]
    assert doc["currency"] == "INR"
    assert doc["issued_by"]["name"] == "Studio A"
    assert doc["bill_to"]["name"] == "Asha Rao"
    assert doc["bill_to"]["address"] == "12 MG Road, Bengaluru"
    assert doc["includes"] == ["12 classes — Classes"]
    assert doc["period_start"] and doc["period_end"]


async def test_invoice_document_carries_the_service_description(client, headers_a):
    """The description line on the printed invoice comes from the service."""
    svc = await create_service(
        client, headers_a, sku="DOC3", rate="3000",
        description="Morning and evening Hatha classes at the studio.",
    )
    rec = await create_client_rec(client, headers_a)
    await _subscribe(client, headers_a, svc, rec, date(2026, 6, 1))
    await client.post("/api/invoices/generate-missing", json={}, headers=headers_a)
    inv = (await _invoices(client, headers_a))[0]

    doc = (await client.get(f"/api/invoices/{inv['id']}", headers=headers_a)).json()
    assert doc["service_description"] == "Morning and evening Hatha classes at the studio."


async def test_invoice_document_without_a_description(client, headers_a):
    """Most services have none, so the field must simply be absent, not an error."""
    svc = await create_service(client, headers_a, sku="DOC4", rate="3000")
    rec = await create_client_rec(client, headers_a)
    await _subscribe(client, headers_a, svc, rec, date(2026, 6, 1))
    await client.post("/api/invoices/generate-missing", json={}, headers=headers_a)
    inv = (await _invoices(client, headers_a))[0]

    doc = (await client.get(f"/api/invoices/{inv['id']}", headers=headers_a)).json()
    assert not doc["service_description"]


async def test_invoice_document_is_org_scoped(client, headers_a, headers_b):
    """A new endpoint taking an id must answer 404 for a foreign tenant (§5.6)."""
    svc = await create_service(client, headers_a, sku="DOC2", rate="3000")
    rec = await create_client_rec(client, headers_a)
    await _subscribe(client, headers_a, svc, rec, date(2026, 6, 1))
    await client.post("/api/invoices/generate-missing", json={}, headers=headers_a)
    inv = (await _invoices(client, headers_a))[0]

    assert (await client.get(f"/api/invoices/{inv['id']}", headers=headers_b)).status_code == 404
    assert (await client.get(f"/api/invoices/{inv['id']}", headers=headers_a)).status_code == 200


# ---------------------------------------------------------------- deleting


async def _one_invoice(client, headers):
    return (await _invoices(client, headers))[0]


async def test_void_invoice_can_be_deleted(client, headers_a):
    svc = await create_service(client, headers_a, sku="DEL1", rate="3000")
    rec = await create_client_rec(client, headers_a)
    await _subscribe(client, headers_a, svc, rec, date(2026, 6, 1))
    await client.post("/api/invoices/generate-missing", json={}, headers=headers_a)
    inv = await _one_invoice(client, headers_a)
    await client.patch(f"/api/invoices/{inv['id']}", json={"status": "void"}, headers=headers_a)

    res = await client.delete(f"/api/invoices/{inv['id']}", headers=headers_a)
    assert res.status_code == 204
    remaining = [i["id"] for i in await _invoices(client, headers_a)]
    assert inv["id"] not in remaining


async def test_due_invoice_cannot_be_deleted(client, headers_a):
    svc = await create_service(client, headers_a, sku="DEL2", rate="3000")
    rec = await create_client_rec(client, headers_a)
    await _subscribe(client, headers_a, svc, rec, date(2026, 6, 1))
    await client.post("/api/invoices/generate-missing", json={}, headers=headers_a)
    inv = await _one_invoice(client, headers_a)

    res = await client.delete(f"/api/invoices/{inv['id']}", headers=headers_a)
    assert res.status_code == 422
    assert "Void it first" in res.json()["detail"]


async def test_paid_invoice_cannot_be_deleted(client, headers_a):
    svc = await create_service(client, headers_a, sku="DEL3", rate="3000")
    rec = await create_client_rec(client, headers_a)
    await _subscribe(client, headers_a, svc, rec, date(2026, 6, 1))
    await client.post("/api/invoices/generate-missing", json={}, headers=headers_a)
    inv = await _one_invoice(client, headers_a)
    await client.patch(f"/api/invoices/{inv['id']}", json={"status": "paid"}, headers=headers_a)

    res = await client.delete(f"/api/invoices/{inv['id']}", headers=headers_a)
    assert res.status_code == 422
    assert "paid" in res.json()["detail"]


async def test_deleting_a_void_leaves_billing_coverage_intact(client, headers_a):
    """Delete a void whose period was already re-issued — the live invoice stays and
    generation stays idempotent."""
    svc = await create_service(client, headers_a, sku="DEL4", rate="3000")
    rec = await create_client_rec(client, headers_a)
    await _subscribe(client, headers_a, svc, rec, date(2026, 6, 1))
    await client.post("/api/invoices/generate-missing", json={}, headers=headers_a)
    inv = await _one_invoice(client, headers_a)
    period = inv["period_start"]
    # Void it, let the period re-issue, then delete the stale void.
    await client.patch(f"/api/invoices/{inv['id']}", json={"status": "void"}, headers=headers_a)
    await client.post("/api/invoices/generate-missing", json={}, headers=headers_a)
    await client.delete(f"/api/invoices/{inv['id']}", headers=headers_a)

    live = [i for i in await _invoices(client, headers_a) if i["period_start"] == period]
    assert len(live) == 1 and live[0]["status"] == "due"
    res = await client.post("/api/invoices/generate-missing", json={}, headers=headers_a)
    assert res.json()["created"] == 0


async def test_delete_invoice_is_org_scoped(client, headers_a, headers_b):
    svc = await create_service(client, headers_a, sku="DEL5", rate="3000")
    rec = await create_client_rec(client, headers_a)
    await _subscribe(client, headers_a, svc, rec, date(2026, 6, 1))
    await client.post("/api/invoices/generate-missing", json={}, headers=headers_a)
    inv = await _one_invoice(client, headers_a)
    await client.patch(f"/api/invoices/{inv['id']}", json={"status": "void"}, headers=headers_a)

    assert (await client.delete(f"/api/invoices/{inv['id']}", headers=headers_b)).status_code == 404
    assert (await client.delete(f"/api/invoices/{inv['id']}", headers=headers_a)).status_code == 204
