# Mac mini — integration hub

The Mac mini pulls the GitHub repo and runs shared infrastructure so 4 laptops can focus on Cursor.

## First-time setup

```bash
cd mac-mini
cp .env.example .env    # fill secrets — never commit
chmod +x *.sh
./setup.sh
```

## After every teammate push

```bash
./sync-from-github.sh
```

Or cron every 2 minutes during hackathon:
```bash
*/2 * * * * cd /path/to/cursor-hackathon-thehague/mac-mini && ./sync-from-github.sh >> /tmp/hackathon-sync.log 2>&1
```

## Services (docker-compose.yml)

| Service | Port | Notes |
|---------|------|-------|
| postgres | 5432 | user/pass/db: hackathon |
| redis | 6379 | optional queues |

## Public webhooks (cloudflared)

1. Install: `brew install cloudflared` (or download from Cloudflare)
2. Quick tunnel: `cloudflared tunnel --url http://localhost:4000`
3. Copy HTTPS URL → root `README.md` → `PUBLIC_WEBHOOK_URL`
4. Dev B uses this for n8n webhook triggers pointing at local API

## SSH access for team

Enable **Remote Login** on Mac mini (System Settings → Sharing).
Teammates can `ssh user@mac-mini-ip` to tail logs.

## Secrets

`mac-mini/.env` is gitignored. Sync keys from team password manager:
- APIFY_TOKEN
- ELEVENLABS_API_KEY
- N8N_API_KEY
