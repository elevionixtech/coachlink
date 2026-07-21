# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

CoachLink — multi-tenant class & client management (services, clients, instructors, batches,
enrollments, subscriptions, invoices). The authoritative behavioral spec is
`docs/CoachLink Spec.dc.html` (§-references in code comments point into it); read it before
changing business rules. FastAPI backend in `server/`, React frontend in `web/app/`.

## Commands

Backend (from `server/`, uses uv):

```bash
uv run pytest                          # full suite (~3s, SQLite in-memory)
uv run pytest tests/test_billing.py -k test_generate_missing   # single test
uv run ruff check . && uv run ruff format .
uv run alembic upgrade head            # apply migrations
uv run alembic revision --autogenerate -m "..."   # after model changes
uv run python -m scripts.seed          # demo data (idempotent; logins in README)
uv run uvicorn app.main:app --port 8200 --reload
```

Frontend (from `web/app/`):

```bash
npm run dev        # Vite dev server, proxies /api → localhost:8200
npm run build      # tsc -b + vite build (use this as the type-check)
npm run gen:api    # regenerate src/api/schema.d.ts from the running backend
```

After changing any Pydantic schema or route, run `npm run gen:api` (backend must be up)
— frontend types in `src/api/types.ts` are aliases into the generated `schema.d.ts`.

Local environment quirks: Postgres runs on port **5433** (not 5432); ports 8000/8100 are
taken by other projects, hence the API on **8200**. Scripts must run as modules from
`server/` (`python -m scripts.seed`), not by file path.

## Architecture

### Tenancy — the load-bearing invariant

Every domain endpoint takes the `OrgUser` dependency (`app/deps.py: require_org_user`),
which rejects platform (org-less) users with 403 and yields the caller's org resolved
from the user row — org id is **never** accepted from the client. Rules enforced app-layer
and guarded by `tests/test_isolation.py`:

- Foreign-tenant ids answer **404, never 403** — use `routers/common.py: get_owned_or_404`
  for any id in a path or body (it also filters soft-deleted rows via `archived_at`).
- Top-level tables (service, client, instructor, location, batch) carry `org_id`; child
  tables (deliverables, notes, subscriptions, enrollments, invoices) do **not** — tenancy
  checks walk up through the parent (e.g. `subscription.client.org_id`).
- Uniqueness is per-org composite (org_id + sku/code/username), checked explicitly in
  routers to return 409 with a message rather than a bare IntegrityError.
- JWT carries only the user id; the user row is re-fetched every request, so org expiry
  (`deps.ensure_org_not_expired`, the single §5.7 chokepoint) takes effect immediately.
  Superadmin is never blocked and is 403'd from all domain APIs.

Any new endpoint must extend the isolation suite — that is the spec's own requirement.

### Portable models (Postgres prod, SQLite tests)

`app/models.py` deliberately avoids Postgres-only types so the test suite runs on
in-memory SQLite: enums are `sa.Enum(..., native_enum=False)` (varchar + CHECK), arrays
(`skills`, `pricing_options`) and `settings` are `JSON().with_variant(JSONB, "postgresql")`,
ids are `sa.Uuid` with client-side `uuid4` defaults, timestamps are Python-side defaults
(no DB triggers). Keep new columns portable or the tests break. Alembic
(`alembic/versions/`) is the schema source of truth; `db/schema.sql` is just a pg_dump
snapshot to refresh after migrations.

### Billing engine (`app/billing.py`)

Invoice generation walks billing periods per active subscription from `start_date` to
today. Key decisions:

- Idempotency comes from the `(subscription_id, period_label)` unique constraint plus
  skipping labels that already exist — never generate by date math alone.
- Period N is computed as `nth_period_start(start, interval, n)` **anchored to the
  subscription start**, not by stepping from the previous period — stepping drifts after
  month-end clamping (Jan 31 → Feb 28 → Mar 28 bug).
- Invoice numbers use the per-org counter `organisation.next_invoice_seq`; amounts are
  the discounted rate rounded to the whole rupee (`effective_rate`).
- "Overdue" is derived (`due` AND `issue_date + org.invoice_grace_days < today`), never
  stored.

### Frontend conventions

- Auth state in `src/store/auth.ts` (zustand, persisted); `src/api/client.ts` attaches
  the bearer token and transparently retries once after a refresh on 401.
- Route guards in `App.tsx`: superadmin is confined to `/platform`, org users everywhere
  else — mirrors the backend role split.
- UI primitives live in `src/components/ui.tsx` and implement the Elevionix design system
  (tokens mapped into Tailwind via `@theme` in `src/index.css`, imported from
  `web/elevionix-design-system/`). House rules: orange only on the single committing
  action per screen; IBM Plex Mono for ids/dates/amounts; ₹ with Indian digit grouping
  via `src/lib/format.ts`; statuses always written out, never color-only; no icons/emoji.
- Forms are shared between create and edit (e.g. `ClientForm` in `Clients.tsx` is reused
  by `ClientDetail.tsx`); API errors surface through `errorMessage()` which flattens
  FastAPI 422 field errors.

### Gotchas

- FastAPI ≥0.139 mounts routers lazily (`_IncludedRouter`) — `app.routes` looks empty
  until startup; verify routing with a TestClient request, not route introspection.
- `tests/conftest.py` hashes the shared password once at import (bcrypt is slow) and
  provides `headers_a` / `headers_b` / `headers_root` fixtures plus `create_*` helpers —
  use them rather than re-rolling setup.
- Vite reads the design-system CSS from outside its root; `server.fs.allow` in
  `vite.config.ts` makes that legal — don't "fix" the `../..` import.
