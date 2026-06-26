# Ideation decision — pre-kickoff scoring

Team profile: full-stack web, mobile, automation (mixed). Prize track: undecided.  
Scored 1–5 per criterion from [IDEAS.md](IDEAS.md). **Higher = better.**

## Scoring matrix

| # | Idea | 12h demo | 2+ partners | Use tomorrow | Split 4 ways | Local appeal | **Total /25** |
|---|------|----------|-------------|--------------|--------------|--------------|---------------|
| 1 | Voice Lead Qualifier | 4 | 5 | 4 | 4 | 4 | **21** |
| 2 | Multilingual City Assistant | 3 | 4 | 4 | 3 | 5 | **19** |
| 3 | Competitor Watchdog | 5 | 4 | 5 | 5 | 2 | **21** |
| 4 | Micro-SaaS (Fluxzero) | 3 | 2 | 4 | 3 | 2 | **14** |
| 5 | Document-to-Action | 4 | 4 | 5 | 4 | 2 | **19** |
| 6 | AI Audio Briefing | 4 | 3 | 3 | 3 | 3 | **16** |

## Top 2 finalists

### 🥇 Finalist A: Voice Lead Qualifier (21 pts)
- **Why:** Uses ElevenLabs + Apify + n8n naturally; live voice demo wins rooms; maps cleanly to Dev A–D roles.
- **Risk:** Telephony integration — mitigate with ElevenLabs conversational agent + browser audio demo (no real phone required).
- **The Hague angle:** Scrape local businesses (dentists, gyms, rijksdienst) via Google Maps actor.

### 🥇 Finalist B: Competitor Watchdog (21 pts)
- **Why:** Highest demo reliability; Apify MCP makes data trivial; n8n for alerts; clear B2B story.
- **Risk:** Less "wow" than voice — mitigate with real-time diff UI and Slack/email alert in demo.
- **The Hague angle:** Monitor Dutch e-commerce or local competitor pricing.

## Recommendation for kickoff vote

| If team wants… | Pick |
|----------------|------|
| Maximum demo drama + ElevenLabs track | **Voice Lead Qualifier** |
| Safest 12h ship + Apify/n8n tracks | **Competitor Watchdog** |
| Crowd favorite / local story | **Multilingual City Assistant** (backup) |

## Decision at kickoff

**Chosen idea:** **Competitor Watchdog**  
**Date:** 2026-06-26 (pre-kickoff lock by AJ)  
**Rationale:** Apify + n8n + Mobbin activated; ElevenLabs/Fluxzero skipped; safest 12h ship with clear demo.

See [PRODUCT.md](PRODUCT.md) for full spec.
