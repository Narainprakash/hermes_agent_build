# Benki Multi-Agent System

Benki is a Dockerized Hermes multi-agent system for market research, prediction-market scanning, risk auditing, and dashboard monitoring.

Current default stack:

- `postgres` — PostgreSQL audit database
- `benki-main` — Orchestrator / commander agent
- `benki-predictor` — Kalshi prediction-market worker
- `benki-ui` — Web dashboard on port `3000`
- `benki-trader` — Robinhood MCP worker, present but disabled by default through the Compose profile `disabled`

> Safety default: keep `DRY_RUN=true`, `FEATURE_TRADING=false`, and live credentials disabled until end-to-end dry-run behavior is verified.

## Repository layout

- `docker-compose.yml` — service topology
- `init.sql` — PostgreSQL schema
- `configs/*/config.yaml` — Hermes/Discord agent prompts and plugin lists
- `configs/*/.env.example` — per-agent secret templates
- `plugins/` — Hermes tools for DB, risk, market data, Kalshi, Robinhood MCP, and sentiment
- `skills/` — agent procedures
- `cron/` — Hermes cron definitions/state
- `ui/` — Express dashboard
- `scripts/start-hermes-agent.sh` — shared container startup script
- `SECURE_SETUP.md` — credential handling notes

## Local quick start

1. Copy environment templates:

   ```bash
   cp .env.example .env
   cp configs/main/.env.example configs/main/.env
   cp configs/predictor/.env.example configs/predictor/.env
   cp configs/trader/.env.example configs/trader/.env
   ```

2. Generate secrets:

   ```bash
   openssl rand -hex 32
   ```

   Use strong generated values for `POSTGRES_PASSWORD`, `API_SERVER_KEY`, and `DASHBOARD_TOKEN`.

3. Make database URLs match the same password:

   ```text
   DATABASE_URL=postgresql://benki:<POSTGRES_PASSWORD>@postgres:5432/benki
   BENKI_DB_URL=postgresql://benki:<POSTGRES_PASSWORD>@postgres:5432/benki
   ```

4. Fill required Discord and LLM secrets in `configs/main/.env` and `configs/predictor/.env`.

5. Validate and start:

   ```bash
   docker compose config --quiet
   docker compose up -d --build
   docker compose ps
   ```

6. Open the dashboard:

   ```text
   http://localhost:3000
   ```

   If `DASHBOARD_TOKEN` is set, open `http://localhost:3000/?token=<DASHBOARD_TOKEN>` once to create an HttpOnly browser cookie. API requests also accept `Authorization: Bearer <DASHBOARD_TOKEN>`. For public VPS use, keep a reverse proxy with HTTPS and Basic Auth in front of the dashboard.

## Netcup VPS setup from a fresh Linux root machine

These steps assume a new Netcup VPS with root SSH access. Commands target Ubuntu/Debian. If the VPS image is not Ubuntu/Debian, install equivalent packages for your distribution.

### 1. SSH into the server

From your local machine:

```bash
ssh root@YOUR_VPS_IP
```

Change the root password immediately if the provider gave you an initial password:

```bash
passwd
```

### 2. Update the OS

```bash
apt update
apt -y upgrade
apt -y install ca-certificates curl gnupg git ufw fail2ban openssl nano htop jq
reboot
```

Reconnect after reboot:

```bash
ssh root@YOUR_VPS_IP
```

### 3. Create a non-root deploy user

```bash
adduser benki
usermod -aG sudo benki
```

Optional but recommended: configure SSH key login from your local machine. Preferably use ED25519 SHA 256 keys:

```bash
mkdir -p /home/benki/.ssh
nano /home/benki/.ssh/authorized_keys
chown -R benki:benki /home/benki/.ssh
chmod 700 /home/benki/.ssh
chmod 600 /home/benki/.ssh/authorized_keys
```

Paste your public key into `authorized_keys`.

### 4. Harden SSH and firewall

Open only SSH and the dashboard port. If you later use Nginx/Caddy with TLS, open ports 80/443 instead of exposing 3000 publicly.

```bash
ufw allow OpenSSH
ufw allow 3000/tcp
ufw enable
ufw status verbose
systemctl enable --now fail2ban
```

Recommended SSH hardening after key login works:

