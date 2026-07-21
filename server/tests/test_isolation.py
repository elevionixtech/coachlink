"""Tenant isolation suite (§5.6) — the guard for app-layer enforcement."""

from tests.conftest import (
    create_batch,
    create_client_rec,
    create_instructor,
    create_location,
    create_service,
)


async def test_lists_are_org_scoped(client, headers_a, headers_b):
    await create_service(client, headers_a, sku="A-SKU")
    await create_client_rec(client, headers_a, name="Only A")
    for path in ("/api/services", "/api/clients"):
        res = await client.get(path, headers=headers_b)
        assert res.status_code == 200
        assert res.json()["items"] == []


async def test_foreign_tenant_reads_and_mutations_404(client, headers_a, headers_b):
    service = await create_service(client, headers_a)
    cl = await create_client_rec(client, headers_a)
    instructor = await create_instructor(client, headers_a)
    location = await create_location(client, headers_a)
    batch = await create_batch(client, headers_a, location["id"], instructor["id"])

    checks = [
        ("/api/services/", service["id"]),
        ("/api/clients/", cl["id"]),
        ("/api/instructors/", instructor["id"]),
        ("/api/locations/", location["id"]),
        ("/api/batches/", batch["id"]),
    ]
    for prefix, obj_id in checks:
        assert (await client.get(prefix + obj_id, headers=headers_b)).status_code == 404
        assert (
            await client.patch(prefix + obj_id, json={"name": "X"}, headers=headers_b)
        ).status_code == 404
        assert (await client.delete(prefix + obj_id, headers=headers_b)).status_code == 404
        # And the owner still sees it.
        assert (await client.get(prefix + obj_id, headers=headers_a)).status_code == 200


async def test_cross_org_reference_ids_rejected_as_404(client, headers_a, headers_b):
    # Org B resources
    instructor_b = await create_instructor(client, headers_b)
    location_b = await create_location(client, headers_b)
    client_b = await create_client_rec(client, headers_b)
    service_b = await create_service(client, headers_b)
    batch_b = await create_batch(client, headers_b, location_b["id"], instructor_b["id"])

    # Org A tries to attach org B's ids
    instructor_a = await create_instructor(client, headers_a)
    location_a = await create_location(client, headers_a)
    client_a = await create_client_rec(client, headers_a)

    res = await client.post(
        "/api/batches",
        json={
            "name": "X",
            "code": "X-1",
            "location_id": location_b["id"],
            "instructor_id": instructor_a["id"],
        },
        headers=headers_a,
    )
    assert res.status_code == 404

    res = await client.post(
        "/api/batches",
        json={
            "name": "X",
            "code": "X-1",
            "location_id": location_a["id"],
            "instructor_id": instructor_b["id"],
        },
        headers=headers_a,
    )
    assert res.status_code == 404

    res = await client.post(
        "/api/enrollments",
        json={
            "client_id": client_a["id"],
            "batch_id": batch_b["id"],
            "start_date": "2026-07-01",
        },
        headers=headers_a,
    )
    assert res.status_code == 404

    res = await client.post(
        "/api/enrollments",
        json={
            "client_id": client_b["id"],
            "batch_id": batch_b["id"],
            "start_date": "2026-07-01",
        },
        headers=headers_a,
    )
    assert res.status_code == 404

    res = await client.post(
        f"/api/clients/{client_a['id']}/subscriptions",
        json={"service_id": service_b["id"], "start_date": "2026-07-01"},
        headers=headers_a,
    )
    assert res.status_code == 404

    res = await client.patch(
        f"/api/clients/{client_a['id']}",
        json={"account_type": "Family", "family_link_id": client_b["id"]},
        headers=headers_a,
    )
    assert res.status_code == 404


async def test_per_org_uniqueness(client, headers_a, headers_b):
    # Same SKU in two orgs is fine; duplicate within one org conflicts.
    await create_service(client, headers_a, sku="SHARED")
    await create_service(client, headers_b, sku="SHARED")
    res = await client.post(
        "/api/services",
        json={
            "name": "Dup",
            "sku": "SHARED",
            "service_type": "Subscription",
            "delivery_mode": "Offline",
            "rate": "100",
        },
        headers=headers_a,
    )
    assert res.status_code == 409

    # Same location code across orgs fine, dup within org conflicts.
    await create_location(client, headers_a, code="MAIN")
    await create_location(client, headers_b, code="MAIN")
    res = await client.post(
        "/api/locations", json={"name": "Dup", "code": "MAIN"}, headers=headers_a
    )
    assert res.status_code == 409


async def test_role_matrix(client, seed, headers_a, headers_a_staff, headers_b, headers_root):
    org_a_id = str(seed["org_a"].id)
    member = {"name": "New", "username": "new-user", "password": "pass1234", "role": "staff"}

    # Staff cannot manage members.
    res = await client.post(
        f"/api/organisations/{org_a_id}/members", json=member, headers=headers_a_staff
    )
    assert res.status_code == 403

    # Foreign org admin gets 404, never a 403 (no existence leak).
    res = await client.post(
        f"/api/organisations/{org_a_id}/members", json=member, headers=headers_b
    )
    assert res.status_code == 404

    # Own admin can add; created members can never be superadmin.
    res = await client.post(
        f"/api/organisations/{org_a_id}/members", json=member, headers=headers_a
    )
    assert res.status_code == 201
    res = await client.post(
        f"/api/organisations/{org_a_id}/members",
        json={**member, "username": "evil", "role": "superadmin"},
        headers=headers_a,
    )
    assert res.status_code == 422

    # Superadmin manages any org but gets 403 on all domain APIs.
    res = await client.post(
        f"/api/organisations/{org_a_id}/members",
        json={**member, "username": "via-root"},
        headers=headers_root,
    )
    assert res.status_code == 201
    for path in ("/api/clients", "/api/services", "/api/dashboard", "/api/invoices"):
        assert (await client.get(path, headers=headers_root)).status_code == 403

    # Org users get 403 on platform APIs.
    assert (await client.get("/api/admin/organisations", headers=headers_a)).status_code == 403


async def test_username_unique_per_org_but_reusable_across_orgs(
    client, seed, headers_a, headers_b
):
    org_a_id = str(seed["org_a"].id)
    org_b_id = str(seed["org_b"].id)
    member = {"name": "Sam", "username": "sam", "password": "pass1234", "role": "staff"}
    assert (
        await client.post(
            f"/api/organisations/{org_a_id}/members", json=member, headers=headers_a
        )
    ).status_code == 201
    assert (
        await client.post(
            f"/api/organisations/{org_b_id}/members", json=member, headers=headers_b
        )
    ).status_code == 201
    assert (
        await client.post(
            f"/api/organisations/{org_a_id}/members", json=member, headers=headers_a
        )
    ).status_code == 409
