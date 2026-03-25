#!/usr/bin/env python3
"""Extract all hardcoded detection constants into rules_defaults.json.gz + rules_version.json.

Run from code/ directory:
    python tools/extract_rules_defaults.py
"""
import gzip
import json
import os
import sys
from datetime import date

# Ensure backend is importable.
# When run as `python tools/extract_rules_defaults.py` from code/, CODE_DIR = code/
# When run inside Docker where backend/ is mounted at /app/, detect that case.
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CODE_DIR = os.path.dirname(SCRIPT_DIR)
BACKEND_DIR = os.path.join(CODE_DIR, "backend")

# Docker fallback: if backend/ doesn't exist at computed path, try /app/
if not os.path.isdir(BACKEND_DIR):
    if os.path.isdir("/app/utils"):
        BACKEND_DIR = "/app"
        CODE_DIR = os.path.dirname(BACKEND_DIR)

sys.path.insert(0, BACKEND_DIR)

OUTPUT_DIR = os.path.join(BACKEND_DIR, "data")
VERSION = "1.0.0"
TODAY = date.today().isoformat()


def extract_reference_data() -> dict:
    """Extract constants from utils.heuristics.reference_data."""
    from utils.heuristics.reference_data import (
        HEURISTIC_WEIGHTS,
        HARD_BAN_VERBS,
        HARD_BAN_ADJ,
        HARD_BAN_FILLER,
        HARD_BAN_FILLER_PHRASES,
        FUNCTION_WORD_FREQS,
        GENRE_BASELINES,
    )
    return {
        "heuristic_weights": dict(HEURISTIC_WEIGHTS),
        "buzzwords": {
            "hard_ban_verbs": sorted(HARD_BAN_VERBS),
            "hard_ban_adj": sorted(HARD_BAN_ADJ),
            "hard_ban_filler": sorted(HARD_BAN_FILLER),
            "hard_ban_filler_phrases": list(HARD_BAN_FILLER_PHRASES),
        },
        "function_word_freqs": dict(FUNCTION_WORD_FREQS),
        "genre_baselines": dict(GENRE_BASELINES),
    }


def extract_ai_phrases() -> dict:
    """Extract AI phrase categories from utils.heuristics.ai_phrases."""
    from utils.heuristics.ai_phrases import (
        VAGUE_ABSTRACTIONS,
        FALSE_DEPTH,
        METAPHOR_CLICHES,
        CORPORATE_ACTION,
        HEDGING_FILLERS,
        FALSE_INSIDER,
    )
    return {
        "vague_abstraction": list(VAGUE_ABSTRACTIONS),
        "false_depth": list(FALSE_DEPTH),
        "metaphor_cliche": list(METAPHOR_CLICHES),
        "corporate_action": list(CORPORATE_ACTION),
        "hedging_filler": list(HEDGING_FILLERS),
        "false_insider": list(FALSE_INSIDER),
    }


def extract_severity() -> dict:
    """Extract severity constants from utils.heuristics.severity."""
    from utils.heuristics.severity import SEVERITY_MULTIPLIERS, SEVERITY_POINTS
    return {
        "multipliers": dict(SEVERITY_MULTIPLIERS),
        "points": dict(SEVERITY_POINTS),
        "thresholds": {
            "caution_max": 1,
            "warning_max": 3,
            "strong_min": 4,
        },
    }


def extract_classification() -> dict:
    """Extract classification boundaries from utils.heuristics.classification."""
    # These are inline in classify_category — extract the logic thresholds
    return {
        "clean_upper": 20,
        "clean_with_tells_upper": 30,
        "clean_human_tells_min": 3,
        "ghost_written_lower": 40,
        "ghost_written_assisted_lower": 32,
        "ghost_written_assisted_human_tells_max": 2,
        "ghost_written_assisted_ai_signals_min": 3,
        "confidence": {
            "ghost_written_high": 60,
            "ghost_written_medium": 50,
            "clean_high": 10,
            "clean_medium": 15,
            "ghost_touched_medium_low": 28,
            "ghost_touched_medium_high": 38,
        },
    }


def extract_pipeline() -> dict:
    """Extract pipeline constants from scoring.py and router.py."""
    # From router.py: route_analysis combined_score = ai * 0.6 + heuristic * 0.4
    # From scoring.py: composite_score weights and bonuses
    return {
        "ai_weight": 0.6,
        "heuristic_weight": 0.4,
        "sentence_tier_weight": 0.45,
        "paragraph_tier_weight": 0.30,
        "document_tier_weight": 0.25,
        "convergence_bonus_max": 10,
        "convergence_variance_threshold": 100,
        "density_bonus_max_3tier": 10,
        "density_bonus_min_signals_3tier": 8,
        "density_bonus_max_2tier": 5,
        "density_bonus_min_signals_2tier": 5,
        "signal_count_bonus_max": 15,
        "signal_count_bonus_per_signal": 3,
        "signal_count_bonus_min_signals": 2,
        "signal_count_bonus_weight_threshold": 0.3,
        "high_conf_convergence_count": 3,
        "high_conf_convergence_avg_threshold": 30,
        "high_conf_convergence_bonus": 5,
        "high_conf_weight_threshold": 0.7,
    }


