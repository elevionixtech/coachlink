#!/usr/bin/env bash
# Stop the local stack (backend + frontend).
#
# Postgres is deliberately left running: the Homebrew cluster is shared with other
# projects on this machine. Pass --with-db if you really want it stopped.
#
#   scripts/stop.sh             # stop backend + frontend
#   scripts/stop.sh --with-db   # ...and stop the shared postgres cluster too

source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

WITH_DB=0
for arg in "$@"; do
  case "$arg" in
    --with-db) WITH_DB=1 ;;
    -h|--help) sed -n '2,9p' "$0"; exit 0 ;;
    *) die "unknown option: $arg" ;;
  esac
done

# Stop a service by its pid file: TERM the process group, then KILL if it lingers.
stop_svc() {
  local name="$1" port="$2"
  local f; f="$(pid_file "$name")"

  if running "$name"; then
    local pid; pid="$(cat "$f")"
    say "stopping $name (pid $pid)"
    # Negative pid targets the group, so uvicorn's --reload child and npm's vite
    # child go down with the parent instead of being orphaned onto the port.
    kill -TERM -"$pid" 2>/dev/null || kill -TERM "$pid" 2>/dev/null || true
    for _ in $(seq 1 10); do
      running "$name" || break
      sleep 1
    done
    if running "$name"; then
      warn "$name ignored SIGTERM, sending SIGKILL"
      kill -KILL -"$pid" 2>/dev/null || kill -KILL "$pid" 2>/dev/null || true
      sleep 1
    fi
    ok "$name stopped"
  elif [ -f "$f" ]; then
    ok "$name was not running (stale pid file)"
  else
    ok "$name was not running"
  fi
  rm -f "$f"

  # Children can outlive the parent and keep the port. Clean up what's left.
  local leftover; leftover="$(port_pids "$port")"
  if [ -n "$leftover" ]; then
    warn "port $port still held by pid(s) $leftover — killing"
    echo "$leftover" | xargs kill -TERM 2>/dev/null || true
    sleep 1
    leftover="$(port_pids "$port")"
    [ -n "$leftover" ] && echo "$leftover" | xargs kill -KILL 2>/dev/null || true
  fi
}

stop_svc web "$WEB_PORT"
stop_svc api "$API_PORT"

if [ "$WITH_DB" = 1 ]; then
  say "stopping postgres ($BREW_PG) — shared cluster, other projects will lose it too"
  brew services stop "$BREW_PG" >/dev/null && ok "postgres stopped"
else
  pg_up && ok "postgres left running on $PG_PORT (use --with-db to stop it)"
fi

echo
ok "stack stopped"
