import subprocess

import httpx

from jarvis.config import settings

_DEFAULT_TIMEOUT = httpx.Timeout(15.0, connect=2.0)
_REMOTE_TIMEOUT = httpx.Timeout(2.0, connect=0.5)

_helper_client: httpx.AsyncClient | None = None


def _get_client() -> httpx.AsyncClient:
    global _helper_client
    if _helper_client is None or _helper_client.is_closed:
        _helper_client = httpx.AsyncClient(
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
        )
    return _helper_client


async def close_helper_client() -> None:
    global _helper_client
    if _helper_client is not None and not _helper_client.is_closed:
        await _helper_client.aclose()
    _helper_client = None


async def health() -> dict:
    try:
        resp = await _get_client().get(
            f"{settings.macos_helper_url}/status",
            timeout=httpx.Timeout(3.0, connect=1.0),
        )
        resp.raise_for_status()
        return {"ok": True, **resp.json()}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


async def notify(title: str, message: str, speak: bool = False) -> dict:
    try:
        resp = await _get_client().post(
            f"{settings.macos_helper_url}/notify",
            json={"title": title, "message": message, "speak": speak},
            timeout=httpx.Timeout(10.0),
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
    try:
        resp = await _get_client().post(
            f"{settings.macos_helper_url}/speak",
            json={"text": text},
            timeout=httpx.Timeout(30.0),
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


async def _helper_post(
    path: str,
    *,
    json: dict | None = None,
    timeout: httpx.Timeout | None = None,
) -> dict:
    try:
        resp = await _get_client().post(
            f"{settings.macos_helper_url}{path}",
            json=json or {},
            timeout=timeout or _DEFAULT_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


async def _helper_get(path: str, *, timeout: httpx.Timeout | None = None) -> dict:
    try:
        resp = await _get_client().get(
            f"{settings.macos_helper_url}{path}",
            timeout=timeout or _DEFAULT_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


async def _remote_post(path: str, *, json: dict | None = None) -> dict:
    return await _helper_post(path, json=json, timeout=_REMOTE_TIMEOUT)


async def screenshot() -> dict:
    result = await _helper_post("/screenshot")
    if not result.get("ok") and "error" in result:
        return result
    return result


async def mouse_move(x: float, y: float) -> dict:
    return await _remote_post("/mousemove", json={"x": x, "y": y})


async def mouse_down(x: float, y: float, *, button: str = "left") -> dict:
    return await _remote_post("/mousedown", json={"x": x, "y": y, "button": button})


async def mouse_up(x: float, y: float, *, button: str = "left") -> dict:
    return await _remote_post("/mouseup", json={"x": x, "y": y, "button": button})


async def click(x: float, y: float, *, button: str = "left") -> dict:
    return await _remote_post("/click", json={"x": x, "y": y, "button": button})


async def type_text(text: str) -> dict:
    return await _remote_post("/type", json={"text": text})


async def press_key(key: str, *, modifiers: list[str] | None = None) -> dict:
    return await _remote_post("/key", json={"key": key, "modifiers": modifiers or []})


async def sleep_voice() -> dict:
    return await _helper_post("/sleep")


async def listen_voice() -> dict:
    """Enter conversation mode so the user can speak without the wake word."""
    return await _helper_post("/wake/listen")


async def clear_transcript() -> dict:
    return await _helper_post("/transcript/clear")


async def start_guided_voice_enrollment() -> dict:
    return await _helper_post("/voice/enroll/start-guided")


async def voice_enrollment_status() -> dict:
    return await _helper_get("/voice/enroll/status", timeout=httpx.Timeout(5.0))


async def cancel_voice_enrollment() -> dict:
    return await _helper_post("/voice/enroll/cancel")


async def handle_dialogs_native() -> dict:
    return await _helper_post("/dialogs/handle")


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
    try:
        resp = await _get_client().post(
            f"{settings.macos_helper_url}/mute",
            json={"muted": muted},
            timeout=httpx.Timeout(5.0),
        )
        resp.raise_for_status()
        return {"ok": True, **resp.json()}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


async def prompt_permissions() -> dict:
    """User-initiated permission prompts (triggers TCC dialogs). Use bootstrap_permissions() for automation."""
    try:
        resp = await _get_client().post(
            f"{settings.macos_helper_url}/permissions/prompt",
            timeout=httpx.Timeout(10.0),
        )
        resp.raise_for_status()
        return {"ok": True, **resp.json()}
    except Exception as exc:
        return {"ok": False, "error": str(exc), "accessibility": False}


async def bootstrap_permissions() -> dict:
    """Open missing settings panes + native AX — no TCC popup spam."""
    try:
        resp = await _get_client().post(
            f"{settings.macos_helper_url}/permissions/bootstrap",
            timeout=httpx.Timeout(10.0),
        )
        resp.raise_for_status()
        return {"ok": True, **resp.json()}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


async def screen_watcher_status() -> dict:
    return await _helper_get("/screen/status")


async def screen_watcher_pause() -> dict:
    return await _helper_post("/screen/pause")


async def screen_watcher_resume() -> dict:
    return await _helper_post("/screen/resume")


async def dispatch_remote_action(action: str, payload: dict) -> dict:
    """Execute a single remote input action (used by HTTP + WebSocket relay)."""
    if action == "mousemove":
        return await mouse_move(float(payload["x"]), float(payload["y"]))
    if action == "mousedown":
        return await mouse_down(
            float(payload["x"]),
            float(payload["y"]),
            button=str(payload.get("button", "left")),
        )
    if action == "mouseup":
        return await mouse_up(
            float(payload["x"]),
            float(payload["y"]),
            button=str(payload.get("button", "left")),
        )
    if action == "click":
        return await click(
            float(payload["x"]),
            float(payload["y"]),
            button=str(payload.get("button", "left")),
        )
    if action == "type":
        return await type_text(str(payload.get("text", "")))
    if action == "key":
        mods = payload.get("modifiers") or []
        if not isinstance(mods, list):
            mods = []
        return await press_key(str(payload["key"]), modifiers=[str(m) for m in mods])
    return {"ok": False, "error": f"unknown action: {action}"}
