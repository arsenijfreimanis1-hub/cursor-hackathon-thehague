# Teammate onboarding — send this to your 3 devs

## 1. Clone the repo (after lead publishes to GitHub)

```bash
git clone https://github.com/arsenijfreimanis1-hub/cursor-hackathon-thehague.git
cd cursor-hackathon-thehague
cp .env.example .env.local   # add your API keys — never commit
export HACKATHON_DEV_ID=dev-X  # see table below
```

## 2. Activate your perks (30 min)

Follow [docs/PERK_ACTIVATION.md](docs/PERK_ACTIVATION.md):

| Perk | Action |
|------|--------|
| Cursor Pro | https://cursor.com/referral?code=YSKZL8N3HWQL |
| Apify | Code `30CURSOR` at console.apify.com |
| Mobbin | Code `CURSORHACKATHONNE26` at mobbin.com |
| ElevenLabs | Discord `#coupon-codes` + your Luma email |
| WhatsApp | https://chat.whatsapp.com/Hpmqgv7CzwIAtXbJ7f1Eo0 |

## 3. Paste your Cursor prompt

Open Cursor in the cloned repo. Copy **the entire file** for your role into the first agent message:

| Role | Prompt file | Folder |
|------|-------------|--------|
| Frontend / mobile | `prompts/dev-a-frontend.md` | `apps/web/` |
| n8n automation | `prompts/dev-b-n8n.md` | `apps/workflows/` |
| Backend + Apify | `prompts/dev-c-backend.md` | `apps/api/` |
| Voice + pitch | `prompts/dev-d-voice.md` | `apps/voice/` |

## 4. How we stay in sync

- **README.md** = team bus. Update Changelog after every push.
- **Auto-push hook** is in `.cursor/hooks.json` — enable Hooks in Cursor settings.
- Always: `git pull --rebase origin main` before coding.

## 5. Mac mini

Lead runs `mac-mini/sync-from-github.sh` after your pushes to wire webhooks and Docker services.
