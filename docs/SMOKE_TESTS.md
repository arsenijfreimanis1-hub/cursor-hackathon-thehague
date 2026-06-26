# Integration smoke tests

Verify partner stack before / during hackathon build.

## Run locally

```bash
cp .env.example .env.local   # add APIFY_TOKEN, ELEVENLABS_API_KEY after perk activation
chmod +x scripts/smoke-test/*.sh scripts/open-perk-activation.sh mac-mini/*.sh
./scripts/smoke-test/run-all.sh
```

## What each test checks

| Test | Requires | Pass criteria |
|------|----------|---------------|
| API `/health` | Node/npm | Returns `{"status":"ok"}` |
| n8n webhook | Node/npm | `POST /webhooks/n8n` returns `{"received":true}` |
| Apify API | `APIFY_TOKEN` | `/v2/users/me` returns username |
| ElevenLabs TTS | `ELEVENLABS_API_KEY` | Writes `apps/voice/assets/smoke-test.mp3` |

## Apify MCP (Cursor)

1. Open repo in Cursor
2. Settings → MCP → confirm `apify` server from `.cursor/mcp.json`
3. In agent chat: *"Search Apify store for Google Maps scraper"*
4. OAuth sign-in when prompted

## n8n Cloud (manual)

1. Redeem voucher → create workflow with **Webhook** trigger
2. Set URL to `{PUBLIC_WEBHOOK_URL}/webhooks/n8n` (from Mac mini tunnel)
3. Import starter: `apps/workflows/exports/00-healthcheck-webhook.json`

## Last run

| Date | API | n8n webhook | Apify | ElevenLabs | Notes |
|------|-----|-------------|-------|------------|-------|
| 2026-06-26 | ✅ | ✅ | SKIP | SKIP | Local tests pass; cloud tests need keys in `.env.local` |
