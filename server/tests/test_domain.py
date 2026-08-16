"""Domain rules: company/family fields (§5.3), notes, capacity (§5.5),
enrollment dedupe, soft deletes, search."""

from tests.conftest import (
    create_batch,
    create_client_rec,
    create_instructor,
    create_location,
    create_service,
)


async def test_company_and_gstin_fields_are_plain(client, headers_a):
    rec = await create_client_rec(
        client,
        headers_a,
        company_name="Acme",
        gstin="27AAA",
        company_contact="Ravi",
    )
    assert rec["company_name"] == "Acme"
    # These are ordinary fields — an unrelated edit leaves them intact.
    res = await client.patch(
        f"/api/clients/{rec['id']}", json={"work": "Analyst"}, headers=headers_a
    )
    body = res.json()
    assert body["company_name"] == "Acme" and body["company_contact"] == "Ravi"
    assert body["gstin"] == "27AAA"


async def test_family_link_and_reverse_link(client, headers_a):
    anchor = await create_client_rec(client, headers_a, name="Anchor")
    member = await create_client_rec(
        client, headers_a, name="Member", family_link_id=anchor["id"]
    )
    assert member["family_link_name"] == "Anchor"
    # Reverse link shown on the linked member's profile.
    res = await client.get(f"/api/clients/{anchor['id']}", headers=headers_a)
    assert [x["name"] for x in res.json()["linked_by"]] == ["Member"]
    # Clearing the link removes it.
    res = await client.patch(
        f"/api/clients/{member['id']}", json={"family_link_id": None}, headers=headers_a
    )
    assert res.json()["family_link_id"] is None
    # Self-link rejected.
    res = await client.patch(
        f"/api/clients/{anchor['id']}",
        json={"family_link_id": anchor["id"]},
        headers=headers_a,
    )
    assert res.status_code == 422


async def test_notes_append_only_newest_first(client, headers_a):
    rec = await create_client_rec(client, headers_a)
    for day, text in [("2026-07-01", "first"), ("2026-07-10", "second")]:
        res = await client.post(
            f"/api/clients/{rec['id']}/notes",
            json={"date": day, "channel": "Call", "text": text},
            headers=headers_a,
        )
        assert res.status_code == 201
        assert res.json()["author_name"] == "Admin-A"
    res = await client.get(f"/api/clients/{rec['id']}/notes", headers=headers_a)
    assert [n["text"] for n in res.json()] == ["second", "first"]


async def test_enrollment_duplicate_409_and_roster(client, headers_a):
    instructor = await create_instructor(client, headers_a)
    location = await create_location(client, headers_a)
    batch = await create_batch(client, headers_a, location["id"], instructor["id"])
    rec = await create_client_rec(client, headers_a)

    body = {"client_id": rec["id"], "batch_id": batch["id"], "start_date": "2026-07-01"}
    assert (
        await client.post("/api/enrollments", json=body, headers=headers_a)
    ).status_code == 201
    assert (
        await client.post("/api/enrollments", json=body, headers=headers_a)
    ).status_code == 409

    res = await client.get(f"/api/batches/{batch['id']}/roster", headers=headers_a)
    assert [e["client_name"] for e in res.json()] == ["Asha Rao"]
    res = await client.get(f"/api/batches/{batch['id']}", headers=headers_a)
    assert res.json()["enrolled_count"] == 1 and res.json()["capacity"] == 10


async def test_capacity_warn_vs_block(client, seed, headers_a, headers_root):
    instructor = await create_instructor(client, headers_a)
    location = await create_location(client, headers_a, code="TINY", capacity_per_batch=1)
    batch = await create_batch(
        client, headers_a, location["id"], instructor["id"], code="TINY-B"
    )
    first = await create_client_rec(client, headers_a, name="One")
    second = await create_client_rec(client, headers_a, name="Two")

    res = await client.post(
        "/api/enrollments",
        json={"client_id": first["id"], "batch_id": batch["id"], "start_date": "2026-07-01"},
        headers=headers_a,
    )
    assert res.status_code == 201 and res.json()["capacity_warning"] is None

    # Default policy is warn: over-capacity allowed, with a warning.
    res = await client.post(
        "/api/enrollments",
        json={"client_id": second["id"], "batch_id": batch["id"], "start_date": "2026-07-01"},
        headers=headers_a,
    )
    assert res.status_code == 201
    assert "over capacity" in res.json()["capacity_warning"]

    # Switch org to block: rejected.
    res = await client.patch("/api/org", json={"capacity_policy": "block"}, headers=headers_a)
    assert res.status_code == 200
    third = await create_client_rec(client, headers_a, name="Three")
    res = await client.post(
        "/api/enrollments",
        json={"client_id": third["id"], "batch_id": batch["id"], "start_date": "2026-07-01"},
        headers=headers_a,
    )
    assert res.status_code == 409


