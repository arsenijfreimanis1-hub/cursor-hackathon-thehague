"""Anti-hallucination helpers — William only speaks verified or conversational truth."""

import re

UNVERIFIED_VOICE = "I couldn't verify that, boss."
UNVERIFIED_WEB = "I don't have verified information on that."

FACTUAL_SIGNAL = re.compile(
    r"\?|\b(who|what|when|where|which|how many|how much|why|is there|are there|"
    r"did|does|do|was|were|tell me about|define|meaning of|capital of|population|"
    r"latest|news|score|price|true that)\b",
    re.I,
)

HEDGE_PATTERN = re.compile(
    r"\b(I think|I believe|probably|maybe|might be|could be|as far as I know|"
    r"if I recall|I'm not sure but|likely|possibly|I assume|I guess)\b",
    re.I,
)

INVENTION_PATTERN = re.compile(
    r"\b(is by|was written by|released in|founded in|born in|located in)\b",
    re.I,
)


def needs_grounding(text: str) -> bool:
    return bool(FACTUAL_SIGNAL.search(text.strip()))


def grounding_rules(*, voice: bool) -> str:
    unverified = UNVERIFIED_VOICE if voice else UNVERIFIED_WEB
    return (
        "GROUNDING (mandatory):\n"
        "- Only state facts present in Verified facts, MEMORY, or RECENT CONVERSATION.\n"
        f"- If facts do not answer the question, say exactly: {unverified}\n"
        "- Never invent names, numbers, dates, lyrics, news, or song attributions.\n"
        "- For casual chat, be natural but do not fabricate shared history or events."
    )


def fact_answer_prompt(question: str, facts: str, *, voice: bool) -> str:
    unverified = UNVERIFIED_VOICE if voice else UNVERIFIED_WEB
    return (
        f"Question: {question}\n\n"
        f"Verified facts (ONLY source of truth):\n{facts}\n\n"
        "Answer in one or two plain sentences using ONLY verified facts. "
        f"If facts do not contain the answer, reply exactly: {unverified}"
    )


def enforce_grounded_reply(
    reply: str,
    *,
    voice: bool,
    had_facts: bool,
    confidence: str = "none",
) -> str:
    text = reply.strip()
    if not text:
        return UNVERIFIED_VOICE if voice else UNVERIFIED_WEB

    if had_facts and confidence in ("high", "medium"):
        return text

    if not had_facts or confidence in ("low", "none"):
        if HEDGE_PATTERN.search(text) or (
            INVENTION_PATTERN.search(text) and "?" in text
        ):
            return UNVERIFIED_VOICE if voice else UNVERIFIED_WEB

    if not had_facts and INVENTION_PATTERN.search(text):
        return UNVERIFIED_VOICE if voice else UNVERIFIED_WEB

    return text
