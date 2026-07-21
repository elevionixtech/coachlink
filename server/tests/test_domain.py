"""Domain rules: corporate/family accounts (§5.3), notes, capacity (§5.5),
enrollment dedupe, soft deletes, search."""

from tests.conftest import (
    create_batch,
    create_client_rec,
    create_instructor,
    create_location,
    create_service,
)


async def test_corporate_fields_cleared_on_switch_away(client, headers_a):
    rec = await create_client_rec(
        client,
        headers_a,
        account_type="Corporate",
        company_name="Acme",
        gstin="27AAA",
        company_contact="Ravi",
    )
    assert rec["company_name"] == "Acme"
    res = await client.patch(
        f"/api/clients/{rec['id']}", json={"account_type": "Individual"}, headers=headers_a
    )
    body = res.json()
    assert body["company_name"] is None and body["gstin"] is None


async def test_family_link_and_reverse_link(client, headers_a):
    anchor = await create_client_rec(client, headers_a, name="Anchor")
    member = await create_client_rec(
        client, headers_a, name="Member", account_type="Family", family_link_id=anchor["id"]
    )
    assert member["family_link_name"] == "Anchor"
    # Reverse link shown on the linked member's profile.
    res = await client.get(f"/api/clients/{anchor['id']}", headers=headers_a)
    assert [x["name"] for x in res.json()["linked_by"]] == ["Member"]
    # Switching away from Family clears the link.
    res = await client.patch(
        f"/api/clients/{member['id']}", json={"account_type": "Individual"}, headers=headers_a
    )
    assert res.json()["family_link_id"] is None
    # Self-link rejected.
    res = await client.patch(
        f"/api/clients/{anchor['id']}",
        json={"account_type": "Family", "family_link_id": anchor["id"]},
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


async def test_search_and_lifecycle_filter(client, headers_a):
    await create_client_rec(client, headers_a, name="Asha Rao", phone="98860")
    await create_client_rec(client, headers_a, name="Vikram Iyer")
    res = await client.get("/api/clients?q=asha", headers=headers_a)
    assert [c["name"] for c in res.json()["items"]] == ["Asha Rao"]
    res = await client.get("/api/clients?q=98860", headers=headers_a)
    assert [c["name"] for c in res.json()["items"]] == ["Asha Rao"]
    res = await client.get("/api/clients?lifecycle_stage=Lead", headers=headers_a)
    assert len(res.json()["items"]) == 2


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