def extract_word_lists() -> dict:
    """Extract inline word lists from detector.py functions."""
    # _check_hedge_words hedges list (regex patterns)
    hedges = [
        r'\bhowever\b', r'\bfurthermore\b', r'\bmoreover\b', r'\badditionally\b',
        r'\bconsequently\b', r'\bnevertheless\b', r'\bnotably\b', r'\bimportantly\b',
        r'\bsignificantly\b', r'\bundoubtedly\b', r'\bultimately\b',
        r"\bit'?s fair to say\b", r'\bit bears mentioning\b',
        r'\bit stands to reason\b', r'\bgenerally speaking\b',
        r'\bbroadly speaking\b', r'\bby and large\b',
        r'\bmore often than not\b', r'\bneedless to say\b',
        r'\bgiven the circumstances\b',
    ]

    # _check_transitions patterns
    transitions = [
        r'^(In conclusion|To summarize|In summary|Overall|In essence)',
        r'^(It is worth noting|It should be noted|It is important to)',
        r'^(This (demonstrates|illustrates|highlights|underscores|showcases))',
        r'^(By (leveraging|utilizing|harnessing|implementing))',
    ]

    # _check_hedge_clusters hedge_words set
    hedge_cluster_words = sorted([
        "however", "furthermore", "moreover", "additionally", "consequently",
        "nevertheless", "notably", "importantly", "significantly", "ultimately",
        "it's worth noting", "it should be noted", "it is important to note",
        "interestingly", "remarkably", "arguably", "admittedly",
    ])

    # _check_transition_stacks stack_starters
    transition_stack_starters = sorted([
        "moreover", "furthermore", "additionally", "consequently", "subsequently",
        "similarly", "likewise", "conversely", "nevertheless", "nonetheless",
        "in addition", "as a result", "on the other hand", "in contrast",
    ])

    return {
        "hedge_patterns": hedges,
        "transition_patterns": transitions,
        "hedge_cluster_words": hedge_cluster_words,
        "transition_stack_starters": transition_stack_starters,
    }


def extract_ai_prompt() -> str:
    """Extract ANALYZE_PROMPT from claude_provider."""
    from ai_providers.claude_provider import ANALYZE_PROMPT
    return ANALYZE_PROMPT


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("Extracting rules defaults...")

    # 1. Reference data
    ref = extract_reference_data()
    print(f"  heuristic_weights: {len(ref['heuristic_weights'])} weights")
    print(f"  buzzwords: {sum(len(v) for v in ref['buzzwords'].values())} items")
    print(f"  function_word_freqs: {len(ref['function_word_freqs'])} words")
    print(f"  genre_baselines: {len(ref['genre_baselines'])} genres")

    # 2. AI phrases
    ai_phrases = extract_ai_phrases()
    total_phrases = sum(len(v) for v in ai_phrases.values())
    print(f"  ai_phrases: {total_phrases} phrases in {len(ai_phrases)} categories")

    # 3. Severity
    severity = extract_severity()
    print(f"  severity: {len(severity['multipliers'])} tiers")

    # 4. Classification
    classification = extract_classification()
    print(f"  classification: {len(classification)} boundary groups")

    # 5. Pipeline
    pipeline = extract_pipeline()
    print(f"  pipeline: {len(pipeline)} constants")

    # 6. Word lists
    word_lists = extract_word_lists()
    total_wl = sum(len(v) for v in word_lists.values())
    print(f"  word_lists: {total_wl} items in {len(word_lists)} lists")

    # 7. AI prompt
    ai_prompt = extract_ai_prompt()
    print(f"  ai_prompt: {len(ai_prompt)} chars")

    # Build output
    rules = {
        "version": VERSION,
        "date": TODAY,
        "sections": {
            "heuristic_weights": ref["heuristic_weights"],
            "buzzwords": ref["buzzwords"],
            "ai_phrases": ai_phrases,
            "word_lists": word_lists,
            "thresholds": {
                "genre_baselines": ref["genre_baselines"],
                "function_word_freqs": ref["function_word_freqs"],
            },
            "classification": classification,
            "severity": severity,
            "pipeline": pipeline,
            "ai_prompt": ai_prompt,
        },
    }

    # Write compressed JSON
    gz_path = os.path.join(OUTPUT_DIR, "rules_defaults.json.gz")
    json_bytes = json.dumps(rules, indent=2, ensure_ascii=False).encode("utf-8")
    with gzip.open(gz_path, "wb") as f:
        f.write(json_bytes)
    gz_size = os.path.getsize(gz_path)
    print(f"\nWrote {gz_path} ({gz_size:,} bytes compressed, {len(json_bytes):,} bytes uncompressed)")

    # Write version file
    version_info = {
        "version": VERSION,
        "date": TODAY,
        "min_app_version": "1.0.0",
        "changelog": "Initial rules extraction from Python source",
    }
    version_path = os.path.join(OUTPUT_DIR, "rules_version.json")
    with open(version_path, "w") as f:
        json.dump(version_info, f, indent=2)
    print(f"Wrote {version_path}")

    print("\nDone.")


if __name__ == "__main__":
    main()
