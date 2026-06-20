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


async def speak(text: str) -> dict:
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.post(
                f"{settings.macos_helper_url}/speak",
                json={"text": text},
            )
            resp.raise_for_status()
            return {"ok": True, **resp.json()}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}


def _voice_clear(helper: dict) -> bool:
    if not helper.get("ok"):
        return True
    if helper.get("busy") or helper.get("voice_speaking"):
        return False
    if helper.get("listening_for_response") or helper.get("conversation_mode"):
        return False
    if helper.get("live_transcript_partial") and (helper.get("live_transcript") or "").strip():
        return False
    return True


async def speak_when_clear(text: str, *, max_wait: float = 14.0) -> dict:
    import asyncio
    import time

    deadline = time.monotonic() + max_wait
    while time.monotonic() < deadline:
        status = await health()
        if _voice_clear(status):
            return await speak(text)
        await asyncio.sleep(0.45)
    return {"ok": False, "error": "deferred: user speaking"}


async def _helper_post(path: str, *, json: dict | None = None, timeout: float = 15.0) -> dict:
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            resp = await client.post(f"{settings.macos_helper_url}{path}", json=json or {})
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:
            return {"ok": False, "error": str(exc)}


async def screenshot() -> dict:
    result = await _helper_post("/screenshot")
    if not result.get("ok") and "error" in result:
        return result
    return result


async def click(x: float, y: float) -> dict:
    return await _helper_post("/click", json={"x": x, "y": y})


async def type_text(text: str) -> dict:
    return await _helper_post("/type", json={"text": text})


async def press_key(key: str, *, modifiers: list[str] | None = None) -> dict:
    return await _helper_post("/key", json={"key": key, "modifiers": modifiers or []})


async def sleep_voice() -> dict:
    return await _helper_post("/sleep")


async def listen_voice() -> dict:
    """Enter conversation mode so the user can speak without the wake word."""
    return await _helper_post("/wake/listen")


async def clear_transcript() -> dict:
    return await _helper_post("/transcript/clear")


async def ensure_voice_awake() -> dict:
    """Heal helper if voice pipeline is down or unhealthy."""
    status = await health()
    if not status.get("ok"):
        return await restart_helper_service()

    perms = status.get("permissions") or {}
    mic = perms.get("microphone")
    speech = perms.get("speech")
    if mic in ("undetermined", "denied") or speech in ("undetermined", "denied", "restricted"):
        return {
            "ok": False,
            "action": "permissions_needed",
            "healthy": False,
            "permissions": perms,
        }

    healthy = status.get("healthy", False)
    listening = status.get("wake_listening", False)
    audio = perms.get("audio_running", False)

    if listening and audio and healthy:
        return {"ok": True, "action": "already_awake", "healthy": True}

    result = await _helper_post("/wake/start")
    return {**result, "action": "wake_started"}


async def restart_helper_service() -> dict:
    import subprocess

    uid = subprocess.check_output(["id", "-u"], text=True).strip()
    label = f"gui/{uid}/com.willy.jarvis-helper"
    try:
        subprocess.run(
            ["launchctl", "kickstart", "-k", label],
            check=True,
            timeout=15,
            capture_output=True,
        )
        return {"ok": True, "action": "helper_restarted"}
    except Exception as exc:
        return {"ok": False, "error": str(exc), "action": "helper_restart_failed"}


async def restart_core_service() -> dict:
    import subprocess

    uid = subprocess.check_output(["id", "-u"], text=True).strip()
    label = f"gui/{uid}/com.willy.jarvis-core"
    try:
        subprocess.run(
            ["launchctl", "kickstart", "-k", label],
            check=True,
            timeout=15,
            capture_output=True,
        )
        return {"ok": True, "action": "core_restarted"}
    except Exception as exc:
        return {"ok": False, "error": str(exc), "action": "core_restart_failed"}


async def set_muted(muted: bool) -> dict:
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            resp = await client.post(
                f"{settings.macos_helper_url}/mute",
                json={"muted": muted},
            )
            resp.raise_for_status()
            return {"ok": True, **resp.json()}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}


async def prompt_permissions() -> dict:
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.post(f"{settings.macos_helper_url}/permissions/prompt")
            resp.raise_for_status()
            return {"ok": True, **resp.json()}
        except Exception as exc:
            return {"ok": False, "error": str(exc), "accessibility": False}


async def _helper_get(path: str, *, timeout: float = 5.0) -> dict:
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            resp = await client.get(f"{settings.macos_helper_url}{path}")
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:
            return {"ok": False, "error": str(exc)}


async def screen_watcher_status() -> dict:
    return await _helper_get("/screen/status")


async def screen_watcher_pause() -> dict:
    return await _helper_post("/screen/pause")


async def screen_watcher_resume() -> dict:
    return await _helper_post("/screen/resume")
