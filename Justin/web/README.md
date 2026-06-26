# Frontend — Competitor Watchdog dashboard

**Owner:** Justin  
**Product:** [docs/PRODUCT.md](../../docs/PRODUCT.md)

## Build
```bash
cd Justin/web
npm create vite@latest . -- --template react-ts   # if not scaffolded yet
npm install && npm run dev
```

## MVP screens
1. **Dashboard** — list competitors + last scrape time
2. **Alerts feed** — `GET /alerts` from Tarik's API
3. **Add competitor** — form → `POST /competitors`

Env: `VITE_API_URL=http://localhost:4000`

Use Mobbin Pro for UI reference.
