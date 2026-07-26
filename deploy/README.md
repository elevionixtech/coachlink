# Deploying CoachLink

Single-VM deployment: **PostgreSQL + FastAPI + nginx on one Debian 12 machine**, sized
for a GCP `e2-micro` (the always-free tier). nginx terminates TLS, serves the built
frontend, and proxies `/api` to a uvicorn systemd service; Postgres runs locally and is
never exposed to the internet.

The production instance runs at **https://coachlink.elevionixtech.com** (VM `coachlink`,
zone `us-east1-b`, project `coachlink-503612`).

## Layout on the VM

| Path | What |
|---|---|
| `/opt/coachlink/server` | backend source + `.venv` (owned by the login user) |
| `/opt/coachlink/server/.env` | `COACHLINK_DATABASE_URL`, `COACHLINK_JWT_SECRET`, `COACHLINK_CORS_ORIGINS` |
| `/var/www/coachlink` | built frontend (nginx root) |
| `/opt/coachlink-dbpass`, `/opt/coachlink-jwt` | generated secrets (mode 600) |
| `coachlink.service` | systemd unit → `uvicorn app.main:app` on `127.0.0.1:8200` |

Secrets are generated **on the box** by `provision.sh` and never leave it — nothing
secret lives in this repo.

## First-time deploy

Prerequisites: `gcloud` authenticated, project with **billing enabled**, and the
`compute.googleapis.com` API on.

```bash
PROJECT=coachlink-503612
ZONE=us-east1-b
gcloud config set project $PROJECT
gcloud services enable compute.googleapis.com

# 1. Firewall: allow HTTP/HTTPS to tagged instances (SSH is open by default).
gcloud compute firewall-rules create allow-http  --allow=tcp:80  --target-tags=http-server
gcloud compute firewall-rules create allow-https --allow=tcp:443 --target-tags=https-server

# 2. VM: e2-micro in a US region qualifies for the always-free tier.
gcloud compute instances create coachlink \
  --zone=$ZONE --machine-type=e2-micro \
  --image-family=debian-12 --image-project=debian-cloud \
  --boot-disk-size=30GB --boot-disk-type=pd-standard \
  --tags=http-server,https-server

# 3. Build + package + upload the source.
( cd web/app && npm run build )
tar -czf /tmp/coachlink-deploy.tgz \
  --exclude='server/.venv' --exclude='**/__pycache__' \
  --exclude='**/.pytest_cache' --exclude='**/.ruff_cache' --exclude='server/.env' \
  server web/app/dist
gcloud compute scp /tmp/coachlink-deploy.tgz deploy/provision.sh coachlink:/tmp/ --zone=$ZONE

# 4. Provision (installs Postgres/nginx/uv, migrates, seeds, starts everything).
gcloud compute ssh coachlink --zone=$ZONE --command='
  rm -rf /tmp/coachlink-src && mkdir -p /tmp/coachlink-src &&
  tar xzf /tmp/coachlink-deploy.tgz -C /tmp/coachlink-src &&
  sudo bash /tmp/provision.sh'
```

At this point the app answers on `http://<VM_IP>`.

### TLS (Let's Encrypt)

Point a DNS **A record** for your domain at the VM's external IP (Cloudflare: use
**DNS-only / grey-cloud**, not proxied, so the HTTP-01 challenge reaches the box). Then:

```bash
gcloud compute ssh coachlink --zone=$ZONE --command='
  sudo apt-get install -y certbot python3-certbot-nginx &&
  sudo sed -i "s/server_name _;/server_name YOUR_DOMAIN;/" /etc/nginx/sites-available/coachlink &&
  sudo nginx -t && sudo systemctl reload nginx &&
  sudo certbot --nginx -d YOUR_DOMAIN --non-interactive --agree-tos -m YOUR_EMAIL --redirect'
```

certbot installs the cert, switches nginx to 443, adds the HTTP→HTTPS redirect, and sets
up auto-renewal. Finally point the app's CORS at the domain:

```bash
gcloud compute ssh coachlink --zone=$ZONE --command='
  sudo sed -i "s|^COACHLINK_CORS_ORIGINS=.*|COACHLINK_CORS_ORIGINS=[\"https://YOUR_DOMAIN\"]|" /opt/coachlink/server/.env &&
  sudo systemctl restart coachlink'
```

## Updating a running deploy

From the repo root, after committing your changes:

```bash
deploy/redeploy.sh
```

It builds the frontend, uploads, swaps the code in **preserving `.env`**, runs
`alembic upgrade head`, and restarts the service. Override `VM=` / `ZONE=` if needed.

## Operations

```bash
# logs / status
gcloud compute ssh coachlink --zone=us-east1-b --command='sudo journalctl -u coachlink -n 50 --no-pager'
gcloud compute ssh coachlink --zone=us-east1-b --command='systemctl is-active coachlink nginx postgresql'

# database backup (keep a copy off the VM)
gcloud compute ssh coachlink --zone=us-east1-b --command='sudo -u postgres pg_dump -Fc coachlink > /tmp/coachlink.dump'
gcloud compute scp coachlink:/tmp/coachlink.dump ./coachlink-$(date +%F).dump --zone=us-east1-b
```

## Notes

- **Cost:** an `e2-micro` + 30 GB standard disk in a US region is $0 on the always-free
  tier, within the monthly egress allowance. Watch egress and a retained static IP.
- **RAM:** 1 GB is tight; `provision.sh` adds a 2 GB swapfile. The frontend is built
  locally and uploaded (not built on the VM) to avoid OOM.
- **Postgres** binds `127.0.0.1` only. To reach it from a local tool, use an SSH tunnel
  (e.g. DBeaver's built-in SSH tab via `~/.ssh/google_compute_engine`).
- **Seed logins** (`coachlink123`) are public knowledge — change them after first login
  via the in-app "Change password", and lock SSH (port 22) to your IP if desired.
