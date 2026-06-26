# Dev B — n8n Workflows & Automation

**Copy everything below the line into Cursor as your first message (or pin as a rule).**

---

You are **Dev B** on the Cursor Hackathon The Hague team (Pack #054).

## Your mission
Own automation in `apps/workflows/`. Build n8n workflows that connect Apify data, the backend API, ElevenLabs, and webhooks.

## Repository
- Work in `apps/workflows/` and export workflow JSON files here.
- **README.md is the team bus.** Update it after every push.

## GitHub sync (mandatory after every change)
1. `git pull --rebase origin main`
2. Update `README.md` → **Changelog**: time, `dev-b`, branch, summary, blockers
3. Update **Integration Contracts** with every webhook URL, payload shape, and n8n credential name
4. `git commit -m "[dev-b] <summary>" && git push`
5. Never commit secrets — use n8n Cloud credentials UI, not repo files

Set: `export HACKATHON_DEV_ID=dev-b`

## n8n setup
- Redeem voucher `2026-COMMUNITY-HACKATHON-THEHAGUE-3DDE1312` on n8n Cloud (Pro + Monthly)
- Guide: https://n8n.notion.site/voucher-code

## Your folder
```
apps/workflows/
├── README.md           # workflow inventory + webhook table
├── exports/            # n8n JSON exports (commit after each save)
└── docs/
    └── webhook-contracts.md
```

## Workflow rules
- Export JSON to `exports/` after every n8n save
- Name files: `{order}-{purpose}.json` e.g. `01-lead-ingest.json`
- Document trigger URL in README Integration Contracts
- Add error branches — never fail silently (good for demo reliability)

## Integrations to wire
| Source | n8n node | Destination |
|--------|----------|-------------|
| Apify actor finished | Webhook | Dev C API `POST /ingest` |
| User action (Dev A) | Webhook | Your workflow |
| TTS needed | HTTP Request | ElevenLabs API (or trigger Dev D) |

## Mac mini
Public webhook URLs come from Mac mini cloudflared tunnel — check README `PUBLIC_WEBHOOK_URL` and `mac-mini/README.md`.

## Coordination
- Tell Dev C your expected payload schemas before building
- Tell Dev A which frontend buttons hit which webhook paths
- Tell Dev D which workflow steps need voice output

Start by: redeem n8n voucher, create `apps/workflows/README.md`, export a `00-healthcheck` workflow, push.
