"""A batch's services gate enrolment (§5.5): only clients with an active subscription to
one of the batch's services may enrol; a serviceless batch stays open."""

from datetime import date

from tests.conftest import (
    create_batch,
    create_client_rec,
    create_instructor,
    create_location,
    create_service,
)


async def _batch_with_services(client, headers, service_ids, code="BS-1"):
    loc = await create_location(client, headers, code=f"L-{code}")
    ins = await create_instructor(client, headers)
    return await create_batch(
        client, headers, loc["id"], ins["id"], code=code, service_ids=service_ids
    )


async def _subscribe(client, headers, client_id, service_id):
    res = await client.post(
        f"/api/clients/{client_id}/subscriptions",
        json={"service_id": service_id, "start_date": str(date.today())},
        headers=headers,
    )
    assert res.status_code == 201, res.text
    return res.json()


async def _enroll(client, headers, client_id, batch_id):
    return await client.post(
        "/api/enrollments",
        json={"client_id": client_id, "batch_id": batch_id, "start_date": str(date.today())},
        headers=headers,
    )


async def test_batch_stores_its_services(client, headers_a):
    svc = await create_service(client, headers_a, sku="BS-SVC")
    batch = await _batch_with_services(client, headers_a, [svc["id"]])
    assert [s["id"] for s in batch["services"]] == [svc["id"]]
    # And it round-trips on read.
    got = (await client.get(f"/api/batches/{batch['id']}", headers=headers_a)).json()
    assert [s["sku"] for s in got["services"]] == ["BS-SVC"]


async def test_subscribed_client_can_enrol(client, headers_a):
    svc = await create_service(client, headers_a, sku="BS-OK")
    batch = await _batch_with_services(client, headers_a, [svc["id"]], code="BS-OK")
    rec = await create_client_rec(client, headers_a)
    await _subscribe(client, headers_a, rec["id"], svc["id"])
    res = await _enroll(client, headers_a, rec["id"], batch["id"])
    assert res.status_code == 201, res.text


async def test_unsubscribed_client_is_refused(client, headers_a):
    svc = await create_service(client, headers_a, sku="BS-NO")
    batch = await _batch_with_services(client, headers_a, [svc["id"]], code="BS-NO")
    rec = await create_client_rec(client, headers_a)  # no subscription
    res = await _enroll(client, headers_a, rec["id"], batch["id"])
    assert res.status_code == 422
    assert "active subscription" in res.json()["detail"]


async def test_subscription_to_a_different_service_does_not_qualify(client, headers_a):
    wanted = await create_service(client, headers_a, sku="BS-WANT")
    other = await create_service(client, headers_a, sku="BS-OTHER")
    batch = await _batch_with_services(client, headers_a, [wanted["id"]], code="BS-DIFF")
    rec = await create_client_rec(client, headers_a)
    await _subscribe(client, headers_a, rec["id"], other["id"])
    res = await _enroll(client, headers_a, rec["id"], batch["id"])
    assert res.status_code == 422


async def test_ended_subscription_does_not_qualify(client, headers_a):
    svc = await create_service(client, headers_a, sku="BS-END")
    batch = await _batch_with_services(client, headers_a, [svc["id"]], code="BS-END")
    rec = await create_client_rec(client, headers_a)
    sub = await _subscribe(client, headers_a, rec["id"], svc["id"])
    await client.patch(f"/api/subscriptions/{sub['id']}", json={"status": "ended"}, headers=headers_a)
    res = await _enroll(client, headers_a, rec["id"], batch["id"])
    assert res.status_code == 422


async def test_serviceless_batch_stays_open(client, headers_a):
    """Backwards-compatible: a batch with no listed service admits anyone."""
    batch = await _batch_with_services(client, headers_a, [], code="BS-OPEN")
    rec = await create_client_rec(client, headers_a)  # no subscription at all
    res = await _enroll(client, headers_a, rec["id"], batch["id"])
    assert res.status_code == 201, res.text


async def test_batch_cannot_reference_another_orgs_service(client, headers_a, headers_b):
    """A new id-taking body field must 404 on a foreign tenant's id (§5.6)."""
    svc_b = await create_service(client, headers_b, sku="B-SVC")
    loc = await create_location(client, headers_a, code="L-X")
    ins = await create_instructor(client, headers_a)
    res = await client.post(
        "/api/batches",
        json={
            "name": "X", "code": "X-SVC", "status": "active",
            "location_id": loc["id"], "instructor_id": ins["id"],
            "service_ids": [svc_b["id"]],
        },
        headers=headers_a,
    )
    assert res.status_code == 404


async def _eligible(client, headers, batch_id):
    res = await client.get(f"/api/batches/{batch_id}/eligible-clients", headers=headers)
    assert res.status_code == 200, res.text
    return {c["name"] for c in res.json()}