async def test_soft_delete_hides_but_keeps_row(client, headers_a):
    service = await create_service(client, headers_a, sku="GONE-1")
    assert (
        await client.delete(f"/api/services/{service['id']}", headers=headers_a)
    ).status_code == 204
    assert (
        await client.get(f"/api/services/{service['id']}", headers=headers_a)
    ).status_code == 404
    res = await client.get("/api/services", headers=headers_a)
    assert service["id"] not in {s["id"] for s in res.json()["items"]}


async def test_clients_list_shows_subscriptions_and_batch(client, headers_a):
    """The clients list summarises each client's active subscriptions and their batch."""
    instructor = await create_instructor(client, headers_a)
    location = await create_location(client, headers_a)
    batch = await create_batch(client, headers_a, location["id"], instructor["id"])
    svc = await create_service(client, headers_a, sku="SUM-1", rate="3000")
    rec = await create_client_rec(client, headers_a, name="Summed")
    await client.post(
        f"/api/clients/{rec['id']}/subscriptions",
        json={"service_id": svc["id"], "start_date": "2026-07-01"},
        headers=headers_a,
    )
    await client.post(
        "/api/enrollments",
        json={"client_id": rec["id"], "batch_id": batch["id"], "start_date": "2026-07-01"},
        headers=headers_a,
    )

    listed = (await client.get("/api/clients?q=Summed", headers=headers_a)).json()["items"]
    assert len(listed) == 1
    row = listed[0]
    assert row["active_services"] == [svc["name"]]
    assert row["batch_name"] == batch["name"]
    assert row["batch_code"] == batch["code"]

    # A client with no subscription or enrolment reports empty summaries.
    await create_client_rec(client, headers_a, name="Bare")
    listed = (await client.get("/api/clients?q=Bare", headers=headers_a)).json()["items"]
    assert listed[0]["active_services"] == []
    assert listed[0]["batch_name"] is None


async def test_clients_filter_by_batches_and_services(client, headers_a):
    """Clients can be filtered by batch and by subscribed service; ids OR within a facet,
    facets AND together, and the total follows."""
    instructor = await create_instructor(client, headers_a)
    location = await create_location(client, headers_a)
    batch_x = await create_batch(client, headers_a, location["id"], instructor["id"], code="BX")
    batch_y = await create_batch(client, headers_a, location["id"], instructor["id"], code="BY")
    svc = await create_service(client, headers_a, sku="FS-1", rate="3000")

    alice = await create_client_rec(client, headers_a, name="Alice")
    bob = await create_client_rec(client, headers_a, name="Bob")
    await create_client_rec(client, headers_a, name="Carol")  # in nothing

    # Alice: subscribed + in batch_x. Bob: only in batch_y.
    await client.post(
        f"/api/clients/{alice['id']}/subscriptions",
        json={"service_id": svc["id"], "start_date": "2026-07-01"},
        headers=headers_a,
    )
    for cid, bid in ((alice["id"], batch_x["id"]), (bob["id"], batch_y["id"])):
        await client.post(
            "/api/enrollments",
            json={"client_id": cid, "batch_id": bid, "start_date": "2026-07-01"},
            headers=headers_a,
        )

    async def names(query):
        res = (await client.get(f"/api/clients?{query}", headers=headers_a)).json()
        return res["total"], sorted(c["name"] for c in res["items"])

    # Batch facet OR: either batch → Alice and Bob.
    assert await names(f"batch_ids={batch_x['id']}&batch_ids={batch_y['id']}") == (2, ["Alice", "Bob"])
    # Single batch.
    assert await names(f"batch_ids={batch_y['id']}") == (1, ["Bob"])
    # Service facet.
    assert await names(f"service_ids={svc['id']}") == (1, ["Alice"])
    # Facets AND: in batch_y AND subscribed → nobody (Bob isn't subscribed).
    assert await names(f"batch_ids={batch_y['id']}&service_ids={svc['id']}") == (0, [])