```bash
nano /etc/ssh/sshd_config
```

Set or confirm:

```text
PermitRootLogin prohibit-password
PasswordAuthentication no
PubkeyAuthentication yes
```

Then restart SSH:

```bash
systemctl restart ssh
```

Keep one existing SSH session open while testing a new login.

### 5. Install Docker Engine and Compose plugin

First detect the VPS OS. Netcup images are often Debian, and using the Ubuntu Docker repository on Debian causes `Package docker-ce is not available` errors.

```bash
. /etc/os-release
echo "$ID $VERSION_CODENAME"
```

Then install Docker with the repository that matches the detected OS:

```bash
apt -y remove docker docker-engine docker.io containerd runc podman-docker || true
apt -y install ca-certificates curl gnupg
install -m 0755 -d /etc/apt/keyrings

. /etc/os-release
case "$ID" in
   ubuntu|debian)
      DOCKER_OS="$ID"
      ;;
   *)
      echo "Unsupported OS ID: $ID. Use Docker's official install docs for this distro."
      exit 1
      ;;
esac

rm -f /etc/apt/sources.list.d/docker.list
curl -fsSL "https://download.docker.com/linux/${DOCKER_OS}/gpg" | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg
printf 'deb [arch=%s signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/%s %s stable\n' "$(dpkg --print-architecture)" "$DOCKER_OS" "$VERSION_CODENAME" > /etc/apt/sources.list.d/docker.list

apt update
apt-cache policy docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
apt -y install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
systemctl enable --now docker
usermod -aG docker benki
```

If `apt-cache policy docker-ce` still shows no candidate, the VPS image codename may not be supported by Docker yet. Use the convenience installer fallback:

```bash
curl -fsSL https://get.docker.com -o /tmp/get-docker.sh
sh /tmp/get-docker.sh
apt -y install docker-buildx-plugin docker-compose-plugin || true
systemctl enable --now docker
usermod -aG docker benki
```

Verify:

```bash
docker --version
docker compose version
```

Log out and back in as `benki` so Docker group membership applies:

```bash
su - benki
```

### 6. Deploy the repository

The deployment repository is:

```text
https://github.com/Narainprakash/hermes_agent_build
```

Before deploying on the VPS, sync your current local code to `origin`:

```bash
git status
git add .
git commit -m "Prepare Hermes agent VPS deployment"
git remote add origin https://github.com/Narainprakash/hermes_agent_build.git 2>/dev/null || git remote set-url origin https://github.com/Narainprakash/hermes_agent_build.git
git push -u origin main
```

If your default branch is `master`, replace `main` with `master`.

As user `benki`:

```bash
mkdir -p ~/apps
cd ~/apps
git clone https://github.com/Narainprakash/hermes_agent_build.git benki
cd benki
```

If you are uploading from your local machine instead of Git, use this fallback only when the GitHub repo is unavailable:

```bash
# run from local machine, not VPS
rsync -av --exclude '.git' --exclude '.env' --exclude 'node_modules' ./ root@YOUR_VPS_IP:/home/benki/apps/benki/
```

Then on the VPS:

```bash
chown -R benki:benki /home/benki/apps/benki
cd /home/benki/apps/benki
```

### 7. Create environment files

```bash
cp .env.example .env
cp configs/main/.env.example configs/main/.env
cp configs/predictor/.env.example configs/predictor/.env
cp configs/trader/.env.example configs/trader/.env
```

Generate secrets:

```bash
POSTGRES_PASSWORD_VALUE=$(openssl rand -hex 32)
API_SERVER_KEY_VALUE=$(openssl rand -hex 32)
DASHBOARD_TOKEN_VALUE=$(openssl rand -hex 32)
echo "POSTGRES_PASSWORD=$POSTGRES_PASSWORD_VALUE"
echo "API_SERVER_KEY=$API_SERVER_KEY_VALUE"
echo "DASHBOARD_TOKEN=$DASHBOARD_TOKEN_VALUE"
```

Edit `.env`:

```bash
nano .env
```

Set:

