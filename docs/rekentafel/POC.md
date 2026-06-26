# Rekentafel PoC — Cheat Sheet

Everything you need for the hackathon demo. **No William/Jarvis required.**

## Two devices

| Device | What it does |
|--------|----------------|
| **Mac mini** | Runs the server (database, API, websites, public internet link) |
| **MacBook** | Builds the waiter iPhone app in Xcode (one time) |

Guests use **Safari only** — they scan a printed QR code. No app install for guests.

---

## Part A — Mac mini (server)

### One-time prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) running
- Node.js 22+ and pnpm (`npm install -g pnpm`)
- A free [Mollie](https://www.mollie.com) account (test mode — no real money)

### Start the demo (one command)

```bash
cd /Users/willy/jarvis-core
chmod +x scripts/rekentafel-poc.sh
./scripts/rekentafel-poc.sh
```

Wait until you see **"Rekentafel PoC is running"** with a public URL like `https://xxxx.trycloudflare.com`.

### Add Mollie test key

1. Open [Mollie Dashboard → Developers → API keys](https://www.mollie.com/dashboard/developers/api-keys)
2. Copy the **Test** key (`test_...`)
3. Edit `.env` on the Mac mini:
   ```
   MOLLIE_API_KEY=test_your_key_here
   ```
   (`MOLLIE_WEBHOOK_URL` is set automatically by the PoC script.)
4. Restart the API: press Ctrl+C, then run `./scripts/rekentafel-poc.sh` again  
   — or in another terminal: `pnpm dev:api`

### Print QR codes

Open on the Mac mini:

```
data/qr-codes/rekentafel-qr-sheet.pdf
```

Print the A4 sheet — 4 QR codes (T01–T04). Stick one on each demo table.

You can also download from the waiter app: **Vloerplan → QR printen**.

---

## Part B — MacBook (waiter iPhone app)

### Roles

| Machine | Job |
|---------|-----|
| **Mac mini** | Runs API + database (`pnpm dev:api` or `./scripts/rekentafel-poc.sh`) |
| **MacBook** | Builds the iOS app once per API URL change |
| **iPhone** | Same Wi‑Fi as Mac mini («Titaan Members») |

### One-time prerequisites

- Xcode from the App Store
- Node.js 22+ and pnpm
- iPhone connected by USB (trust this computer)

### Clone and build (MacBook)

```bash
git clone git@github.com:arsenijfreimanis1-hub/cursor-hackathon-thehague.git
cd cursor-hackathon-thehague
pnpm install
```

Get the Mac mini LAN IP from the mini (`./scripts/print-network-urls.sh`) — usually `10.43.0.40`.

**One command** — bakes the API URL into the app and syncs Xcode:

```bash
./scripts/prepare-waiter-ios.sh 10.43.0.40
pnpm --filter @rekentafel/waiter-mobile cap:open:ios
```

In Xcode: select your **iPhone** → **Run** (▶).

Manual alternative: copy `apps/staff-web/.env.production.example` → `.env.production`, edit `VITE_API_BASE_URL`, then build + `cap sync`.

### Log in on the app

- Email: `waiter@demo.rekentafel.nl`
- Password: anything (dev mode)

### If you see “No connection”

1. **Mac mini:** API must be running — `curl http://10.43.0.40:3000/v1/health` should return `{"status":"ok"}`
2. **MacBook:** App was likely built with `localhost` — re-run `./scripts/prepare-waiter-ios.sh 10.43.0.40` and Run in Xcode again
3. **iPhone:** Must be on the same Wi‑Fi as the Mac mini

---

## Part C — Run the demo

1. **Waiter (iPhone app):** Tap **T01** → **Gezeten** → add bill items (name + price) → **Activeer betaling**
2. **Guest (any phone):** Scan **T01** QR → enter name → claim items → **Pay**
3. **Mollie test checkout** opens → choose a test payment method → pay (fake money)
4. **Waiter app** shows which items are claimed vs **Vrij** (free)
5. Table moves to **Betaald** when fully paid

Repeat for T02–T04 if you want.

---

## Table states

| State | Meaning |
|-------|---------|
| Dormant | Empty table |
| Gezeten | Guests seated |
| Besteld | Bill has items |
| Klaar om te betalen | Guests can join and split |
| Betaald | Bill paid |

---

## Troubleshooting

**`DATABASE_URL not found`**  
Run from repo root. Ensure `.env` exists (`cp .env.example .env`).

**QR codes show localhost**  
Re-run `./scripts/rekentafel-poc.sh` so the public URL is detected, or set `PUBLIC_BASE_URL` in `.env` and run `pnpm generate:qr`.

**Waiter app can't load tables**  
Check `VITE_API_BASE_URL` in `apps/staff-web/.env.production` matches the Mac mini public URL.

**Mollie checkout fails**  
Ensure `MOLLIE_API_KEY` starts with `test_` and API was restarted after editing `.env`.

**Public URL changed**  
Cloudflare quick tunnel URLs change when restarted. Re-run PoC script, update `.env.production` on MacBook, rebuild staff-web, `cap sync` again.

---

## Android (after iPhone demo)

```bash
pnpm --filter @rekentafel/waiter-mobile cap:open:android
```

Requires Android Studio. Same API URL config as iOS.
