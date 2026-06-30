from jarvis.services import build_intake


HOSPITALITY_SNIPPET = """
PART 1 — PRODUCT REFRAME
PART 5 — BILL-SPLITTING LOGIC
PART 6 — PAYMENT ARCHITECTURE
Use Mollie as primary PSP.
MVP vs post-MVP prioritization.
restaurant table QR product.
"""


def test_classify_blueprint_prompt():
    assert build_intake.classify_prompt(HOSPITALITY_SNIPPET) == "blueprint"


def test_classify_implementation_prompt():
    assert build_intake.classify_prompt("scaffold a react todo app with fastapi backend") == "implementation"


def test_extract_explicit_parts():
    prompt = """
PART 1 — PRODUCT REFRAME
Rewrite the idea into a sharp startup concept.
- product name ideas
- one-sentence pitch

PART 2 — CORE USER FLOWS
Create detailed user flows for guests and waiters.

PART 3 — ROLE-BASED PRODUCT SURFACES
Define guest web app and staff panel.
"""
    parts = build_intake.extract_explicit_parts(prompt)
    assert len(parts) == 3
    assert parts[0]["id"] == "part-1"
    assert "PRODUCT REFRAME" in parts[0]["title"]
    assert parts[1]["id"] == "part-2"
    assert "user flows" in parts[1]["summary"].lower()


def test_merge_prefers_explicit_parts():
    ai = [{"id": "part-1", "title": "Short", "summary": "AI only"}]
    explicit = [
        {"id": "part-1", "title": "PART 1 — PRODUCT REFRAME", "summary": "Long explicit summary", "requirements": [], "deliverables": []},
        {"id": "part-2", "title": "PART 2 — FLOWS", "summary": "Flows body", "requirements": [], "deliverables": []},
    ]
    merged = build_intake._merge_identified_parts(ai, explicit)
    assert len(merged) == 2
    assert merged[0]["title"] == "Short"
    assert merged[0]["summary"] == "AI only"
    assert merged[1]["id"] == "part-2"


def test_normalize_intake():
    raw = {
        "product_summary": "Hospitality fintech",
        "identified_parts": [{"id": "part-1", "title": "Product", "summary": "QR payments"}],
        "mvp_scope": "Bill split only",
    }
    intake = build_intake._normalize_intake(raw, HOSPITALITY_SNIPPET)
    assert intake["product_summary"] == "Hospitality fintech"
    assert len(intake["identified_parts"]) >= 1
    assert intake["identified_parts"][0]["id"] == "part-1"


def test_intake_summary():
    intake = {
        "prompt_class": "blueprint",
        "one_line_pitch": "Table QR payments",
        "product_summary": "Full product",
        "mvp_scope": "MVP scope",
        "risks": ["PSD2 compliance"],
    }
    summary = build_intake.intake_summary_for_prompt(intake)
    assert "Table QR payments" in summary
    assert "PSD2" in summary
