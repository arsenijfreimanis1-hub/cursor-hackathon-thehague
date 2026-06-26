# Workflows — Competitor Watchdog automation

**Owner:** Leo  
**Product:** [docs/PRODUCT.md](../../docs/PRODUCT.md)

## Workflows to build
| File | Purpose |
|------|---------|
| `exports/00-healthcheck-webhook.json` | ✅ Smoke test (import first) |
| `exports/01-schedule-scrape.json` | Cron → Apify → POST snapshot |
| `exports/02-diff-alert.json` | Compare snapshots → alert webhook |

## API targets (Tarik)
- `POST http://localhost:4000/webhooks/n8n` (dev)
- `POST {PUBLIC_WEBHOOK_URL}/webhooks/n8n` (via AJ's Mac mini tunnel)

Export JSON after every n8n save. Update root README Integration Contracts.
