"""Seed the dev database: platform superadmin, a plan, and a demo organisation
with sample catalogue, clients, batches and billing.

Run:  cd server && uv run python -m scripts.seed
Logins (password for all: coachlink123):
  PLATFORM / root      — platform superadmin
  AURA / admin         — org admin of Aura Yoga Studio
  AURA / staff         — org staff
"""

import asyncio
from datetime import date, time, timedelta
from decimal import Decimal

import sqlalchemy as sa

from app.billing import generate_missing
from app.db import SessionLocal
from app.models import (
    AppUser,
    Batch,
    BatchStatus,
    BillingInterval,
    Client,
    ContactNote,
    DeliveryMode,
    Enrollment,
    Instructor,
    LifecycleStage,
    Location,
    Organisation,
    Role,
    Service,
    ServiceDeliverable,
    ServiceType,
    Subscription,
    SubscriptionPlan,
)
from app.security import hash_password

PASSWORD = "coachlink123"


async def main() -> None:
    async with SessionLocal() as session:
        if await session.scalar(sa.select(Organisation.id).where(Organisation.code == "AURA")):
            print("already seeded — AURA exists")
            return

        pw = hash_password(PASSWORD)

        root = AppUser(name="Platform Root", username="root", password_hash=pw, role=Role.superadmin)
        plan = SubscriptionPlan(
            name="Growth", amount=Decimal("4999"), no_of_days=365,
            description="Annual platform subscription",
        )
        session.add_all([root, plan])
        await session.flush()

        today = date.today()
        org = Organisation(
            name="Aura Yoga Studio",
            code="AURA",
            plan_id=plan.id,
            subscription_starts_on=today,
            subscription_ends_on=today + timedelta(days=plan.no_of_days),
        )
        session.add(org)
        await session.flush()

        admin = AppUser(org_id=org.id, name="Ananya Desai", username="admin", password_hash=pw, role=Role.admin)
        staff = AppUser(org_id=org.id, name="Rohan Kulkarni", username="staff", password_hash=pw, role=Role.staff)
        session.add_all([admin, staff])

        hatha = Service(
            org_id=org.id, name="Hatha Yoga — Monthly", sku="HATHA-M",
            service_type=ServiceType.subscription, delivery_mode=DeliveryMode.offline,
            billing_interval=BillingInterval.monthly, rate=Decimal("3000"),
            max_capacity=15,
            deliverables=[ServiceDeliverable(name="Hatha yoga classes", quantity=12, unit="classes")],
        )
        personal = Service(
            org_id=org.id, name="Personal Training — Quarterly", sku="PT-Q",
            service_type=ServiceType.subscription, delivery_mode=DeliveryMode.hybrid,
            billing_interval=BillingInterval.quarterly, rate=Decimal("18000"),
            deliverables=[ServiceDeliverable(name="1-on-1 sessions", quantity=24, unit="sessions")],
        )
        workshop = Service(
            org_id=org.id, name="Inversions Workshop", sku="WKSP-INV",
            service_type=ServiceType.one_time, delivery_mode=DeliveryMode.offline,
            billing_interval=BillingInterval.na, rate=Decimal("1500"),
        )
        session.add_all([hatha, personal, workshop])

        meera = Instructor(
            org_id=org.id, name="Meera Nair", date_of_birth=date(1990, 3, 12),
            phone="98450 11223", skills=["Hatha", "Vinyasa", "Pranayama"],
            experience_at_joining=Decimal("6.0"), joining_date=date(2023, 4, 1),
            certifications="RYT-500",
        )
        arjun = Instructor(
            org_id=org.id, name="Arjun Menon", date_of_birth=date(1987, 11, 2),
            phone="98801 44556", skills=["Ashtanga", "Strength"],
            experience_at_joining=Decimal("9.5"), joining_date=date(2024, 1, 10),
        )
        session.add_all([meera, arjun])

        koramangala = Location(
            org_id=org.id, name="Koramangala Studio", code="KRM", type="Studio",
            address="80 Feet Rd, Koramangala", capacity_per_batch=15, parallel_batches=2,
        )
        indiranagar = Location(
            org_id=org.id, name="Indiranagar Studio", code="IND", type="Studio",
            address="100 Feet Rd, Indiranagar", capacity_per_batch=10, parallel_batches=1,
        )
        session.add_all([koramangala, indiranagar])
        await session.flush()

        morning = Batch(
            org_id=org.id, name="Morning Hatha", code="HATHA-AM", status=BatchStatus.active,
            location_id=koramangala.id, instructor_id=meera.id,
            start_date=today - timedelta(days=45), end_date=today + timedelta(days=320),
            start_time=time(7, 0), end_time=time(8, 15),
        )
        evening = Batch(
            org_id=org.id, name="Evening Vinyasa", code="VIN-PM", status=BatchStatus.active,
            location_id=indiranagar.id, instructor_id=arjun.id,
            start_date=today - timedelta(days=20), end_date=today + timedelta(days=160),
            start_time=time(18, 30), end_time=time(19, 45),
        )
        session.add_all([morning, evening])

        asha = Client(
            org_id=org.id, name="Asha Rao", name_hint="Marathon runner", phone="98860 12345",
            email="asha@example.com", lead_source="Referral",
            lifecycle_stage=LifecycleStage.customer,
        )
        vikram = Client(
            org_id=org.id, name="Vikram Iyer", phone="99000 67890",
            lead_source="Instagram", lifecycle_stage=LifecycleStage.customer,
        )
        leela = Client(
            org_id=org.id, name="Leela Sharma", email="leela@example.com",
            lead_source="Walk-in", lifecycle_stage=LifecycleStage.lead, do_not_call=True,
        )
        session.add_all([asha, vikram, leela])
        await session.flush()

        session.add_all([
            Subscription(client_id=asha.id, service_id=hatha.id,
                         start_date=today - timedelta(days=75), discount_pct=Decimal("10")),
            Subscription(client_id=vikram.id, service_id=personal.id,
                         start_date=today - timedelta(days=30)),
            Enrollment(client_id=asha.id, batch_id=morning.id, start_date=today - timedelta(days=40)),
            Enrollment(client_id=vikram.id, batch_id=evening.id, start_date=today - timedelta(days=15)),
            ContactNote(client_id=leela.id, date=today - timedelta(days=3), channel="Call",
                        text="Interested in morning batches; will visit for a trial on Saturday.",
                        author_id=admin.id),
        ])
        await session.flush()

        created = await generate_missing(session, org)
        await session.commit()
        print(f"seeded — org AURA, {created} invoice(s) generated. Password for all: {PASSWORD}")


if __name__ == "__main__":
    asyncio.run(main())
