import re
import subprocess
from urllib.parse import quote_plus

from jarvis.config import settings
from jarvis.services import macos, spotify


def _run(script: str) -> dict:
    try:
        result = subprocess.run(
            ["/usr/bin/osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        out = (result.stdout or "").strip()
        if result.returncode != 0:
            err = (result.stderr or result.stdout or "osascript failed").strip()
            return {"ok": False, "error": err[:200]}
        return {"ok": True, "result": out}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def _open_app(name: str) -> dict:
    try:
        subprocess.run(["/usr/bin/open", "-a", name], check=True, timeout=10)
        return {"ok": True, "app": name}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def open_url(url: str) -> dict:
    try:
        subprocess.run(["/usr/bin/open", url], check=True, timeout=10)
        return {"ok": True, "url": url}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def play_music(*, query: str | None = None) -> dict:
    provider = settings.music_provider.lower().strip()
    if provider == "spotify":
        return spotify.play(query=query)
    for app in ("Music", "Spotify"):
        r = _open_app(app)
        if r.get("ok"):
            return {"ok": True, "app": app}
    return {"ok": False, "error": "Music app not found"}


def watch_youtube(query: str | None = None) -> dict:
    if query:
        url = f"https://www.youtube.com/results?search_query={quote_plus(query)}"
    else:
        url = "https://www.youtube.com"
    return open_url(url)


def open_app(name: str) -> dict:
    aliases = {
        "safari": "Safari",
        "chrome": "Google Chrome",
        "firefox": "Firefox",
        "finder": "Finder",
        "terminal": "Terminal",
        "music": "Music",
        "spotify": "Spotify",
        "notes": "Notes",
        "messages": "Messages",
        "mail": "Mail",
        "calendar": "Calendar",
        "photos": "Photos",
        "settings": "System Settings",
        "cursor": "Cursor",
        "code": "Visual Studio Code",
        "youtube": "Safari",
    }
    key = name.lower().strip()
    if key == "youtube":
        return watch_youtube()
    if key == "spotify":
        return spotify.open_app()
    app = aliases.get(key, name.title())
    return _open_app(app)


def focus_app(name: str) -> dict:
    aliases = {
        "safari": "Safari", "chrome": "Google Chrome", "firefox": "Firefox",
        "finder": "Finder", "terminal": "Terminal", "music": "Music",
        "spotify": "Spotify", "cursor": "Cursor",
    }
    app_name = aliases.get(name.lower().strip(), name.title())
    script = f'tell application "{app_name}" to activate'
    return _run(script)


async def close_window_via_helper() -> dict:
    try:
        r = await macos.press_key("w", modifiers=["cmd"])
        if r.get("ok"):
            return {"ok": True}
        return {"ok": False, "error": r.get("error", "key press failed")}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


async def minimise_window_via_helper() -> dict:
    try:
        r = await macos.press_key("m", modifiers=["cmd"])
        if r.get("ok"):
            return {"ok": True}
        return {"ok": False, "error": r.get("error", "key press failed")}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


# --- intent parsing ---

QUERY_NOISE_RE = re.compile(
    r"\b(summary of the conversation|the user was|preparing to leave|costco|hello like)\b",
    re.I,
)
LIKED_RE = re.compile(
    r"\b(liked songs?|liked playlist|liked tracks?|my likes|from my liked|"
    r"favourites?|favorites?|songs i like)\b",
    re.I,
)
GENRE_FROM_MY_RE = re.compile(
    r"\b(?:play(?:\s+me)?\s+)?(?:some\s+)?(?P<genre>[a-z]{3,24})\s+"
    r"(?:song|songs|music|tracks?)\s+from\s+my\b",
    re.I,
)
ARTIST_TRACK_RE = re.compile(
    r"\bplay(?:\s+me)?\s+(?P<query>.+?)\s+by\s+(?P<artist>[a-z0-9][\w\s'-]{1,40})\b",
    re.I,
)
LATEST_LIKED_RE = re.compile(
    r"\b(latest|most recent|newest|last)\b.{0,30}\b(liked|likes|favourite|favorite|liked song)\b",
    re.I,
)
MUSIC_RE = re.compile(
    r"\b(play music|listen to music|open music|put on music|some music|resume music|continue music)\b",
    re.I,
)
PLAY_SOMETHING_RE = re.compile(
    r"\bplay(?:\s+me)?\s+something(?:\s+on\s+spotify)?\b|\bput on something\b",
    re.I,
)
PAUSE_RE = re.compile(r"\b(pause music|pause spotify|stop music|pause playback)\b", re.I)
NEXT_RE = re.compile(r"\b(next song|next track|skip song|skip track|skip)\b", re.I)
PREV_RE = re.compile(r"\b(previous song|previous track|last song|go back)\b", re.I)
SPOTIFY_PLAY_RE = re.compile(r"\bplay\s+(.+?)\s+on\s+spotify\b", re.I)
SPOTIFY_RE = re.compile(r"\b(spotify|open spotify)\b", re.I)
PLAY_QUERY_RE = re.compile(r"\bplay\s+(.+)\b", re.I)
YOUTUBE_RE = re.compile(
    r"\b(youtube|watch youtube|open youtube|play .+ on youtube|watch .+ on youtube)\b",
    re.I,
)
OPEN_APP_RE = re.compile(
    r"\b(?:open|launch|start)\s+(safari|chrome|firefox|finder|terminal|music|spotify|"
    r"notes|messages|mail|calendar|photos|cursor|youtube)\b",
    re.I,
)
FOCUS_RE = re.compile(
    r"\b(?:switch to|focus|go to|show)\s+(safari|chrome|firefox|finder|terminal|music|spotify|cursor)\b",
    re.I,
)
CLOSE_RE = re.compile(r"\b(close (?:this |the )?window|close window)\b", re.I)
MINIMISE_RE = re.compile(r"\b(minimi[sz]e(?: window)?)\b", re.I)


def _sanitize_play_query(query: str) -> str | None:
    q = query.strip()
    q = re.sub(r"^(me|please|a|some)\s+", "", q, flags=re.I)
    q = re.sub(r"\s+please$", "", q, flags=re.I)
    m = QUERY_NOISE_RE.search(q)
    if m:
        q = q[: m.start()].strip()
    if len(q) > 60:
        q = q[:60].rsplit(" ", 1)[0].strip()
    if len(q) < 2 or QUERY_NOISE_RE.search(q):
        return None
    return q


def parse_command(text: str) -> dict | None:
    t = text.strip()
    if PAUSE_RE.search(t):
        return {"action": "pause"}
    if NEXT_RE.search(t):
        return {"action": "next"}
    if PREV_RE.search(t):
        return {"action": "previous"}
    m = GENRE_FROM_MY_RE.search(t)
    if m:
        return {"action": "liked_music", "filter": m.group("genre").strip(), "latest": False}
    if LATEST_LIKED_RE.search(t) or LIKED_RE.search(t):
        return {"action": "liked_music", "latest": bool(LATEST_LIKED_RE.search(t))}
    if PLAY_SOMETHING_RE.search(t):
        return {"action": "liked_music", "latest": False}
    if MUSIC_RE.search(t):
        return {"action": "music"}
    m = ARTIST_TRACK_RE.search(t)
    if m:
        query = f"{m.group('query').strip()} {m.group('artist').strip()}"
        clean = _sanitize_play_query(query)
        if clean:
            return {"action": "music", "query": clean}
    m = SPOTIFY_PLAY_RE.search(t)
    if m:
        clean = _sanitize_play_query(m.group(1).strip())
        if clean:
            return {"action": "music", "query": clean}
    if SPOTIFY_RE.search(t):
        return {"action": "spotify"}
    m = YOUTUBE_RE.search(t)
    if m:
        query = None
        qm = re.search(r"(?:play|watch)\s+(.+?)\s+on youtube", t, re.I)
        if qm:
            query = _sanitize_play_query(qm.group(1).strip())
        return {"action": "youtube", "query": query}
    m = PLAY_QUERY_RE.search(t)
    if m and settings.music_provider.lower() == "spotify":
        clean = _sanitize_play_query(m.group(1).strip())
        if clean and not re.search(r"\bon youtube\b", clean, re.I):
            if re.search(r"\bfrom\s+my\s+(liked|likes|favourites?|favorites?|playlist)\b", clean, re.I):
                return {"action": "liked_music", "latest": False}
            return {"action": "music", "query": clean}
    m = OPEN_APP_RE.search(t)
    if m:
        return {"action": "open_app", "target": m.group(1)}
    m = FOCUS_RE.search(t)
    if m:
        return {"action": "focus", "target": m.group(1)}
    if CLOSE_RE.search(t):
        return {"action": "close_window"}
    if MINIMISE_RE.search(t):
        return {"action": "minimise"}
    return None


def _music_reply(*, ok: bool, query: str | None = None, started: bool = True) -> str:
    if not ok:
        if not spotify.installed():
            return "Install Spotify and sign in, boss."
        return "Cannot play on Spotify, boss."
    if query:
        return f"Playing {query}, boss."
    if started:
        return "Playing on Spotify, boss."
    return "Spotify open, boss."


async def execute(text: str) -> dict:
    cmd = parse_command(text)
    if not cmd:
        return {"ok": False, "error": "not a system command"}

    action = cmd["action"]
    if action == "liked_music":
        r = spotify.play_liked(latest=cmd.get("latest", False))
        genre = cmd.get("filter")
        if r.get("ok"):
            if cmd.get("latest"):
                reply = "Playing your latest liked song, boss."
            elif genre:
                reply = f"Playing your liked songs, boss. I can't filter by {genre} yet."
            else:
                reply = "Playing your liked songs, boss."
        else:
            reply = "Cannot play liked songs on Spotify, boss."
        return {**r, "reply": reply}
    if action == "music":
        r = play_music(query=cmd.get("query"))
        return {**r, "reply": _music_reply(ok=r.get("ok"), query=cmd.get("query"))}
    if action == "pause":
        r = spotify.pause()
        return {**r, "reply": "Paused, boss." if r.get("ok") else "Cannot pause Spotify, boss."}
    if action == "next":
        r = spotify.next_track()
        return {**r, "reply": "Next track, boss." if r.get("ok") else "Cannot skip, boss."}
    if action == "previous":
        r = spotify.previous_track()
        return {**r, "reply": "Previous track, boss." if r.get("ok") else "Cannot go back, boss."}
    if action == "spotify":
        r = spotify.open_app()
        return {**r, "reply": "Opening Spotify, boss." if r.get("ok") else "Install Spotify, boss."}
    if action == "youtube":
        r = watch_youtube(cmd.get("query"))
        label = cmd.get("query") or "YouTube"
        return {**r, "reply": f"Opening {label}, boss." if r.get("ok") else "Cannot open YouTube, boss."}
    if action == "open_app":
        r = open_app(cmd["target"])
        return {**r, "reply": f"Opening {cmd['target']}, boss." if r.get("ok") else f"Cannot open {cmd['target']}, boss."}
    if action == "focus":
        r = focus_app(cmd["target"])
        return {**r, "reply": f"Switched to {cmd['target']}, boss." if r.get("ok") else f"Cannot focus {cmd['target']}, boss."}
    if action == "close_window":
        r = await close_window_via_helper()
        return {**r, "reply": "Closed, boss." if r.get("ok") else "Enable Accessibility for JarvisHelper, boss."}
    if action == "minimise":
        r = await minimise_window_via_helper()
        return {**r, "reply": "Minimised, boss." if r.get("ok") else "Enable Accessibility for JarvisHelper, boss."}
    return {"ok": False, "error": "unknown action"}
