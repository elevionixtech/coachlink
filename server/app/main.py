from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import (
    admin,
    auth,
    batches,
    clients,
    dashboard,
    enrollments,
    instructors,
    invoices,
    locations,
    members,
    org,
    services,
    subscriptions,
)

app = FastAPI(title="CoachLink API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for router in (
    auth.router,
    org.router,
    members.router,
    admin.router,
    services.router,
    clients.router,
    instructors.router,
    locations.router,
    batches.router,
    enrollments.router,
    subscriptions.router,
    invoices.router,
    dashboard.router,
):
    app.include_router(router, prefix="/api")


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}
