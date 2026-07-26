#!/usr/bin/env bash
# Provision CoachLink on a single Debian 12 VM: PostgreSQL + FastAPI + nginx.
#
# Runs on the VM, as root (via sudo). Idempotent — safe to re-run; it preserves the
# generated secrets (DB password, JWT secret) once created, and re-syncs code/deps.
#
# Expects the app source already unpacked at /tmp/coachlink-src, containing:
#   server/            the FastAPI backend (app/, alembic/, scripts/, pyproject.toml)
#   web/app/dist/      the built frontend (npm run build output)
#
# See deploy/README.md for how to create the VM and upload the source.
set -euo pipefail

APP_USER="${SUDO_USER:-$(whoami)}"
APP_HOME="/opt/coachlink"
WEB_ROOT="/var/www/coachlink"
SRC="/tmp/coachlink-src"
EXTERNAL_IP="$(curl -s -H 'Metadata-Flavor: Google' \
  http://metadata.google.internal/computeMetadata/v1/instance/network-interfaces/0/access-configs/0/external-ip || echo '')"

echo "==> user=$APP_USER  ip=${EXTERNAL_IP:-unknown}"
[ -d "$SRC/server" ] || { echo "missing $SRC/server — upload the source first"; exit 1; }

# --- swap (e2-micro has only 1 GB RAM) -------------------------------------
if [ ! -f /swapfile ]; then
  echo "==> creating 2G swap"
  fallocate -l 2G /swapfile
  chmod 600 /swapfile
  mkswap /swapfile
  swapon /swapfile
  echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

# --- packages --------------------------------------------------------------
echo "==> installing packages"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq postgresql nginx curl ca-certificates >/dev/null

# --- postgres role + db (password generated once, kept) --------------------
echo "==> configuring postgres"
DB_PASS_FILE=/opt/coachlink-dbpass
if [ ! -f "$DB_PASS_FILE" ]; then
  openssl rand -hex 24 > "$DB_PASS_FILE"
  chmod 600 "$DB_PASS_FILE"
fi
DB_PASS="$(cat "$DB_PASS_FILE")"
sudo -u postgres psql -tc "SELECT 1 FROM pg_roles WHERE rolname='coachlink'" | grep -q 1 || \
  sudo -u postgres psql -c "CREATE ROLE coachlink LOGIN PASSWORD '${DB_PASS}';"
sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='coachlink'" | grep -q 1 || \
  sudo -u postgres psql -c "CREATE DATABASE coachlink OWNER coachlink;"

# --- code (frontend to nginx root, backend to /opt) ------------------------
echo "==> installing code"
rm -rf "$APP_HOME/server" "$WEB_ROOT"
mkdir -p "$APP_HOME" "$WEB_ROOT"
cp -r "$SRC/server" "$APP_HOME/server"
cp -r "$SRC/web/app/dist/." "$WEB_ROOT/"
chown -R "$APP_USER":"$APP_USER" "$APP_HOME"
chown -R www-data:www-data "$WEB_ROOT"

# --- app env (JWT secret generated once, kept) -----------------------------
JWT_FILE=/opt/coachlink-jwt
[ -f "$JWT_FILE" ] || { openssl rand -hex 32 > "$JWT_FILE"; chmod 600 "$JWT_FILE"; }
JWT_SECRET="$(cat "$JWT_FILE")"
# Preserve an existing .env (e.g. a CORS origin already set to the real domain).
if [ ! -f "$APP_HOME/server/.env" ]; then
  cat > "$APP_HOME/server/.env" <<ENV
COACHLINK_DATABASE_URL=postgresql+asyncpg://coachlink:${DB_PASS}@localhost:5432/coachlink
COACHLINK_JWT_SECRET=${JWT_SECRET}
COACHLINK_CORS_ORIGINS=["http://${EXTERNAL_IP}"]
ENV
fi
chown "$APP_USER":"$APP_USER" "$APP_HOME/server/.env"
chmod 600 "$APP_HOME/server/.env"

# --- uv (system-wide) ------------------------------------------------------
if ! command -v uv >/dev/null 2>&1; then
  echo "==> installing uv"
  curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR=/usr/local/bin sh >/dev/null
fi
UV=/usr/local/bin/uv

# --- deps, migrations, seed (as the app user) ------------------------------
echo "==> uv sync (provisions Python 3.12 + deps)"
sudo -u "$APP_USER" bash -c "cd $APP_HOME/server && $UV sync"
echo "==> alembic upgrade head"
sudo -u "$APP_USER" bash -c "cd $APP_HOME/server && $UV run alembic upgrade head"
# Seed only a fresh database (no organisations yet). The seed script is idempotent,
# but this keeps re-runs from touching an org you have already created.
if [ "$(sudo -u postgres psql coachlink -tAc 'SELECT count(*) FROM organisation' 2>/dev/null || echo 0)" = "0" ]; then
  echo "==> seed (fresh database)"
  sudo -u "$APP_USER" bash -c "cd $APP_HOME/server && $UV run python -m scripts.seed"
fi

# --- systemd service -------------------------------------------------------
echo "==> systemd service"
cat > /etc/systemd/system/coachlink.service <<UNIT
[Unit]
Description=CoachLink API
After=network.target postgresql.service
Requires=postgresql.service

[Service]
User=${APP_USER}
WorkingDirectory=${APP_HOME}/server
ExecStart=${UV} run uvicorn app.main:app --host 127.0.0.1 --port 8200
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
UNIT
systemctl daemon-reload
systemctl enable --now coachlink
systemctl restart coachlink

# --- nginx (HTTP; certbot adds TLS later, see README) ----------------------
echo "==> nginx"
cat > /etc/nginx/sites-available/coachlink <<'NGINX'
server {
    listen 80 default_server;
    server_name _;
    root /var/www/coachlink;
    index index.html;

    location /api {
        proxy_pass http://127.0.0.1:8200;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    location = /healthz { proxy_pass http://127.0.0.1:8200/healthz; }

    # index.html must always revalidate so a new deploy shows up without a hard refresh;
    # the hashed assets under /assets are safe to cache forever.
    location = /index.html { add_header Cache-Control "no-cache"; }
    location / { try_files $uri $uri/ /index.html; }
}
NGINX
ln -sf /etc/nginx/sites-available/coachlink /etc/nginx/sites-enabled/coachlink
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl reload nginx

echo "==> waiting for API"
for _ in $(seq 1 20); do curl -sf -o /dev/null http://127.0.0.1:8200/healthz && break; sleep 2; done
echo "DONE — http://${EXTERNAL_IP:-<vm-ip>}  (run certbot for TLS, see deploy/README.md)"
