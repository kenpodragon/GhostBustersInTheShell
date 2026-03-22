"""Check text against a voice profile for compliance."""
import re
import json


def check_voice_compliance(text: str, voice_profile_id: int = None) -> dict:
    """Check text against voice profile rules.

    Returns violations found and suggestions.
    """
    if voice_profile_id:
        from db import query_one
        profile = query_one(
            "SELECT rules_json FROM voice_profiles WHERE id = %s",
            (voice_profile_id,)
        )
        if profile and profile["rules_json"]:
            rules = json.loads(profile["rules_json"])
        else:
            rules = _default_rules()
    else:
        rules = _default_rules()

    violations = []

    # Check banned words
    for word in rules.get("banned_words", []):
        if re.search(rf'\b{re.escape(word)}\b', text, re.IGNORECASE):
            violations.append({
                "type": "banned_word",
                "word": word,
                "suggestion": f"Remove or replace '{word}' with a simpler alternative",
            })

    # Check structural patterns
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
