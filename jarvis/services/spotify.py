import shutil
import subprocess
from pathlib import Path
from urllib.parse import quote

SPOTIFY_APP = Path("/Applications/Spotify.app")
DOWNLOAD_URL = "https://www.spotify.com/download/mac/"
DEFAULT_QUERY = "popular music"


def installed() -> bool:
    return SPOTIFY_APP.exists() or shutil.which("spotify") is not None


def _run(script: str) -> dict:
    try:
        result = subprocess.run(
            ["/usr/bin/osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        if result.returncode != 0:
            err = (result.stderr or result.stdout or "osascript failed").strip()
            return {"ok": False, "error": err[:200]}
        return {"ok": True, "result": (result.stdout or "").strip()}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def _escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace('"', '\\"')


def _player_state() -> str:
    r = _run('tell application "Spotify" to get player state as string')
    return r.get("result", "stopped") if r.get("ok") else "stopped"


def _play_uri(uri: str) -> dict:
    script = f'tell application "Spotify" to play track "{_escape(uri)}"'
    r = _run(script)
    if r.get("ok"):
        _run('tell application "Spotify" to activate')
    return r


def open_app() -> dict:
    if not installed():
        subprocess.run(["/usr/bin/open", DOWNLOAD_URL], check=False, timeout=10)
        return {"ok": False, "error": "Spotify not installed"}
    try:
        subprocess.run(["/usr/bin/open", "-a", "Spotify"], check=True, timeout=10)
        return {"ok": True}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def play_liked(*, latest: bool = False) -> dict:
    if not installed():
        subprocess.run(["/usr/bin/open", DOWNLOAD_URL], check=False, timeout=10)
        return {"ok": False, "error": "Spotify not installed"}

    _run('tell application "Spotify" to activate')
    r = _play_uri("spotify:collection:tracks")
    if r.get("ok") and latest:
        # Liked Songs are ordered with newest first in the collection view.
        return r
    return r


def play(*, query: str | None = None) -> dict:
    if not installed():
        subprocess.run(["/usr/bin/open", DOWNLOAD_URL], check=False, timeout=10)
        return {"ok": False, "error": "Spotify not installed"}

    _run('tell application "Spotify" to activate')

    if query:
        return _play_uri(f"spotify:search:{quote(query)}")

    r = _run('tell application "Spotify" to play')
    if r.get("ok") and _player_state() == "playing":
        return {"ok": True}

    return _play_uri(f"spotify:search:{quote(DEFAULT_QUERY)}")


def pause() -> dict:
    if not installed():
        return {"ok": False, "error": "Spotify not installed"}
    return _run('tell application "Spotify" to pause')


def resume() -> dict:
    if not installed():
        return {"ok": False, "error": "Spotify not installed"}
    return _run('tell application "Spotify" to play')


def next_track() -> dict:
    if not installed():
        return {"ok": False, "error": "Spotify not installed"}
    return _run('tell application "Spotify" to next track')


def previous_track() -> dict:
    if not installed():
        return {"ok": False, "error": "Spotify not installed"}
    return _run('tell application "Spotify" to previous track')
