import re
from urllib.parse import quote
from datetime import datetime
from html import unescape
from zoneinfo import ZoneInfo

import httpx

from jarvis.config import settings

USER_AGENT = "Mozilla/5.0 (compatible; JarvisCore/1.0; +local)"

WEATHER_QUERY = re.compile(r"\b(weather|forecast|temperature|rain|sunny|cloudy)\b", re.I)
CALC_QUERY = re.compile(
    r"(?:^|\s)([\d\s+\-*/().]+(?:\s*[\d+\-*/().]+)+)\s*(?:=|\?)?\s*$"
)
CITY_HINT = re.compile(
    r"\b(?:in|for|at)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b"
)


def _strip_html(raw: str) -> str:
    text = re.sub(r"<[^>]+>", " ", raw)
    return re.sub(r"\s+", " ", unescape(text)).strip()


def _extract_city(text: str) -> str:
    m = CITY_HINT.search(text)
    if m:
        return m.group(1).strip()
    return "Amsterdam"


async def _weather(city: str | None = None) -> str:
    city = city or "Amsterdam"
    async with httpx.AsyncClient(timeout=10.0) as client:
        geo = await client.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": city, "count": 1},
        )
        geo.raise_for_status()
        results = geo.json().get("results") or []
        if not results:
            return ""
        lat, lon = results[0]["latitude"], results[0]["longitude"]
        name = results[0].get("name", city)
        wx = await client.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": lat,
                "longitude": lon,
                "current": "temperature_2m,weather_code,wind_speed_10m",
                "timezone": settings.timezone,
            },
        )
        wx.raise_for_status()
        cur = wx.json().get("current", {})
        temp = cur.get("temperature_2m")
        wind = cur.get("wind_speed_10m")
        if temp is None:
            return ""
        return f"Weather in {name}: {temp}°C, wind {wind} km/h (Open-Meteo)"


async def _wikipedia(query: str) -> str:
    async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
        try:
            resp = await client.get(
                f"https://en.wikipedia.org/api/rest_v1/page/summary/{quote(query.replace(' ', '_'), safe='')}",
                headers={"User-Agent": USER_AGENT},
            )
            if resp.status_code != 200:
                search = await client.get(
                    "https://en.wikipedia.org/w/api.php",
                    params={
                        "action": "query",
                        "list": "search",
                        "srsearch": query,
                        "format": "json",
                        "srlimit": 1,
                    },
                )
                search.raise_for_status()
                hits = search.json().get("query", {}).get("search", [])
                if not hits:
                    return ""
                title = hits[0]["title"]
                resp = await client.get(
                    f"https://en.wikipedia.org/api/rest_v1/page/summary/{quote(title.replace(' ', '_'), safe='')}",
                    headers={"User-Agent": USER_AGENT},
                )
            if resp.status_code != 200:
                return ""
            data = resp.json()
            extract = data.get("extract", "")
            if extract:
                return f"{data.get('title', query)}: {extract[:400]} (Wikipedia)"
        except Exception:
            pass
    return ""


async def search(query: str, *, max_results: int = 5) -> str:
    snippets: list[str] = []

    async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
        try:
            resp = await client.get(
                "https://api.duckduckgo.com/",
                params={"q": query, "format": "json", "no_html": 1, "skip_disambig": 1},
            )
            resp.raise_for_status()
            data = resp.json()
            if data.get("AbstractText"):
                line = data["AbstractText"]
                if data.get("AbstractSource"):
                    line += f" ({data['AbstractSource']})"
                snippets.append(line)
            for topic in data.get("RelatedTopics", [])[:max_results]:
                if isinstance(topic, dict) and topic.get("Text"):
                    snippets.append(topic["Text"])
                elif isinstance(topic, dict):
                    for sub in topic.get("Topics", [])[:2]:
                        if sub.get("Text"):
                            snippets.append(sub["Text"])
        except Exception:
            pass

        if len(" ".join(snippets)) < 120:
            try:
                resp = await client.post(
                    "https://html.duckduckgo.com/html/",
                    data={"q": query, "b": "", "kl": "wt-wt"},
                    headers={"User-Agent": USER_AGENT},
                )
                resp.raise_for_status()
                for match in re.finditer(
                    r'class="result__a"[^>]*>(.*?)</a>.*?class="result__snippet"[^>]*>(.*?)</',
                    resp.text,
                    re.S,
                ):
                    title = _strip_html(match.group(1))
                    snippet = _strip_html(match.group(2))
                    if title and snippet:
                        snippets.append(f"{title}: {snippet}")
                    if len(snippets) >= max_results:
                        break
            except Exception:
                pass

    seen: set[str] = set()
    unique: list[str] = []
    for item in snippets:
        key = item.lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)

    if not unique:
        return ""
    return "\n".join(f"- {line}" for line in unique[:max_results])


def _calc(text: str) -> str | None:
    m = CALC_QUERY.search(text.replace(",", ""))
    if not m:
        return None
    expr = m.group(1).strip()
    if not re.fullmatch(r"[\d\s+\-*/().]+", expr):
        return None
    try:
        result = eval(expr, {"__builtins__": {}}, {})  # noqa: S307
        return f"{expr.strip()} = {result}"
    except Exception:
        return None


def _score_confidence(parts: list[str]) -> str:
    combined = "\n".join(parts)
    if not combined:
        return "none"
    if len(combined) >= 280 and len(parts) >= 2:
        return "high"
    if len(combined) >= 120:
        return "medium"
    return "low"


def _refine_query(text: str) -> str:
    cleaned = re.sub(r"\b(hey willy|hey william|boss|please|tell me|what is|what's)\b", " ", text, flags=re.I)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" ?.")
    return cleaned[:120] or text[:120]


async def gather_facts(text: str) -> dict:
    parts: list[str] = []

    if WEATHER_QUERY.search(text):
        wx = await _weather(_extract_city(text))
        if wx:
            parts.append(wx)

    calc = _calc(text)
    if calc:
        parts.append(calc)

    primary = await search(text)
    if primary:
        parts.append(primary)

    refined = _refine_query(text)
    if refined.lower() != text.lower()[:120].lower():
        extra = await search(refined)
        if extra and extra not in primary:
            parts.append(extra)

    if len("\n".join(parts)) < 100:
        wiki = await _wikipedia(refined)
        if wiki:
            parts.append(wiki)

    combined = "\n".join(parts)
    confidence = _score_confidence(parts)

    return {"text": combined, "confidence": confidence if combined else "none"}


async def research(text: str, *, depth: int = 2) -> dict:
    """Multi-step research: gather, optionally refine query, re-search."""
    first = await gather_facts(text)
    if first.get("confidence") in ("high", "medium") or depth < 2:
        return first

    follow_up = _refine_query(text)
    if "?" in text:
        follow_up = re.sub(r"\?", "", follow_up).strip()

    second = await search(f"{follow_up} facts")
    parts = [first.get("text", "")]
    if second and second not in first.get("text", ""):
        parts.append(second)

    combined = "\n".join(p for p in parts if p)
    return {"text": combined, "confidence": _score_confidence([p for p in parts if p])}


def needs_search(text: str) -> bool:
    from jarvis.services.intent import classify

    return classify(text) in ("fact", "reason", "action", "recall")
