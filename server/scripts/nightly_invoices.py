"""Nightly invoice job (§5.2): iterate organisations and generate missing invoices.
Run via cron:  cd server && uv run python -m scripts.nightly_invoices"""

import asyncio

import sqlalchemy as sa

from app.billing import generate_missing
from app.db import SessionLocal
from app.models import Organisation


async def main() -> None:
    async with SessionLocal() as session:
        orgs = (await session.scalars(sa.select(Organisation))).unique().all()
        total = 0
        for org in orgs:  # backups/exports and this job iterate per org (§5.6)
            created = await generate_missing(session, org)
            await session.commit()
            if created:
                print(f"{org.code}: {created} invoice(s) created")
            total += created
        print(f"done — {total} invoice(s) created")


if __name__ == "__main__":
    asyncio.run(main())
