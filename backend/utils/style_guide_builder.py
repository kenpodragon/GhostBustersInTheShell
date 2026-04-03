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
        from db import query_all
        rows = query_all(
            "SELECT element_name, strategy, best_score, detection_override, enforcement_template "
            "FROM element_routing"
        )
        return {row["element_name"]: dict(row) for row in rows}
    except Exception:
        return {}


def _compute_count(element: dict, target_word_count: int) -> str:
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
        return f"~{pct}"

    if name in ("long_sentence_ratio", "short_sentence_ratio",
                "passive_voice_rate", "verb_tense_past_ratio",
                "verb_tense_present_ratio"):
        pct = round(weight * 100)
        return f"~{pct}"

    if name in ("article_rate", "named_entity_density"):
        val = round(weight * 100, 1)
        return f"~{val}"

    if name == "hedging_language_rate":
        raw = weight * (twc / 20)
        n = max(1, round(raw))
        return f"~{n}"

    if name == "parenthetical_usage":
        raw = weight * (twc / 20)
        n = max(1, round(raw))
        return str(n)

    if name == "intensifier_rate":
        raw = weight * (twc / 20)
        n = max(1, round(raw))
        return str(n)

    if name == "semicolon_usage":
        raw = weight * 0.5 * (twc / 20)
        n = max(1, round(raw))
        return str(n)

    if name == "figurative_language_markers":
        raw = weight * 0.3 * (twc / 20)
        n = max(1, round(raw))
        return str(n)

    if name == "transition_word_rate":
        raw = weight * 0.2 * (twc / 20)
        n = max(1, round(raw))
        return str(n)

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
    return f"## Voice Profile — Hard Targets\n\nMatch these quantitative targets precisely:\n\n```json\n{block}\n```"


def _build_english_section(elements: list) -> str:
    """Build the English style guidance section."""
    if not elements:
        return ""
    lines = [translate_element(el) for el in elements]
    guidance = "\n".join(f"- {line}" for line in lines)
    return f"## Voice Profile — Style Guidance\n\nFollow these voice patterns:\n\n{guidance}"


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
            count_str = _compute_count(el, target_word_count)
            instruction = template.replace("{count}", count_str)
        lines.append(f"{len(lines) + 1}. {instruction}")
    body = "\n".join(lines)
    return (
        "## MANDATORY Style Fingerprint Rules\n\n"
        "These specific patterns are NON-NEGOTIABLE. The author's voice depends on them.\n"
        "Verify each one before returning your text.\n\n"
        + body
    )


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

def seed_routing_table():
    """Seed element_routing table from JSON file if empty or outdated."""
    import os
    from db import get_conn, query_one

    data_file = os.path.join(os.path.dirname(__file__), "..", "data", "element_routing.json")
    data_file = os.path.normpath(data_file)
    if not os.path.exists(data_file):
        return

    try:
        with open(data_file, encoding="utf-8") as f:
            data = json.load(f)

        seed_version = data.get("version", "1.0.0")
        entries = data.get("routing", data if isinstance(data, list) else [])

        # Check current version in settings
        row = query_one("SELECT routing_version FROM settings WHERE id = 1")
        current_version = row["routing_version"] if row else "0.0.0"

        if current_version >= seed_version:
            return  # Already up to date

        # Upsert all routing entries
        with get_conn() as conn:
            cur = conn.cursor()
            for entry in entries:
                cur.execute(
                    """INSERT INTO element_routing
                       (element_name, strategy, best_score, detection_override, enforcement_template)
                       VALUES (%s, %s, %s, %s, %s)
                       ON CONFLICT (element_name) DO UPDATE SET
                           strategy = EXCLUDED.strategy,
                           best_score = EXCLUDED.best_score,
                           detection_override = EXCLUDED.detection_override,
                           enforcement_template = EXCLUDED.enforcement_template,
                           updated_at = NOW()
                    """,
                    (
                        entry["element_name"],
                        entry.get("strategy", "english"),
                        entry.get("best_score"),
                        entry.get("detection_override"),
                        entry.get("enforcement_template"),
                    ),
                )
            # Update version in settings
            cur.execute(
                "UPDATE settings SET routing_version = %s WHERE id = 1",
                (seed_version,),
            )
            cur.close()
        # get_conn auto-commits on exit
        print(f"[startup] Seeded element_routing table ({len(entries)} elements, v{seed_version})")
    except Exception as e:
        print(f"[seed_routing_table] Warning: {e}")
