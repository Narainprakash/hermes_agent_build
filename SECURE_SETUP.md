# Secure Credential Setup

This project uses local `.env` files for secrets. Real secret files are ignored by Git. Commit only the `.env.example` files.

## 1. Rotate any exposed credentials

If any real Discord, OpenRouter, Minimax, database, Kalshi, or Robinhood credentials were ever committed or shared, revoke and recreate them before running live.

## 2. Create local env files

From the repository root:

```powershell
Copy-Item .env.example .env
Copy-Item configs/main/.env.example configs/main/.env
Copy-Item configs/trader/.env.example configs/trader/.env
Copy-Item configs/predictor/.env.example configs/predictor/.env
```

Generate strong local values:

```powershell
# 32-byte hex value for POSTGRES_PASSWORD or API_SERVER_KEY
-join ((1..32) | ForEach-Object { '{0:X2}' -f (Get-Random -Maximum 256) })
```

Use the same database password in:

- `.env` → `POSTGRES_PASSWORD`
- `.env` → `DATABASE_URL`
- `configs/main/.env` → `BENKI_DB_URL`
- `configs/trader/.env` → `BENKI_DB_URL`
- `configs/predictor/.env` → `BENKI_DB_URL`

## 3. Kalshi credentials

Create a Kalshi API key from Kalshi account settings. Kalshi uses:

- `KALSHI_API_KEY_ID`
- RSA private key material

If Kalshi gave you an RSA key as text, save that text into a local ignored key file. The file extension can be `.pem`; the important part is the contents, usually including lines like:

```text
-----BEGIN RSA PRIVATE KEY-----
...
-----END RSA PRIVATE KEY-----
```

or:

```text
-----BEGIN PRIVATE KEY-----
...
-----END PRIVATE KEY-----
```

Recommended local layout:

```text
secrets/
  kalshi-private-key.pem
```

`secrets/` and `*.pem` are ignored by Git.

Set in `configs/predictor/.env`:

```text
KALSHI_API_KEY_ID=<your key id>
KALSHI_PRIVATE_KEY_PATH=/run/secrets/kalshi_private_key.pem
KALSHI_BASE_URL=https://external-api.kalshi.com/trade-api/v2
DRY_RUN=true
```

PowerShell-safe way to create the local file without committing it:

```powershell
New-Item -ItemType Directory -Force secrets
notepad secrets/kalshi-private-key.pem
```

Paste the full RSA private key into Notepad, save, then close it. Do not paste the key into chat or commit it.

Optional file permission hardening on Windows:

```powershell
icacls secrets\kalshi-private-key.pem /inheritance:r
icacls secrets\kalshi-private-key.pem /grant:r "$env:USERNAME:R"
```

To expose that file inside the predictor container, add a read-only mount when ready:

```yaml
# docker-compose.yml, benki-predictor volumes
- ./secrets/kalshi-private-key.pem:/run/secrets/kalshi_private_key.pem:ro
```

Keep `DRY_RUN=true` until you have verified end-to-end behavior.

## 4. Robinhood MCP details

The repository only stores the MCP server name/account identifier, not Robinhood passwords or session tokens.

Set in `configs/trader/.env`:

```text
ROBINHOOD_MCP_SERVER=robinhood
ROBINHOOD_ACCOUNT_ID=<optional account id or label>
DRY_RUN=true
```

Configure Robinhood authentication in your local MCP server setup, outside this repository. Do not place Robinhood login credentials, cookies, refresh tokens, or session files in this repo.

## 5. Safe defaults

- `FEATURE_TRADING=false` until Robinhood MCP is connected and tested.
- `FEATURE_PREDICTIONS=false` until Kalshi credentials are connected and tested.
- `DRY_RUN=true` in every agent env until paper trading is validated.

## 6. Verify before running

```powershell
git status --short
git ls-files -- .env configs/main/.env configs/trader/.env configs/predictor/.env secrets/
docker compose config --quiet
```

The `git ls-files` command should print nothing for real secret files.
