# Workflows (Dev B)

Export n8n JSON files to `exports/` after every save in n8n Cloud.

## Inventory

| File | Trigger | Purpose | Status |
|------|---------|---------|--------|
| `exports/00-healthcheck-webhook.json` | Webhook POST | Smoke test → pings team API `/webhooks/n8n` | Ready to import |

## Webhook URLs

Document all URLs in root `README.md` → Integration Contracts.