```text
POSTGRES_PASSWORD=<generated value>
DATABASE_URL=postgresql://benki:<same generated password>@postgres:5432/benki
API_SERVER_KEY=<generated value>
DASHBOARD_TOKEN=<generated value>
OPENROUTER_API_KEY=<your key if used>
MINIMAX_API_KEY=<your key if used>
FEATURE_TRADING=false
FEATURE_PREDICTIONS=false
```

Edit each agent env file:

```bash
nano configs/main/.env
nano configs/predictor/.env
nano configs/trader/.env
```

Minimum required values:

```text
DISCORD_TOKEN=<agent bot token>
OPENROUTER_API_KEY=<LLM provider key>
BENKI_DB_URL=postgresql://benki:<same generated password>@postgres:5432/benki
DRY_RUN=true
```

For the predictor, leave Kalshi disabled until ready:

```text
KALSHI_API_KEY_ID=
KALSHI_PRIVATE_KEY_PATH=
KALSHI_BASE_URL=https://external-api.kalshi.com/trade-api/v2
DRY_RUN=true
```

### 8. Optional Kalshi private key file

Only do this when prediction markets are ready. Never paste secrets into chat or commit them.

```bash
mkdir -p secrets
nano secrets/kalshi-private-key.pem
chmod 600 secrets/kalshi-private-key.pem
```

Set in `configs/predictor/.env`:

```text
KALSHI_API_KEY_ID=<your key id>
KALSHI_PRIVATE_KEY_PATH=/run/secrets/kalshi_private_key.pem
DRY_RUN=true
```

Add a read-only mount to `benki-predictor` in `docker-compose.yml` only when ready:

```yaml
- ./secrets/kalshi-private-key.pem:/run/secrets/kalshi_private_key.pem:ro
```

### 9. Validate config and start services

```bash
cd /home/benki/apps/benki
docker compose config --quiet
docker compose pull
docker compose up -d --build postgres
docker compose ps
```

Wait for PostgreSQL to become healthy, then start the active stack:

```bash
docker compose up -d --build benki-main benki-predictor benki-ui
docker compose ps
```

View logs:

```bash
docker compose logs -f postgres
docker compose logs -f benki-main
docker compose logs -f benki-predictor
docker compose logs -f benki-ui
```

### 10. Access the dashboard

Direct access:

```text
http://YOUR_VPS_IP:3000
```

If `DASHBOARD_TOKEN` is enabled, open this URL once to create a browser session cookie:

```text
http://YOUR_VPS_IP:3000/?token=<DASHBOARD_TOKEN>
```

API calls also accept `Authorization: Bearer <DASHBOARD_TOKEN>`. For normal browser access on a public VPS, the recommended setup is still a reverse proxy with HTTPS and Basic Auth.

### 11. Recommended HTTPS reverse proxy with Caddy

Install Caddy:

```bash
apt -y install debian-keyring debian-archive-keyring apt-transport-https
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' > /etc/apt/sources.list.d/caddy-stable.list
apt update
apt -y install caddy
```

Point a DNS A record such as `benki.example.com` to your VPS IP.

Generate a Basic Auth password hash:

```bash
caddy hash-password
```

Edit Caddyfile:

```bash
nano /etc/caddy/Caddyfile
```

Example:

```text
benki.example.com {
  basicauth {
    admin <PASTE_CADDY_HASHED_PASSWORD>
  }
  reverse_proxy 127.0.0.1:3000
}
```

Reload:

```bash
systemctl reload caddy
ufw allow 80/tcp
ufw allow 443/tcp
ufw delete allow 3000/tcp
```

Then use:

```text
https://benki.example.com
```

### 12. Enable prediction markets after dry-run checks

After the dashboard is healthy and Discord bots are responding:

1. Set root `.env`:

   ```text
   FEATURE_PREDICTIONS=true
   ```

## VPS Details (local notes only)

Do not commit real VPS identifiers, root passwords, SSH private keys, provider credentials, or deployment-only notes to GitHub. Keep the concrete Netcup host name, IP addresses, and passwords in a private password manager or an ignored local notes file.

Use placeholders in committed docs:

- Host name: `<your-vps-hostname>`
- IPv4: `<your-vps-ipv4>`
- IPv6: `<your-vps-ipv6>`
- Username: `<deploy-user>` or `root` for initial bootstrap only

Use these values only when connecting to the server or configuring DNS/firewall rules.

