"""William's capability boundaries and reply shaping."""

import re

from jarvis.services import skills

CAN_DO = (
    "time and date",
    "weather",
    "web search for facts",
    "remember facts across sessions",
    "open apps and websites",
    "YouTube and Spotify music",
    "switch, close, and minimise windows",
    "screenshots and screen analysis",
    "background research tasks",
    "notifications",
    "Mac terminal commands (restart services, logs, brew, git with full access)",
    "code tasks via Cursor when configured",
)

CANNOT_DO = (
    "phone calls or texts",
    "email",
    "smart-home control beyond Netatmo",
    "purchases or payments without your approval",
    "anything requiring passwords you have not given",
    "guessing facts when search returns nothing",
)

VOICE_SYSTEM = """You are William Agent on Willy's Mac mini. Address Willy as "boss".
STRICT RULES FOR SPOKEN REPLIES:
- One or two complete sentences. Plain English. Easy to hear aloud.
- Finish every thought — never trail off or cut mid-sentence.
- No humor, lists, markdown, brackets, or engine labels.
- Say numbers and times clearly (e.g. "four thirty PM", not "16:30").
- If you cannot do something, say so in one clear sentence.
- NEVER invent facts. Use ONLY provided context, facts, memory, and conversation history.
- If you lack verified information, say "I couldn't verify that, boss." — do not guess."""

WEB_SYSTEM = """You are William Agent. Address Willy as boss. Be brief and factual. No humor. No markdown.
Never invent facts. If unverified, say you don't have verified information."""

CAPABILITIES_BLOCK = (
    "You CAN: " + "; ".join(CAN_DO) + ". "
    "You CANNOT: " + "; ".join(CANNOT_DO) + "."
)


def full_system(*, voice: bool, lessons: str = "", memory: str = "", conversation: str = "") -> str:
    base = VOICE_SYSTEM if voice else WEB_SYSTEM
    parts = [base, CAPABILITIES_BLOCK]
    from jarvis.services.grounding import grounding_rules

    parts.append(grounding_rules(voice=voice))
    skill_block = skills.load_skills_block()
    if skill_block:
        parts.append(skill_block)
    if conversation:
        parts.append(conversation)
    if memory:
        parts.append(memory)
    if lessons:
        parts.append(lessons)
    return "\n".join(parts)


def sanitize_for_speech(text: str) -> str:
    text = re.sub(r"\[[^\]]+\]", "", text)
    text = re.sub(r"\([^)]*\)", "", text)
    text = re.sub(r"[*#`_]", "", text)
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def trim_reply(text: str, *, voice: bool, max_words: int = 28) -> str:
    text = sanitize_for_speech(text)
    if not text:
        return text
    if not voice:
        return text

    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
    if not sentences:
        return text

    chosen = sentences[0]
    if len(sentences) > 1 and len(chosen.split()) < 8:
        two = f"{sentences[0]} {sentences[1]}"
        if len(two.split()) <= max_words:
            chosen = two

    words = chosen.split()
    if len(words) > max_words:
        chosen = " ".join(words[:max_words]).rstrip(",;:") + "."
    elif not chosen.endswith((".", "!", "?")):
        chosen += "."

    return chosen


def cannot_do_reply(request: str, *, voice: bool) -> str | None:
    lowered = request.lower()
    blocks = {
        "call": ("phone calls", "I cannot make calls, boss."),
        "text message": ("texts", "I cannot send texts, boss."),
        "send email": ("email", "I cannot send email, boss."),
        "buy": ("purchases", "Purchases need your approval, boss."),
        "order": ("orders", "I cannot place orders, boss."),
    }
    for key, (_, reply) in blocks.items():
        if key in lowered:
            return reply
    return None
