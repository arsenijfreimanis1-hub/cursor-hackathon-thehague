import subprocess

import httpx

from jarvis.config import settings


async def health() -> dict:
    async with httpx.AsyncClient(timeout=3.0) as client:
        try:
            resp = await client.get(f"{settings.macos_helper_url}/status")
            resp.raise_for_status()
            return {"ok": True, **resp.json()}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}


async def notify(title: str, message: str, speak: bool = False) -> dict:
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.post(
                f"{settings.macos_helper_url}/notify",
                json={"title": title, "message": message, "speak": speak},
            )
            resp.raise_for_status()
            return {"ok": True, "via": "helper"}
        except Exception:
            pass

    safe_title = title.replace('"', '\\"')
    safe_msg = message.replace('"', '\\"')
    subprocess.run(
        [
            "osascript",
            "-e",
            f'display notification "{safe_msg}" with title "{safe_title}"',
        ],
        check=False,
    )
    return {"ok": True, "via": "osascript"}


async def screenshot() -> dict:
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(f"{settings.macos_helper_url}/screenshot")
        resp.raise_for_status()
        return resp.json()
