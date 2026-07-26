#!/usr/bin/env bash
# Push the current local code to the running VM: build the frontend, package the
# backend + built frontend, upload, swap it in (preserving .env), re-sync deps, restart.
# Run from the repo root:  deploy/redeploy.sh
set -euo pipefail

ZONE="${ZONE:-us-east1-b}"
VM="${VM:-coachlink}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP="$(mktemp -d)"

echo "==> building frontend"
( cd "$ROOT/web/app" && npm run build )

echo "==> packaging"
tar -czf "$TMP/coachlink-deploy.tgz" -C "$ROOT" \
  --exclude='server/.venv' --exclude='**/__pycache__' --exclude='**/.pytest_cache' \
  --exclude='**/.ruff_cache' --exclude='server/.env' \
  server web/app/dist

echo "==> uploading"
gcloud compute scp "$TMP/coachlink-deploy.tgz" "$VM:/tmp/" --zone="$ZONE"

echo "==> deploying on VM"
gcloud compute ssh "$VM" --zone="$ZONE" --command='
  set -e
  rm -rf /tmp/coachlink-src && mkdir -p /tmp/coachlink-src
  tar xzf /tmp/coachlink-deploy.tgz -C /tmp/coachlink-src 2>/dev/null
  sudo cp /opt/coachlink/server/.env /tmp/coachlink.env.bak
  sudo rm -rf /opt/coachlink/server && sudo cp -r /tmp/coachlink-src/server /opt/coachlink/server
  sudo cp /tmp/coachlink.env.bak /opt/coachlink/server/.env
  sudo chown -R "$USER":"$USER" /opt/coachlink
  sudo rm -rf /var/www/coachlink/* && sudo cp -r /tmp/coachlink-src/web/app/dist/. /var/www/coachlink/
  sudo chown -R www-data:www-data /var/www/coachlink
  cd /opt/coachlink/server && /usr/local/bin/uv sync >/dev/null
  # Apply any new migrations before restarting the API.
  /usr/local/bin/uv run alembic upgrade head
  sudo systemctl restart coachlink && sleep 4
  systemctl is-active coachlink
'
rm -rf "$TMP"
echo "==> redeployed"
