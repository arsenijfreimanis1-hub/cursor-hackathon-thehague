"""Vigil LLM proxy — route William's cloud LLM calls through api.vigil.wtf for dashboard metrics."""

from __future__ import annotations

import logging
from urllib.parse import urlparse

import httpx

from jarvis.config import settings

log = logging.getLogger("jarvis.vigil_proxy")

PROVIDERS = frozenset(
    {"anthropic", "openai", "gemini", "mistral", "groq", "together", "python", "langchain"}
)


def proxy_base_url() -> str | None:
    """User dashboard URL → https://api.vigil.wtf/{user_id}"""
    raw = (settings.vigil_proxy_url or settings.vigil_gateway_url or "").strip().rstrip("/")
    if not raw:
        return None
    parsed = urlparse(raw)
    parts = [p for p in parsed.path.split("/") if p]
    if not parts:
        return None
    user_id = parts[0]
    return f"{parsed.scheme}://{parsed.netloc}/{user_id}"


def proxy_url(provider: str, path: str) -> str | None:
    base = proxy_base_url()
    if not base:
        return None
    return f"{base}/{provider.strip('/')}/{path.strip('/')}"


def _proxy_headers(api_key: str) -> dict[str, str]:
    """Headers Vigil expects on proxied provider calls."""
    return {
        "Authorization": f"Bearer {api_key}",
        "X-Vigil-Agent": settings.vigil_agent_id,
        "Content-Type": "application/json",
    }


def configured() -> bool:
    if not settings.vigil_proxy_enabled or not proxy_base_url():
        return False
    if settings.vigil_proxy_provider not in PROVIDERS:
        return False
    if settings.vigil_proxy_provider == "anthropic":
        return bool(settings.resolved_anthropic_api_key())
    if settings.vigil_proxy_provider == "openai":
        return bool(settings.resolved_openai_api_key())
    return False


def status() -> dict:
    base = proxy_base_url()
    provider = settings.vigil_proxy_provider
    anthropic_key = bool(settings.resolved_anthropic_api_key())
    openai_key = bool(settings.resolved_openai_api_key())
    ready = configured()
    missing: list[str] = []
    if settings.vigil_proxy_enabled:
        if not base:
            missing.append("JARVIS_VIGIL_PROXY_URL")
        if provider == "anthropic" and not anthropic_key:
            missing.append("ANTHROPIC_API_KEY")
        if provider == "openai" and not openai_key:
            missing.append("OPENAI_API_KEY")
    return {
        "enabled": settings.vigil_proxy_enabled,
        "configured": ready,
        "provider": provider,
        "agent_tag": settings.vigil_agent_id,
        "base_url": base,
        "anthropic_base_url": f"{base}/anthropic" if base else None,
        "messages_url": proxy_url("anthropic", "v1/messages"),
        "openai_chat_url": proxy_url("openai", "v1/chat/completions"),
        "anthropic_model": settings.vigil_proxy_anthropic_model,
        "openai_model": settings.vigil_proxy_openai_model,
        "has_anthropic_key": anthropic_key,
        "has_openai_key": openai_key,
        "missing": missing,
        "cursor_uses_separate_key": True,
        "cursor_key_env": "CURSOR_API_KEY",
        "ollama_bypassed_when_ready": ready,
    }


async def chat_openai(*, system: str | None, messages: list[dict], model: str | None = None) -> str:
    url = proxy_url("openai", "v1/chat/completions")
    api_key = settings.resolved_openai_api_key()
    if not url or not api_key:
        raise RuntimeError("Vigil OpenAI proxy not configured — set JARVIS_VIGIL_PROXY_URL and OPENAI_API_KEY")

    built: list[dict] = []
    if system:
        built.append({"role": "system", "content": system})
    built.extend(messages)

    payload = {
        "model": model or settings.vigil_proxy_openai_model,
        "messages": built,
        "temperature": 0.1,
    }
    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(url, json=payload, headers=_proxy_headers(api_key))
        if resp.status_code >= 400:
            log.warning("vigil openai proxy %s: %s", resp.status_code, resp.text[:300])
            resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]


async def chat_anthropic(*, system: str | None, messages: list[dict], model: str | None = None) -> str:
    """
    Anthropic messages API via Vigil proxy.

    URL:  {VIGIL_PROXY_URL}/anthropic/v1/messages
    Auth: Authorization: Bearer {ANTHROPIC_API_KEY}
    Tag:  X-Vigil-Agent: william
    """
    url = proxy_url("anthropic", "v1/messages")
    api_key = settings.resolved_anthropic_api_key()
    if not url or not api_key:
        raise RuntimeError("Vigil Anthropic proxy not configured — set JARVIS_VIGIL_PROXY_URL and ANTHROPIC_API_KEY")

    payload = {
        "model": model or settings.vigil_proxy_anthropic_model,
        "max_tokens": settings.vigil_proxy_max_tokens,
        "messages": [
            {"role": m["role"], "content": m["content"]}
            for m in messages
            if m["role"] in ("user", "assistant") and m.get("content")
        ],
    }
    if system:
        payload["system"] = system

    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(url, json=payload, headers=_proxy_headers(api_key))
        if resp.status_code >= 400:
            log.warning("vigil anthropic proxy %s: %s", resp.status_code, resp.text[:300])
            resp.raise_for_status()
        data = resp.json()
        parts = data.get("content") or []
        return "".join(p.get("text", "") for p in parts if p.get("type") == "text")


async def chat(*, system: str | None = None, messages: list[dict] | None = None, prompt: str | None = None) -> str:
    msgs = list(messages or [])
    if prompt and not msgs:
        msgs = [{"role": "user", "content": prompt}]
    if not msgs:
        raise ValueError("prompt or messages required")

    provider = settings.vigil_proxy_provider
    if provider == "openai":
        return await chat_openai(system=system, messages=msgs)
    if provider == "anthropic":
        return await chat_anthropic(system=system, messages=msgs)
    raise RuntimeError(f"Vigil proxy provider '{provider}' is not wired for chat yet — use anthropic or openai")
