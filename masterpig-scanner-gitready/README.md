# MasterPig Scanner (Fast Async, Gap-Limit, Recursive)

**Warning:** Never commit your `.env` with real keys to a public repo.

## Features
- Async scanner with `aiohttp` and batching
- Gap-limit (default 20) on both external (0) and change (1) chains
- Deep recursive follow: when an address has transactions, fetch the peer addresses it interacted with and scan them too (deduped)
- HD support for `xpub`, `ypub`, `zpub`, `tpub` (auto-converts to neutral form before derivation)
- Pluggable providers: **Tatum** (address & tx data), **Blockchair** (xpub & address fallback)
- MongoDB storage (Motor) with fast upserts and indices
- FastAPI service for metrics (`/stats`) and controls (`/start_scan`, `/stop_scan`)

## Quick start
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # fill in keys
uvicorn app.main:app --reload
```

### Docker (with MongoDB)
```bash
docker compose up -d
# service: http://localhost:8080
```

## CLI
```bash
python -m app.cli scan --xpub <xpub/ypub/zpub/tpub> --max-gap 20 --max-depth 2
```

## Providers
- Tatum: address history & balances
- Blockchair: rich xpub/address data (optional key)

You can add more providers in `app/providers/*`.


## Reverse Proxy (Caddy)
The included `Caddyfile` terminates TLS for `masterpig.donthink.so` and proxies to the API container.
Update the email and domain, then:
```bash
docker compose up -d
```
Caddy will auto-provision certificates with Let's Encrypt.

## Frontend
A minimal dashboard is served at `/` (FastAPI static). It polls `/metrics` every 5s and draws a bar chart with Chart.js.


## GitHub: quick publish
```bash
git init
git checkout -b main
git remote add origin git@github.com:feather-weight/masterpig-scanner.git
git add .
git commit -m "Initial commit"
git push -u origin main
```
> Ensure your `.env` is **NOT** committed. The included `.gitignore` ignores it by default.