## Installing Hermes runtime on the VPS

These steps install the Hermes agent runtime used by the `benki-*` services and prepare the system to run the Dockerized images.

1. Ensure Docker Engine and Compose plugin are installed (see step 5 above).

2. (Optional) If you prefer to run the Hermes gateway locally (not in Docker), install Python and the Hermes package. These instructions assume a Debian/Ubuntu VPS:

```bash
apt -y install python3 python3-venv python3-pip
python3 -m venv ~/hermes-venv
source ~/hermes-venv/bin/activate
pip install --upgrade pip
# If there is a published Hermes package, install it. Otherwise install from your local source.
# Example (replace with actual package or git url if available):
# pip install nousresearch-hermes

# If you have the source in the repo, install in editable mode:
pip install -e /home/benki/apps/benki
deactivate
```

3. Run the Hermes gateway inside Docker (recommended for reproducible deployments). From the repo root on the VPS:

```bash
# build images (Dockerfile for ui and any local agent images)
docker compose build --pull

# Start only postgres and gateway for initial warmup
docker compose up -d postgres
docker compose up -d benki-main

# Monitor logs while the gateway initializes
docker compose logs -f benki-main
```

4. Verify the Hermes HTTP gateway is accepting requests (default port `8642` inside the agent image):

```bash
# from the VPS, test via the local API server if enabled
curl -sS -H "Authorization: Bearer $API_SERVER_KEY" http://127.0.0.1:8642/health
```

5. When the gateway is healthy, bring up the rest of the stack:

```bash
docker compose up -d --build benki-predictor benki-ui
docker compose ps
```

6. Follow the rest of the README (cron, secrets, and Kalshi steps) to enable prediction markets and trading when ready.

Security note: keep `DRY_RUN=true` and `FEATURE_TRADING=false` until you've verified paper-mode operations and manually enabled keys/credentials.
   ```

2. Set `docker-compose.yml` or agent environment to pass `FEATURE_PREDICTIONS=true` where needed.
3. Keep `DRY_RUN=true`.
4. Restart:

   ```bash
   docker compose up -d --build benki-main benki-predictor benki-ui
   ```

### 13. Enable trader only after Robinhood MCP is ready

The trader is disabled by default. When Robinhood MCP is configured and dry-run tested:

```bash
docker compose --profile disabled up -d benki-trader
```

Keep `DRY_RUN=true` until you have verified:

- Discord directive parsing
- `risk_check` approval/rejection
- order dry-run output
- database logging
- daily P&L update behavior

### 14. Maintenance commands

Status:

```bash
docker compose ps
```

Logs:

```bash
docker compose logs --tail=200 benki-main benki-predictor benki-ui
```

Restart active stack:

```bash
docker compose restart benki-main benki-predictor benki-ui
```

Update deployment:

```bash
git pull
docker compose config --quiet
docker compose up -d --build
```

Backup PostgreSQL:

```bash
mkdir -p ~/backups
docker compose exec -T postgres pg_dump -U benki -d benki > ~/backups/benki-$(date +%F-%H%M).sql
```

Restore PostgreSQL backup into a fresh DB only after stopping agents:

```bash
docker compose stop benki-main benki-predictor benki-ui
docker compose exec -T postgres psql -U benki -d benki < ~/backups/backup-file.sql
```

### 15. Pre-live safety checklist

- [ ] `docker compose config --quiet` passes.
- [ ] Real `.env` files are not committed.
- [ ] `git ls-files -- .env configs/main/.env configs/predictor/.env configs/trader/.env secrets/` prints nothing.
- [ ] `DRY_RUN=true` in all agent env files.
- [ ] `FEATURE_TRADING=false` until Robinhood MCP is tested.
- [ ] `FEATURE_PREDICTIONS=false` until Kalshi credentials are tested.
- [ ] Dashboard is protected by Caddy Basic Auth or equivalent.
- [ ] PostgreSQL backup command works.
- [ ] Risk audit log receives entries for rejected and approved dry-run actions.
- [ ] Daily P&L updates and circuit breaker behavior are verified.

## Notes on root password handling

Do not store the Netcup root password in this repository or paste it into chat. Use it only to log in and install SSH keys. After key login works, disable password login and operate through the `benki` deploy user.
