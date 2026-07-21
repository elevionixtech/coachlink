# CoachLink

Class & client management platform for businesses that run regular enrolled classes
(fitness/yoga studios first, but the domain model is vertical-agnostic). Multi-tenant:
organisations are the tenant boundary, with org-code login and a superadmin platform surface.

Full specification: `docs/CoachLink Spec.dc.html` · data model: `docs/CoachLink ER Diagram.dc.html`

## Stack

- **Backend** (`server/`): Python 3.12+, FastAPI, SQLAlchemy 2.0 (async) + PostgreSQL,
  Alembic migrations, JWT auth (access + refresh), managed with [uv](https://docs.astral.sh/uv/)
- **Frontend** (`web/app/`): React 19 + TypeScript + Vite, Tailwind CSS 4 with the
  Elevionix design-system theme (`web/elevionix-design-system/`), TanStack Query,
  Zustand, Axios with types generated from the backend's OpenAPI spec

## Prerequisites

- PostgreSQL 16+
- Python 3.12+ with `uv`
- Node 20+

## Setup

### 1. Database

```bash
createdb coachlink
```

The backend reads `COACHLINK_DATABASE_URL` (see `server/app/config.py`); the default is
`postgresql+asyncpg://localhost:5433/coachlink`. If your Postgres runs elsewhere
(e.g. the default port 5432), set it in `server/.env`:

```
COACHLINK_DATABASE_URL=postgresql+asyncpg://localhost:5432/coachlink
```

### 2. Backend

```bash
cd server
uv sync                      # install dependencies
uv run alembic upgrade head  # create the schema
uv run python -m scripts.seed  # optional: demo org + platform admin
uv run uvicorn app.main:app --port 8200 --reload
```

API docs at http://localhost:8200/docs. `db/schema.sql` is a `pg_dump` snapshot of the
Alembic-managed schema, kept for reference — Alembic is the source of truth.

Seed logins (password for all: `coachlink123`):

| Org code | Username | Role |
|---|---|---|
| `PLATFORM` | `root` | platform superadmin |
| `AURA` | `admin` | org admin, Aura Yoga Studio |
| `AURA` | `staff` | org staff |

### 3. Frontend

```bash
cd web/app
npm install
npm run dev
```

Open the printed URL (http://localhost:5173 by default). The Vite dev server proxies
`/api` to the backend — the target port lives in `web/app/vite.config.ts` (8200).

After changing backend schemas, regenerate the API types (backend must be running):

```bash
npm run gen:api
```

## Tests & tooling

```bash
cd server
uv run pytest        # full suite — isolation, login matrix, billing (SQLite in-memory)
uv run ruff check .  # lint
uv run ruff format . # format
```

## Recurring jobs

Nightly invoice generation (idempotent, iterates per org):

```bash
cd server && uv run python -m scripts.nightly_invoices
```

## Project layout

```
db/schema.sql        pg_dump snapshot of the schema
docs/                spec, ER diagram, UI prototype
server/              FastAPI backend (app/, alembic/, scripts/, tests/)
web/app/             React frontend
web/elevionix-design-system/   shared design tokens & guidelines
```
