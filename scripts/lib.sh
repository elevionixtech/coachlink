#!/usr/bin/env bash
# Shared helpers for the local dev scripts. Not meant to be run directly.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_DIR="$ROOT/.run"

# Defaults mirror the checked-in config: app/config.py, web/app/vite.config.ts.
# Override by exporting before invoking, e.g. API_PORT=9000 scripts/start.sh
PG_PORT="${PG_PORT:-5433}"
PG_HOST="${PG_HOST:-localhost}"
DB_NAME="${DB_NAME:-coachlink}"
API_PORT="${API_PORT:-8200}"
WEB_PORT="${WEB_PORT:-5173}"
BREW_PG="${BREW_PG:-postgresql@16}"

mkdir -p "$RUN_DIR"

say()  { printf '\033[1;34m==>\033[0m %s\n' "$*"; }
ok()   { printf '\033[1;32m  ok\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m  !!\033[0m %s\n' "$*" >&2; }
die()  { printf '\033[1;31merror:\033[0m %s\n' "$*" >&2; exit 1; }

need() { command -v "$1" >/dev/null 2>&1 || die "$1 not found on PATH. $2"; }

pg_up() { pg_isready -h "$PG_HOST" -p "$PG_PORT" -q 2>/dev/null; }

# Bring up the shared Homebrew cluster if it isn't listening yet.
# The cluster is shared with other projects, so we only ever start it, never stop it.
ensure_pg() {
  if pg_up; then
    ok "postgres already listening on $PG_PORT"
    return 0
  fi
  say "starting postgres ($BREW_PG)"
  need brew "Install Homebrew, or start postgres yourself on port $PG_PORT."
  brew services start "$BREW_PG" >/dev/null
  for _ in $(seq 1 30); do
    pg_up && { ok "postgres listening on $PG_PORT"; return 0; }
    sleep 1
  done
  die "postgres did not come up on $PG_PORT within 30s.
  The cluster's port lives in \$(brew --prefix)/var/$BREW_PG/postgresql.conf — it must say 'port = $PG_PORT'.
  Logs: \$(brew --prefix)/var/log/$BREW_PG.log"
}

# pid file helpers -----------------------------------------------------------

pid_file() { echo "$RUN_DIR/$1.pid"; }
log_file() { echo "$RUN_DIR/$1.log"; }

# Is the pid in $1's pid file alive?
running() {
  local f; f="$(pid_file "$1")"
  [ -f "$f" ] || return 1
  local pid; pid="$(cat "$f" 2>/dev/null || true)"
  [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null
}

port_pids() { lsof -ti "tcp:$1" -sTCP:LISTEN 2>/dev/null || true; }

# Poll a URL until it answers, or give up.
wait_http() {
  local url="$1" name="$2" tries="${3:-40}"
  for _ in $(seq 1 "$tries"); do
    curl -sf -o /dev/null "$url" && return 0
    sleep 1
  done
  return 1
}
