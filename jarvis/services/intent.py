import re

from jarvis.config import settings
from jarvis.services import ollama

EXIT_PHRASES = re.compile(
    r"\b(thanks|thank you|goodbye|good bye|stop listening|that's all|thats all|bye)\b",
    re.I,
)
CANCEL_PHRASES = re.compile(r"\b(cancel|stop|never mind|forget it)\b", re.I)
TIME_QUERY = re.compile(r"\b(what time|time is it|current time|what's the time)\b", re.I)
DATE_QUERY = re.compile(r"\b(what day|what date|what's the date|today's date)\b", re.I)
WEATHER_QUERY = re.compile(r"\b(weather|forecast|temperature|rain|sunny)\b", re.I)
CODE_HINTS = re.compile(
    r"\b(build app|create app|create website|refactor|implement|scaffold|codebase|"
    r"pull request|typescript|react app|backend api|write tests|fix bug|add feature)\b",
    re.I,
)
ACTION_HINTS = re.compile(
    r"\b(research|look up|find out|investigate|summarise|summarize|analyse|analyze|"
    r"check for me|in the background|while i)\b",
    re.I,
)
REASON_HINTS = re.compile(
    r"\b(why|how does|explain|compare|pros and cons|should i|recommend|plan|strategy|"
    r"think through|reason about)\b",
    re.I,
)
FACT_HINTS = re.compile(
    r"\b(what|who|when|where|how much|how many|news|latest|price|score|population|"
    r"capital|define|meaning|tell me about|is it true|did|does)\b",
    re.I,
)
SYSTEM_HINTS = re.compile(
    r"\b(play music|listen to music|pause music|stop music|next song|skip|spotify|youtube|"
    r"watch youtube|open youtube|open |launch |switch to |focus |close window|minimi[sz]e|play )\b",
    re.I,
)
TERMINAL_HINTS = re.compile(
    r"\b(run |execute |terminal |shell |restart jarvis|restart helper|restart william|"
    r"restart agent|restart both|fix services|launchctl |brew |git |install helper|grant voice|"
    r"show logs|tail logs|check jarvis|check helper|check ollama|ollama )\b",
    re.I,
)
REMEMBER_HINTS = re.compile(r"\b(remember|don't forget|do not forget|keep in mind|note that)\b", re.I)
RECALL_HINTS = re.compile(
    r"\b(what did (?:i|we)|do you remember|recall|what was (?:that|it) about)\b",
    re.I,
)
SCREEN_HINTS = re.compile(
    r"\b(on my screen|what'?s on (?:my )?screen|what am i looking at|look at (?:my |the )?screen|"
    r"see (?:my |the )?screen|read (?:the )?screen|what'?s open|this window|this app|"
    r"click (?:the |on )?|tap (?:the |on )?|press (?:the )?|screenshot|what do you see)\b",
    re.I,
)

VALID = frozenset(
    {"exit", "cancel", "time", "terminal", "system", "weather", "code", "action", "reason", "fact", "chat", "remember", "recall", "screen"}
)


def classify(text: str) -> str:
    """Fast regex classifier — used as fallback and fast-path."""
    cleaned = text.strip()
    if not cleaned:
        return "chat"
    if EXIT_PHRASES.search(cleaned):
        return "exit"
    if CANCEL_PHRASES.search(cleaned):
        return "cancel"
    if TIME_QUERY.search(cleaned) or DATE_QUERY.search(cleaned):
        return "time"
    if TERMINAL_HINTS.search(cleaned):
        return "terminal"
    if SYSTEM_HINTS.search(cleaned):
        return "system"
    if REMEMBER_HINTS.search(cleaned):
        return "remember"
    if RECALL_HINTS.search(cleaned):
        return "recall"
    if SCREEN_HINTS.search(cleaned):
        return "screen"
    if WEATHER_QUERY.search(cleaned):
        return "fact"
    if CODE_HINTS.search(cleaned) or len(cleaned) > 600:
        return "code"
    if ACTION_HINTS.search(cleaned):
        return "action"
    if "?" in cleaned and REASON_HINTS.search(cleaned):
        return "reason"
    if "?" in cleaned or FACT_HINTS.search(cleaned):
        return "fact"
    return "chat"


def _regex_confidence(text: str, kind: str) -> float:
    """Higher = more confident regex got it right."""
    if kind in ("exit", "cancel", "time", "remember", "recall"):
        return 1.0
    if kind == "fact" and WEATHER_QUERY.search(text):
        return 0.95
    if kind == "terminal" and TERMINAL_HINTS.search(text):
        return 0.95
    if kind == "system" and SYSTEM_HINTS.search(text):
        return 0.95
    if kind == "code" and CODE_HINTS.search(text):
        return 0.9
    if kind == "action" and ACTION_HINTS.search(text):
        return 0.85
    if kind in ("fact", "reason") and ("?" in text or FACT_HINTS.search(text) or REASON_HINTS.search(text)):
        return 0.8
    if kind == "chat":
        return 0.5
    return 0.6


async def classify_async(text: str) -> str:
    """Hybrid classifier: regex fast-path, LLM for ambiguous cases."""
    regex_kind = classify(text)
    if not settings.intent_llm_enabled:
        return regex_kind

    confidence = _regex_confidence(text, regex_kind)
    if confidence >= settings.intent_regex_threshold:
        return regex_kind

    prompt = (
        f'Classify this user message into exactly one intent.\n'
        f'Message: "{text[:400]}"\n\n'
        f'Intents: exit, cancel, time, terminal, system, remember, recall, code, action, reason, fact, chat\n'
        f'Reply with ONLY the intent word.'
    )
    try:
        raw = await ollama.chat(
            prompt,
            system="You classify voice assistant intents. Reply with one lowercase word only.",
        )
        word = raw.strip().lower().split()[0] if raw.strip() else regex_kind
        word = re.sub(r"[^a-z]", "", word)
        if word in VALID:
            # LLM often mislabels wake words / greetings as exit — require regex proof.
            if word == "exit" and not EXIT_PHRASES.search(text):
                return regex_kind
            if word == "cancel" and not CANCEL_PHRASES.search(text):
                return regex_kind
            return word
    except Exception:
        pass
    return regex_kind
