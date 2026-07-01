"""OpenClaw gateway health probes."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import httpx

from jarvis.config import settings

_GATEWAY_LOG = Path.home() / ".openclaw" / "logs" / "gateway.log"
_TMP_LOG_DIR = Path("/tmp/openclaw")


def _recent_gateway_log_text() -> str:
    chunks: list[str] = []
    if _GATEWAY_LOG.is_file():
        try:
            chunks.append(_GATEWAY_LOG.read_text(errors="ignore")[-120_000:])
        except OSError:
            pass
    if _TMP_LOG_DIR.is_dir():
        for path in sorted(_TMP_LOG_DIR.glob("openclaw-*.log"), reverse=True)[:2]:
            try:
                chunks.append(path.read_text(errors="ignore")[-120_000:])
            except OSError:
                continue
    return "\n".join(chunks)


async def health() -> dict:
    url = settings.openclaw_gateway_url.rstrip("/")
    out: dict = {"ok": False, "url": url, "whatsapp": False, "bridge": False}

    try:
        async with httpx.AsyncClient(timeout=4.0) as client:
            resp = await client.get(url)
            out["http_ok"] = resp.status_code < 500
            out["ok"] = resp.status_code < 500
    except Exception as exc:
        out["error"] = str(exc)
        return out

    out["bridge"] = _bridge_enabled()
    out["whatsapp"] = _whatsapp_listening()
    out["ok"] = out.get("http_ok", False) and out["whatsapp"]
    return out


def _bridge_enabled() -> bool:
    cfg = Path.home() / ".openclaw" / "openclaw.json"
    if not cfg.is_file():
        return False
    try:
        text = cfg.read_text()
        return '"jarvis-bridge"' in text and '"enabled": true' in text
    except OSError:
        return False


def _whatsapp_listening() -> bool:
    try:
        proc = subprocess.run(
            ["openclaw", "channels", "status"],
            capture_output=True,
            text=True,
            timeout=12,
            check=False,
        )
        out = proc.stdout + proc.stderr
        if "WhatsApp" in out and ("connected" in out.lower() or "running" in out.lower()):
            if "not installed" not in out.lower() and "offline" not in out.lower():
                return True
    except (OSError, subprocess.TimeoutExpired):
        pass

    tail = _recent_gateway_log_text()
    if not tail:
        return False
    if "Listening for WhatsApp inbound messages" not in tail and "Listening for personal WhatsApp inbound messages" not in tail:
        return False
    return True


async def ensure_whatsapp() -> dict:
    """Restart gateway and verify WhatsApp channel comes up."""
    uid = subprocess.check_output(["id", "-u"], text=True).strip()
    subprocess.run(
        ["launchctl", "kickstart", "-k", f"gui/{uid}/ai.openclaw.gateway"],
        check=False,
        capture_output=True,
    )
    import asyncio

    for _ in range(20):
        await asyncio.sleep(2)
        st = await health()
        if st.get("whatsapp"):
            return {"ok": True, **st}
    return {"ok": False, "error": "WhatsApp did not connect — run: openclaw channels login whatsapp"}
