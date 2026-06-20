#!/usr/bin/env python3
"""Seed the Notion Observer specialist agent."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from jarvis.services.agent_registry import get_agent, register_agent
from jarvis.services.agent_types import AgentSpec


SPEC = AgentSpec(
    name="Notion Observer",
    purpose="Monitor screen activity, maintain Notion learning log, surface improvement opportunities for William.",
    instructions=(
        "You are the Notion Observer for William Agent.\n"
        "1. Read recent screen activity via the screen context API or injected SCREEN CONTEXT.\n"
        "2. Write structured observations to Notion when friction (🔴 gotcha) or decisions (🟤) appear.\n"
        "3. Propose concrete William self-improvements when repeated errors or context switches are detected.\n"
        "4. Plan before acting; batch Notion writes (max 5 per run).\n"
        "5. Never invent activity beyond OCR/screen evidence."
    ),
    trigger_phrases=["screen log", "what am I doing", "notion observer", "what was I doing"],
)


async def main() -> None:
    existing = await get_agent(SPEC.name)
    if existing:
        print(f"Notion Observer already exists (id={existing.id})")
        return
    created = await register_agent(SPEC)
    print(f"Created Notion Observer agent id={created.id}")


if __name__ == "__main__":
    asyncio.run(main())
