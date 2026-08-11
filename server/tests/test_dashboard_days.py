"""Today's batches on the dashboard respect the batch's days of the week (§5.5)."""

from datetime import date

from tests.conftest import create_batch, create_instructor, create_location


async def _batch(client, headers, code, **kw):
    loc = await create_location(client, headers, code=f"L-{code}")
    ins = await create_instructor(client, headers)
    return await create_batch(client, headers, loc["id"], ins["id"], code=code, **kw)


async def _todays(client, headers):
    d = (await client.get("/api/dashboard", headers=headers)).json()
    return {b["code"] for b in d["todays_batches"]}


async def test_batch_only_shows_on_its_days(client, headers_a):
    weekday = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")[date.today().weekday()]
    other = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")[(date.today().weekday() + 1) % 7]

    await _batch(client, headers_a, "TODAY", days_of_week=[weekday])
    await _batch(client, headers_a, "NOTTODAY", days_of_week=[other])
    await _batch(client, headers_a, "ANYDAY")  # no days set

    shown = await _todays(client, headers_a)
    assert "TODAY" in shown          # scheduled for today
    assert "NOTTODAY" not in shown   # scheduled for a different day
    assert "ANYDAY" in shown         # unscheduled — still shown
