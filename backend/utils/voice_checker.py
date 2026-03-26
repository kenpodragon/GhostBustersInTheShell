"""Check text against a voice profile for compliance."""
import re
import json


def check_voice_compliance(text: str, voice_profile_id: int = None, voice_elements: list = None) -> dict:
    """Check text against voice profile rules.

    Args:
        text: The text to check.
        voice_elements: Resolved list of element dicts from VoiceProfileService stack.
            When provided, checks directional elements with direction=="less" and weight>0.6.
        voice_profile_id: Legacy — fetches rules_json from DB if voice_elements not provided.

    Returns violations found and suggestions.
    """
    violations = []

    # New schema: check voice_elements directly
    if voice_elements:
        violations.extend(_check_elements(text, voice_elements))
    elif voice_profile_id:
        # Legacy: fetch from rules_json
        from db import query_one
        profile = query_one(
            "SELECT rules_json FROM voice_profiles WHERE id = %s",
            (voice_profile_id,)
        )
        if profile and profile["rules_json"]:
            rules = json.loads(profile["rules_json"])
        else:
            rules = _default_rules()

        # Check banned words (legacy schema)
        for word in rules.get("banned_words", []):
            if re.search(rf'\b{re.escape(word)}\b', text, re.IGNORECASE):
                violations.append({
                    "type": "banned_word",
                    "word": word,
                    "suggestion": f"Remove or replace '{word}' with a simpler alternative",
                })
    else:
        rules = _default_rules()
        for word in rules.get("banned_words", []):
            if re.search(rf'\b{re.escape(word)}\b', text, re.IGNORECASE):
                violations.append({
                    "type": "banned_word",
                    "word": word,
                    "suggestion": f"Remove or replace '{word}' with a simpler alternative",
                })

    # Check structural patterns (always applied)
    structural_checks = [
        (r"It is \w+ to \w+", "impersonal_construction", "Use active voice instead"),
        (r"In conclusion,?", "ai_conclusion", "Remove formulaic conclusion opener"),
        (r"Furthermore,?|Moreover,?|Additionally,?", "ai_transition", "Use simpler connectors"),
        (r"not only .+ but also", "parallel_construction", "Simplify the construction"),
    ]

    for pattern, violation_type, suggestion in structural_checks:
        if re.search(pattern, text, re.IGNORECASE):
            violations.append({
                "type": violation_type,
                "suggestion": suggestion,
            })

    return {
        "compliant": len(violations) == 0,
        "violation_count": len(violations),
        "violations": violations,
    }


def _check_elements(text: str, voice_elements: list) -> list:
    """Check resolved voice elements against text heuristically.

    Focuses on directional elements with direction=="less" and weight>0.6,
    which represent strong avoid signals. Checks vocabulary and punctuation.
    """
    violations = []

    # Map element names to heuristic checks
    _ELEMENT_CHECKS = {
        "em_dash_usage": (r"—", "em_dash", "Avoid em dashes (—); use commas or periods instead"),
        "semicolon_usage": (r";", "semicolon", "Avoid semicolons; use periods instead"),
        "passive_voice_rate": (r"\b(is|are|was|were|been|being)\s+\w+ed\b", "passive_voice", "Avoid passive voice constructions"),
        "ellipsis_usage": (r"\.{3}|…", "ellipsis", "Avoid overusing ellipses"),
        "parenthetical_usage": (r"\([^)]{20,}\)", "long_parenthetical", "Avoid long parenthetical asides"),
    }

    for element in voice_elements:
        direction = element.get("direction", "more")
        weight = element.get("weight", 0.5)
        name = element.get("name", "")

        # Only check "less" elements with high weight (strong avoid signals)
        if direction != "less" or weight <= 0.6:
            continue

        if name in _ELEMENT_CHECKS:
            pattern, vtype, suggestion = _ELEMENT_CHECKS[name]
            if re.search(pattern, text, re.IGNORECASE):
                violations.append({
                    "type": vtype,
                    "element": name,
                    "suggestion": suggestion,
                    "weight": weight,
                })

    return violations


def _default_rules() -> dict:
    """Default voice rules when no profile is specified."""
    return {
        "banned_words": [
            "leverage", "utilize", "spearhead", "synergize", "operationalize",
            "revolutionize", "supercharge", "harness", "empower", "elevate",
            "amplify", "streamline", "champion", "evangelize", "pioneer",
            "robust", "holistic", "innovative", "cutting-edge", "game-changing",
            "best-in-class", "world-class", "state-of-the-art", "mission-critical",
            "enterprise-grade", "paradigm", "synergy",
        ],
    }