async def test_search_and_lifecycle_filter(client, headers_a):
    await create_client_rec(client, headers_a, name="Asha Rao", phone="98860")
    await create_client_rec(client, headers_a, name="Vikram Iyer")
    res = await client.get("/api/clients?q=asha", headers=headers_a)
    assert [c["name"] for c in res.json()["items"]] == ["Asha Rao"]
    res = await client.get("/api/clients?q=98860", headers=headers_a)
    assert [c["name"] for c in res.json()["items"]] == ["Asha Rao"]
    res = await client.get("/api/clients?lifecycle_stage=Lead", headers=headers_a)
    assert len(res.json()["items"]) == 2


async def test_clients_total_and_active_subscriber_filter(client, headers_a):
    """The list reports a filtered total, and active_subscribers restricts to clients
    holding an active subscription — with the total moving to match."""
    svc = await create_service(client, headers_a, sku="AS-1", rate="3000")
    subbed = await create_client_rec(client, headers_a, name="Subbed")
    await create_client_rec(client, headers_a, name="Unsubbed")
    await client.post(
        f"/api/clients/{subbed['id']}/subscriptions",
        json={"service_id": svc["id"], "start_date": "2026-07-01"},
        headers=headers_a,
    )

    everyone = (await client.get("/api/clients", headers=headers_a)).json()
    assert everyone["total"] == 2
    assert len(everyone["items"]) == 2

    active = (await client.get("/api/clients?active_subscribers=true", headers=headers_a)).json()
    assert active["total"] == 1
    assert [c["name"] for c in active["items"]] == ["Subbed"]

    # The filter composes with search, and the total follows the composed filter.
    none = (
        await client.get("/api/clients?active_subscribers=true&q=Unsubbed", headers=headers_a)
    ).json()
    assert none["total"] == 0 and none["items"] == []


async def test_service_deliverables_roundtrip(client, headers_a):
    service = await create_service(client, headers_a, sku="DEL-1")
    assert service["deliverables"][0]["unit"] == "classes"
    res = await client.patch(
        f"/api/services/{service['id']}",
        json={
            "deliverables": [
                {"name": "Sessions", "quantity": 8, "unit": "sessions"},
                {"name": "Assessments", "quantity": 2, "unit": "sessions"},
            ]
        },
        headers=headers_a,
    )
    assert res.status_code == 200
    assert [d["name"] for d in res.json()["deliverables"]] == ["Sessions", "Assessments"]


async def test_batch_validation(client, headers_a):
    instructor = await create_instructor(client, headers_a)
    location = await create_location(client, headers_a)
    res = await client.post(
        "/api/batches",
        json={
            "name": "Bad",
            "code": "BAD-1",
            "location_id": location["id"],
            "instructor_id": instructor["id"],
            "start_date": "2026-08-01",
            "end_date": "2026-07-01",
        },
        headers=headers_a,
    )
    assert res.status_code == 422
    res = await client.post(
        "/api/batches",
        json={
            "name": "Bad",
            "code": "BAD-2",
            "location_id": location["id"],
            "instructor_id": instructor["id"],
            "start_time": "10:00:00",
            "end_time": "09:00:00",
        },
        headers=headers_a,
    )
    assert res.status_code == 422


async def test_instructor_derived_fields(client, headers_a):
    instructor = await create_instructor(
        client,
        headers_a,
        date_of_birth="1990-01-15",
        experience_at_joining="5.0",
        joining_date="2024-01-15",
    )
    assert instructor["age"] >= 36
    assert float(instructor["current_experience"]) >= 7.0


async def test_dashboard_shape(client, headers_a):
    res = await client.get("/api/dashboard", headers=headers_a)
    assert res.status_code == 200
    body = res.json()
    assert {"active_clients", "active_batches", "billed_this_month", "overdue_count"} <= set(
        body
    )
