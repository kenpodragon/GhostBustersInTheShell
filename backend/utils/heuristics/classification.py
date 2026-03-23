"""3-category classification: Ghost Written / Ghost Touched / Clean.

Classifies text into one of three categories based on the overall score
and signal composition from detect_ai_patterns().

Categories:
- Ghost Written (AI): Dominant AI patterns, weak human tells
- Ghost Touched (Assisted): AI patterns present but human skeleton remains
- Clean (Human Only): No meaningful AI signals

Designed for expansion to finer categories later (e.g., Polished vs Paraphrased).
"""

# --- Category definitions ---

CATEGORIES = {
    "ghost_written": {
        "category": "ghost_written",
        "label": "Ghost Written",
        "subtitle": "AI",
    },
    "ghost_touched": {
        "category": "ghost_touched",
        "label": "Ghost Touched",
        "subtitle": "Assisted",
    },
    "clean": {
        "category": "clean",
        "label": "Clean",
        "subtitle": "Human Only",
    },
}

# --- AI signal names (presence = AI patterns detected) ---
AI_SIGNAL_PATTERNS = {
    "buzzword", "ai_phrase", "ai_transition", "hedge_word",
    "ai_opening_phrases", "ai_opening_phrases_heavy", "ai_opening_phrase",
    "not_only_but_also", "it_is_adj_to", "rule_of_three",
    "hedging_sandwich", "front_loaded_description",
    "dual_adjective_pair", "trailing_participial",
    "false_dichotomy", "emotional_exposition",
    "uniform_length", "heavy_structure", "moderate_structure",
    "closing_summary", "closing_summary_heavy",
}

# --- Human-absence signals (presence = human tells are MISSING) ---
HUMAN_ABSENCE_PATTERNS = {
    "no_contractions",
    "no_first_person", "low_first_person",
    "no_specifics",
    "no_digressions",
    "no_questions_exclamations",
}


def _count_ai_signals(patterns: list[dict]) -> int:
    """Count distinct AI signal types in detected patterns."""
    return len({p["pattern"] for p in patterns if p["pattern"] in AI_SIGNAL_PATTERNS})


def _count_human_absence(patterns: list[dict]) -> int:
    """Count human-absence signals (AI lacks human tells)."""
    return len({p["pattern"] for p in patterns if p["pattern"] in HUMAN_ABSENCE_PATTERNS})


def _has_human_tells(patterns: list[dict]) -> int:
    """Count how many human tells are PRESENT (absence signals NOT fired).

    We check which human-absence signals did NOT fire — meaning the human
    tell IS present. More present human tells = more likely Ghost Touched or Clean.
    """
    absent = {p["pattern"] for p in patterns if p["pattern"] in HUMAN_ABSENCE_PATTERNS}
    # Each human-absence signal NOT present = that human tell exists
    present_count = len(HUMAN_ABSENCE_PATTERNS) - len(absent)
    return present_count


def _compute_confidence(score: float, category: str) -> str:
    """Compute confidence level based on how deep into the category the score falls."""
    if category == "ghost_written":
        if score >= 60:
            return "high"
        elif score >= 50:
            return "medium"
        else:
            return "low"
    elif category == "clean":
        if score <= 10:
            return "high"
        elif score <= 15:
            return "medium"
        else:
            return "low"
    else:  # ghost_touched
        # Middle of the range = higher confidence for this category
        if 28 <= score <= 38:
            return "medium"
        else:
            return "low"


def classify_category(result: dict) -> dict:
    """Classify detection result into Ghost Written / Ghost Touched / Clean.

    Args:
        result: The dict returned by detect_ai_patterns(), containing at minimum:
            - overall_score (float)
            - detected_patterns (list of dicts with "pattern" key)

    Returns:
        Dict with: category, label, subtitle, confidence
    """
    score = result.get("overall_score", 0)
    patterns = result.get("detected_patterns", [])

    ai_signal_count = _count_ai_signals(patterns)
    human_tells = _has_human_tells(patterns)
    human_absence_count = _count_human_absence(patterns)

    # --- Rule 1: Clean (Human Only) ---
    # Score ≤ 20: clean regardless
    # Score ≤ 30: clean if strong human tells (3+ present)
    if score <= 20:
        category = "clean"
    elif score <= 30 and human_tells >= 3:
        category = "clean"

    # --- Rule 2: Ghost Written (AI) ---
    # Score ≥ 45: ghost written regardless
    # Score ≥ 35: ghost written if weak human tells (<2) AND 3+ AI signal types
    elif score >= 45:
        category = "ghost_written"
    elif score >= 35 and human_tells < 2 and ai_signal_count >= 3:
        category = "ghost_written"

    # --- Rule 3: Ghost Touched (Assisted) — everything else ---
    else:
        category = "ghost_touched"

    confidence = _compute_confidence(score, category)

    return {
        **CATEGORIES[category],
        "confidence": confidence,
    }
