#!/usr/bin/env bash
# Start the full local stack: postgres (if down), FastAPI backend, Vite frontend.
# Backend and frontend run detached; logs and pids land in .run/
#
#   scripts/start.sh           # start everything, wait until healthy
#   scripts/start.sh --logs    # ...then tail both logs (ctrl-c leaves them running)

source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

TAIL=0
for arg in "$@"; do
  case "$arg" in
    --logs) TAIL=1 ;;
    -h|--help) sed -n '2,7p' "$0"; exit 0 ;;
    *) die "unknown option: $arg" ;;
  esac
done

[ -d "$ROOT/server/.venv" ]      || die "backend deps missing — run scripts/setup.sh first"
[ -d "$ROOT/web/app/node_modules" ] || die "frontend deps missing — run scripts/setup.sh first"

ensure_pg

start_svc() {
  local name="$1" port="$2" dir="$3"; shift 3
  if running "$name"; then
    ok "$name already running (pid $(cat "$(pid_file "$name")"))"
    return 0
  fi
  local existing; existing="$(port_pids "$port")"
  if [ -n "$existing" ]; then
    die "port $port is already in use by pid(s): $existing
  That's not a process this script started. Stop it yourself, or override the port."
  fi
  say "starting $name on port $port"
  ( cd "$dir" && exec "$@" ) > "$(log_file "$name")" 2>&1 &
  echo $! > "$(pid_file "$name")"
}

start_svc api "$API_PORT" "$ROOT/server" \
  uv run uvicorn app.main:app --port "$API_PORT" --reload
start_svc web "$WEB_PORT" "$ROOT/web/app" \
  npm run dev -- --port "$WEB_PORT" --strictPort

if wait_http "http://localhost:$API_PORT/healthz" api; then
  ok "backend healthy — http://localhost:$API_PORT/docs"
else
  warn "backend did not answer /healthz in time. Last lines of $(log_file api):"
  tail -20 "$(log_file api)" >&2
  exit 1
fi

if wait_http "http://localhost:$WEB_PORT/" web; then
  ok "frontend serving — http://localhost:$WEB_PORT"
else
  warn "frontend did not answer in time. Last lines of $(log_file web):"
  tail -20 "$(log_file web)" >&2
  exit 1
fi

echo
echo "  app       http://localhost:$WEB_PORT"
echo "  api docs  http://localhost:$API_PORT/docs"
echo "  logs      .run/api.log  .run/web.log"
echo "  stop      scripts/stop.sh"

if [ "$TAIL" = 1 ]; then
  echo
  tail -f "$(log_file api)" "$(log_file web)"
fi
