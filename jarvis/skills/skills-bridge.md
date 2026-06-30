# Skills Bridge

William integrates multiple agent skill ecosystems. Use the right skill for each task:

| Domain | When to use | Install |
|--------|-------------|---------|
| CAD | 3D models, gears, robotics, STEP/STL | `npx skills install earthtojake/text-to-cad` |
| GSD | Spec-driven builds, phased delivery | Built into build pipeline |
| Web automation | Scraping, forms, browser tasks | `pip install helium` |
| Media | Video edit, ffmpeg, Remotion | `brew install ffmpeg` |
| MCP tools | Filesystem, APIs, NullClaw tools | Configure `.cursor/mcp.json` |

## How they work together

1. **Build pipeline** detects domains from your prompt and injects matching skills into slice agents.
2. **Global skills** from `~/.agents/skills/` are discovered automatically (GSD, CAD, etc.).
3. **MCP servers** from Cursor + NullClaw configs are passed to Cursor SDK agents.
4. **PRD registry** keeps names consistent across CAD parts, API modules, and media assets.

## Voice shortcuts

- "build project: planetary gear assembly" → CAD + GSD domains
- "build: scrape product prices from site" → web automation domain
- "build: promo video with captions" → media domain

When multiple domains apply, slices are ordered: scaffold → domain work → integration.
