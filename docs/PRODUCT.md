# Competitor Watchdog — team product spec

**Status:** LOCKED — all 4 teammates build this one product.

## One-liner
Monitor competitor pricing, ads, and reviews. Get alerted when something changes.

## Demo journey (3 minutes)
1. Justin's dashboard shows tracked competitors and last scrape time
2. Tarik's API returns live scraped product prices / review snippets (Apify)
3. Leo's n8n workflow detects a price change → webhook → alert row on dashboard
4. AJ shows Mac mini tunnel + integration status (optional: Slack/email alert)

## Partner stack in use
| Partner | Role in product | Owner |
|---------|-----------------|-------|
| **Apify** | Scrape competitor sites, Google Maps, social | Tarik |
| **n8n** | Schedule scrapes, diff detection, alerts | Leo |
| **Mobbin** | UI patterns for dashboard | Justin |
| **Cursor** | Build everything | All |
| ElevenLabs | *Stretch:* read alert aloud when activated | Leo |
| Fluxzero | *Not using* | — |

## Data model (MVP)
```json
{
  "competitor": { "id", "name", "url", "niche" },
  "snapshot": { "competitorId", "scrapedAt", "prices": [], "reviews": [] },
  "alert": { "competitorId", "field", "oldValue", "newValue", "detectedAt" }
}
```

## API contracts (Tarik owns — update README when changed)
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Liveness |
| `/integrations/status` | GET | Apify + n8n connectivity |
| `/competitors` | GET, POST | List / add competitor |
| `/competitors/:id/snapshots` | GET | Latest scrape data |
| `/webhooks/n8n` | POST | Receive n8n events |

## n8n workflows (Leo owns)
1. `01-schedule-scrape` — cron → call Apify actor → POST snapshot to API
2. `02-diff-alert` — on new snapshot → compare → if changed → POST `/webhooks/n8n`
3. `00-healthcheck-webhook` — smoke test (already in repo)

## The Hague angle (pitch)
Track local Dutch e-commerce or service businesses (e.g. bike shops, gyms in Den Haag).

## Out of scope for 12h
- Real phone calls, Fluxzero backend, user auth beyond demo
- More than 3 tracked competitors in demo