async def test_eligible_clients_only_lists_subscribers(client, headers_a):
    svc = await create_service(client, headers_a, sku="EL-SVC")
    other = await create_service(client, headers_a, sku="EL-OTHER")
    batch = await _batch_with_services(client, headers_a, [svc["id"]], code="EL-B")

    yes = await create_client_rec(client, headers_a, name="Subscriber")
    await _subscribe(client, headers_a, yes["id"], svc["id"])
    no_sub = await create_client_rec(client, headers_a, name="No Sub")
    wrong = await create_client_rec(client, headers_a, name="Wrong Service")
    await _subscribe(client, headers_a, wrong["id"], other["id"])

    eligible = await _eligible(client, headers_a, batch["id"])
    assert "Subscriber" in eligible
    assert "No Sub" not in eligible
    assert "Wrong Service" not in eligible


async def test_eligible_excludes_already_enrolled(client, headers_a):
    svc = await create_service(client, headers_a, sku="EL2-SVC")
    batch = await _batch_with_services(client, headers_a, [svc["id"]], code="EL2-B")
    rec = await create_client_rec(client, headers_a, name="Already In")
    await _subscribe(client, headers_a, rec["id"], svc["id"])
    assert "Already In" in await _eligible(client, headers_a, batch["id"])

    await _enroll(client, headers_a, rec["id"], batch["id"])
    assert "Already In" not in await _eligible(client, headers_a, batch["id"])


async def test_open_batch_lists_every_client(client, headers_a):
    batch = await _batch_with_services(client, headers_a, [], code="EL3-B")
    await create_client_rec(client, headers_a, name="Anyone")
    assert "Anyone" in await _eligible(client, headers_a, batch["id"])


async def test_eligible_clients_is_org_scoped(client, headers_a, headers_b):
    svc = await create_service(client, headers_a, sku="EL4-SVC")
    batch = await _batch_with_services(client, headers_a, [svc["id"]], code="EL4-B")
    assert (
        await client.get(f"/api/batches/{batch['id']}/eligible-clients", headers=headers_b)
    ).status_code == 404


# ---------------------------------------------------------------- days of week


async def test_batch_days_of_week(client, headers_a):
    loc = await create_location(client, headers_a, code="DOW")
    ins = await create_instructor(client, headers_a)
    batch = await create_batch(
        client, headers_a, loc["id"], ins["id"], code="DOW-1",
        days_of_week=["Mon", "Wed", "Fri"],
    )
    assert batch["days_of_week"] == ["Mon", "Wed", "Fri"]

    got = (await client.get(f"/api/batches/{batch['id']}", headers=headers_a)).json()
    assert got["days_of_week"] == ["Mon", "Wed", "Fri"]

    res = await client.patch(
        f"/api/batches/{batch['id']}", json={"days_of_week": ["Tue", "Thu"]}, headers=headers_a
    )
    assert res.json()["days_of_week"] == ["Tue", "Thu"]


async def test_batch_days_default_empty(client, headers_a):
    loc = await create_location(client, headers_a, code="DOW2")
    ins = await create_instructor(client, headers_a)
    batch = await create_batch(client, headers_a, loc["id"], ins["id"], code="DOW-2")
    assert batch["days_of_week"] == []


async def test_batch_invalid_day_rejected(client, headers_a):
    loc = await create_location(client, headers_a, code="DOW3")
    ins = await create_instructor(client, headers_a)
    res = await client.post(
        "/api/batches",
        json={
            "name": "X", "code": "DOW-3", "status": "active",
            "location_id": loc["id"], "instructor_id": ins["id"],
            "days_of_week": ["Funday"],
        },
        headers=headers_a,
    )
    assert res.status_code == 422


# ---------------------------------------------------------------- one batch per client


async def _open_batch(client, headers, code):
    loc = await create_location(client, headers, code=f"L-{code}")
    ins = await create_instructor(client, headers)
    return await create_batch(client, headers, loc["id"], ins["id"], code=code)


async def test_client_cannot_join_a_second_batch(client, headers_a):
    b1 = await _open_batch(client, headers_a, "OB-1")
    b2 = await _open_batch(client, headers_a, "OB-2")
    rec = await create_client_rec(client, headers_a)
    assert (await _enroll(client, headers_a, rec["id"], b1["id"])).status_code == 201
    res = await _enroll(client, headers_a, rec["id"], b2["id"])
    assert res.status_code == 409
    assert "only one batch" in res.json()["detail"]


async def test_remove_from_batch_then_can_join_another(client, headers_a):
    b1 = await _open_batch(client, headers_a, "RM-1")
    b2 = await _open_batch(client, headers_a, "RM-2")
    rec = await create_client_rec(client, headers_a)
    e1 = (await _enroll(client, headers_a, rec["id"], b1["id"])).json()

    # remove from b1
    res = await client.delete(f"/api/enrollments/{e1['id']}", headers=headers_a)
    assert res.status_code == 204
    # now free to join b2
    assert (await _enroll(client, headers_a, rec["id"], b2["id"])).status_code == 201


async def test_remove_enrollment_is_org_scoped(client, headers_a, headers_b):
    b = await _open_batch(client, headers_a, "RM-ORG")
    rec = await create_client_rec(client, headers_a)
    e = (await _enroll(client, headers_a, rec["id"], b["id"])).json()
    assert (await client.delete(f"/api/enrollments/{e['id']}", headers=headers_b)).status_code == 404
    assert (await client.delete(f"/api/enrollments/{e['id']}", headers=headers_a)).status_code == 204
