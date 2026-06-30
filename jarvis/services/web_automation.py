"""Lightweight browser automation via Helium (falls back gracefully)."""

from __future__ import annotations

import asyncio
import logging
import subprocess
import sys
from typing import Any

log = logging.getLogger("jarvis.web_automation")


def _helium_available() -> bool:
    try:
        import helium  # noqa: F401
        return True
    except ImportError:
        return False


async def automate(
    script: str,
    *,
    url: str = "",
    headless: bool = True,
    timeout_sec: int = 120,
) -> dict[str, Any]:
    """
    Run a Helium automation script or a simple URL navigation.

    script: Python code using helium API, or empty to just open url.
    url: optional starting URL injected as `START_URL` variable.
    """
    if not _helium_available():
        return {
            "ok": False,
            "error": "helium not installed — run: pip install helium",
            "hint": "Or use cursor_agent.run with the web-automation skill",
        }

    preamble = (
        "from helium import *\n"
        f"START_URL = {url!r}\n"
        f"HEADLESS = {headless}\n"
    )
    if url and not script.strip():
        body = (
            "start_chrome(headless=HEADLESS)\n"
            "go_to(START_URL)\n"
            "print('navigated to', START_URL)\n"
        )
    else:
        body = script

    full_script = preamble + body

    def _run() -> dict[str, Any]:
        try:
            proc = subprocess.run(
                [sys.executable, "-c", full_script],
                capture_output=True,
                text=True,
                timeout=timeout_sec,
                check=False,
            )
            return {
                "ok": proc.returncode == 0,
                "stdout": (proc.stdout or "")[:3000],
                "stderr": (proc.stderr or "")[:1000],
                "code": proc.returncode,
            }
        except subprocess.TimeoutExpired:
            return {"ok": False, "error": "timeout", "code": -1}
        except Exception as exc:
            return {"ok": False, "error": str(exc), "code": -1}

    return await asyncio.to_thread(_run)
