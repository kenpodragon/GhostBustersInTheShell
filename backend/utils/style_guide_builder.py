"""
Style guide builder — formats voice profile elements into 3 prompt sections
based on per-element routing strategies stored in the DB.

Sections:
  1. JSON Hard Targets  — strategy: json | json_enforced
  2. English Style Guidance — strategy: english | hybrid
  3. Mandatory Enforcement — strategy: targeted_enforcement
"""

import json
import math

from utils.weight_translator import translate_element


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _load_routing(db_conn=None) -> dict:
    """Load element routing from DB. Returns dict keyed by element_name."""
    try:
        if db_conn is None:
            from db import get_connection
            db_conn = get_connection()
        cur = db_conn.cursor()
        cur.execute(
            "SELECT element_name, strategy, best_score, detection_override, enforcement_template "
            "FROM element_routing"
        )
        rows = cur.fetchall()
        cols = [d[0] for d in cur.description]
        return {row[cols.index("element_name")]: dict(zip(cols, row)) for row in rows}
    except Exception:
        return {}


def _compute_count(element: dict, target_word_count: int, template: str) -> str:
    """Compute a concrete count string for a targeted_enforcement template."""
    name = element.get("name", "")
    weight = element.get("weight", 0.5)
    twc = target_word_count

    if name == "ellipsis_usage":
        raw = weight * 0.3 * (twc / 20)
        n = max(1, math.floor(raw))
        return f"{n}-{n + 1}"

    if name == "exclamation_rate":
        raw = weight * (twc / 20)
        n = max(1, round(raw))
        return str(n)

    if name == "first_person_usage":
        raw = weight * 0.1 * twc
        n = max(1, round(raw))
        return f"~{n}"

    if name == "quotation_density":
        raw = weight * 0.3 * twc * 5 / 100
        n = max(1, math.floor(raw))
        return f"{n}-{n + 1} quotes"

    if name == "single_sentence_paragraph_ratio":
        raw = weight * (twc / 20 / 4)
        n = max(1, round(raw))
        return f"~{n}"

    if name == "narrative_vs_analytical_ratio":
        pct = round((1 - weight) * 100)
        return f"~{pct}% analytical"

    if name in ("long_sentence_ratio", "short_sentence_ratio",
                "passive_voice_rate", "verb_tense_past_ratio",
                "verb_tense_present_ratio"):
        pct = round(weight * 100)
        return f"~{pct}%"

    if name in ("article_rate", "named_entity_density"):
        val = round(weight * 100, 1)
        return f"~{val} per 100 words"

    if name == "hedging_language_rate":
        raw = weight * (twc / 20)
        n = max(1, round(raw))
        return f"~{n}"

    if name == "topic_coherence_score":
        return f"~{round(weight, 2)}"

    if name == "sentence_length_stddev":
        return ""

    # Fallback: express as percentage if looks like a rate, else raw number
    if weight <= 1.0:
        pct = round(weight * 100)
        return f"~{pct}%"
    return str(round(weight, 2))


# ---------------------------------------------------------------------------
# Section builders
# ---------------------------------------------------------------------------

def _build_json_section(elements: list) -> str:
    """Build the JSON hard targets section."""
    if not elements:
        return ""
    items = [
        {
            "name": el["name"],
            "category": el.get("category", ""),
            "target_value": el.get("target_value", el.get("weight", 0)),
        }
        for el in elements
    ]
    block = json.dumps(items, indent=2)
    return f"## Hard Targets\n\nMatch these values precisely:\n\n```json\n{block}\n```"


def _build_english_section(elements: list) -> str:
    """Build the English style guidance section."""
    if not elements:
        return ""
    lines = [translate_element(el) for el in elements]
    guidance = "\n".join(f"- {line}" for line in lines)
    return f"## Style Guidance\n\n{guidance}"


def _build_enforcement_section(elements: list, routing: dict, target_word_count: int) -> str:
    """Build the mandatory enforcement section."""
    if not elements:
        return ""
    lines = []
    for el in elements:
        row = routing.get(el["name"], {})
        template = row.get("enforcement_template") or ""
        if not template:
            # Fallback: simple English instruction
            instruction = translate_element(el)
        else:
            count_str = _compute_count(el, target_word_count, template)
            instruction = template.replace("{count}", count_str)
        lines.append(f"- {instruction}")
    body = "\n".join(lines)
    return f"## MANDATORY Enforcement\n\nThese rules are non-negotiable:\n\n{body}"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_style_guide(
    elements: list,
    target_word_count: int = 600,
    db_conn=None,
) -> str:
    """Build a 3-section style guide string from voice profile elements."""
    if not elements:
        return ""

    routing = _load_routing(db_conn)

    json_els = []
    english_els = []
    enforcement_els = []

    for el in elements:
        name = el.get("name", "")
        row = routing.get(name, {})
        override = row.get("detection_override")
        if override == "detection_wins":
            continue  # excluded from all sections

        strategy = row.get("strategy", "english")  # fallback: english

        if strategy in ("json", "json_enforced"):
            json_els.append(el)
        elif strategy in ("english", "hybrid"):
            english_els.append(el)
        elif strategy == "targeted_enforcement":
            enforcement_els.append(el)
        else:
            english_els.append(el)

    sections = []
    s = _build_json_section(json_els)
    if s:
        sections.append(s)
    s = _build_english_section(english_els)
    if s:
        sections.append(s)
    s = _build_enforcement_section(enforcement_els, routing, target_word_count)
    if s:
        sections.append(s)

    return "\n\n".join(sections)


# ---------------------------------------------------------------------------
# Seeding (Task 5 integration point)
# ---------------------------------------------------------------------------

def seed_routing_table(db_conn=None):
    """Seed element_routing table from JSON file if empty."""
    import os
    data_file = os.path.join(os.path.dirname(__file__), "..", "data", "element_routing.json")
    data_file = os.path.normpath(data_file)
    if not os.path.exists(data_file):
        return

    try:
        if db_conn is None:
            from db import get_connection
            db_conn = get_connection()

        cur = db_conn.cursor()
        cur.execute("SELECT COUNT(*) FROM element_routing")
        count = cur.fetchone()[0]
        if count > 0:
            return  # already seeded

        with open(data_file) as f:
            rows = json.load(f)

        for row in rows:
            cur.execute(
                """
                INSERT INTO element_routing
                    (element_name, strategy, best_score, detection_override, enforcement_template)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (element_name) DO UPDATE SET
                    strategy = EXCLUDED.strategy,
                    best_score = EXCLUDED.best_score,
                    detection_override = EXCLUDED.detection_override,
                    enforcement_template = EXCLUDED.enforcement_template
                """,
                (
                    row["element_name"],
                    row.get("strategy", "english"),
                    row.get("best_score"),
                    row.get("detection_override"),
                    row.get("enforcement_template"),
                ),
            )

        cur.execute(
            "INSERT INTO settings (key, value) VALUES ('routing_version', '1') "
            "ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value"
        )
        db_conn.commit()
    except Exception as e:
        print(f"[seed_routing_table] Warning: {e}")
