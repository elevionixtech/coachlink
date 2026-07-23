#!/usr/bin/env bash
# One-time (and safe-to-repeat) local setup: dependencies, database, schema, demo data.
# Run this once after cloning, and again after pulling changes that touch deps or migrations.
#
#   scripts/setup.sh            # deps + migrations + seed
#   scripts/setup.sh --no-seed  # skip the demo data

source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

SEED=1
for arg in "$@"; do
  case "$arg" in
    --no-seed) SEED=0 ;;
    -h|--help) sed -n '2,8p' "$0"; exit 0 ;;
    *) die "unknown option: $arg" ;;
  esac
done

say "checking prerequisites"
need uv "Install with: brew install uv"
need node "Install Node 20+ with: brew install node"
need npm "Ships with Node."
need psql "Install with: brew install $BREW_PG"
ok "uv $(uv --version | awk '{print $2}'), node $(node -v), psql $(psql --version | awk '{print $3}')"

ensure_pg

say "ensuring database '$DB_NAME' exists"
if psql -h "$PG_HOST" -p "$PG_PORT" -d postgres -tAc \
     "select 1 from pg_database where datname='$DB_NAME'" | grep -q 1; then
  ok "database already exists — leaving it alone"
else
  createdb -h "$PG_HOST" -p "$PG_PORT" "$DB_NAME"
  ok "created database $DB_NAME"
fi

say "installing backend dependencies"
(cd "$ROOT/server" && uv sync)

say "applying migrations"
(cd "$ROOT/server" && uv run alembic upgrade head)
ok "schema at $(cd "$ROOT/server" && uv run alembic current 2>/dev/null | tail -1)"

if [ "$SEED" = 1 ]; then
  say "seeding demo data (idempotent)"
  (cd "$ROOT/server" && uv run python -m scripts.seed)
fi

say "installing frontend dependencies"
(cd "$ROOT/web/app" && npm install --no-fund --no-audit)

echo
ok "setup complete — start the app with: scripts/start.sh"
