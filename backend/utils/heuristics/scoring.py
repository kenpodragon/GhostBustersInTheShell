"""Scoring engine for AI text detection.

Replaces simple averaging with weighted Bayesian signal combination,
genre-aware baselines, and confidence interval estimation.
"""
import re
from utils.heuristics.reference_data import HEURISTIC_WEIGHTS, GENRE_BASELINES


def combine_signals(signals: dict[str, float]) -> float:
    """Combine heuristic signals using weighted averaging with signal count bonus.

    Each signal's contribution is weighted by its discriminative power
    (from HEURISTIC_WEIGHTS). Signals scoring 0 are excluded entirely.

    Args:
        signals: dict of {heuristic_name: score} where score is 0-100

    Returns:
        Combined score 0-100
    """
    active = {k: v for k, v in signals.items() if v > 0}
    if not active:
        return 0

    weighted_sum = 0
    weight_total = 0
    for name, score in active.items():
        w = HEURISTIC_WEIGHTS.get(name, 0.5)
        weighted_sum += score * w
        weight_total += w

    if weight_total == 0:
        return 0

    base_score = weighted_sum / weight_total

    # Signal count bonus: convergence of evidence
    count_bonus = min(20, (len(active) - 1) * 4)

    # Extra boost when multiple high-confidence signals agree
    high_conf_signals = [s for n, s in active.items()
                         if HEURISTIC_WEIGHTS.get(n, 0) >= 0.7]
    if len(high_conf_signals) >= 3:
        avg_high = sum(high_conf_signals) / len(high_conf_signals)
        if avg_high > 30:
            count_bonus += 5

    return min(100, base_score + count_bonus)


def estimate_confidence(score: float, signal_count: int, word_count: int) -> tuple[float, float]:
    """Estimate confidence interval for an AI detection score.

    Wider intervals for: fewer signals, shorter text, mid-range scores.
    Returns (lower_bound, upper_bound).
    """
    base_margin = 15

    signal_factor = max(0.4, 1.0 - (signal_count * 0.08))
    word_factor = max(0.5, 1.0 - (word_count / 1000))

    extremity = abs(score - 50) / 50
    extremity_factor = max(0.5, 1.0 - (extremity * 0.4))

    margin = base_margin * signal_factor * word_factor * extremity_factor

    lower = max(0, score - margin)
    upper = min(100, score + margin)

    return round(lower, 1), round(upper, 1)


def detect_genre(text: str) -> str:
    """Auto-detect text genre for baseline selection.

    Uses simple keyword/pattern heuristics to classify text into one of:
    general, academic, casual, business, creative, resume
    """
    text_lower = text.lower()
    words = re.findall(r"[a-z']+", text_lower)
    word_count = len(words)

    if word_count == 0:
        return "general"

    word_set = set(words)

    academic_words = {"study", "research", "analysis", "findings", "hypothesis",
                      "methodology", "participants", "results", "significant",
                      "correlation", "data", "sample", "statistical", "literature",
                      "et", "al", "conclusion", "abstract", "variables"}
    academic_score = len(word_set & academic_words) / max(1, min(word_count / 20, 10))

    casual_words = {"i", "you", "we", "gonna", "wanna", "kinda", "yeah", "ok",
                    "lol", "haha", "dunno", "tbh", "honestly", "basically", "stuff",
                    "thing", "things", "guys", "cool", "awesome"}
    casual_score = len(word_set & casual_words) / max(1, min(word_count / 20, 10))

    contraction_count = len(re.findall(r"\b\w+'(?:t|s|re|ve|ll|d|m)\b", text_lower))
    casual_score += min(0.5, contraction_count / max(1, word_count / 50))

    business_words = {"stakeholders", "roi", "kpi", "deliverables", "synergy",
                      "pipeline", "quarterly", "revenue", "strategy", "initiative",
                      "alignment", "scalable", "leverage", "optimize", "metrics"}
    business_score = len(word_set & business_words) / max(1, min(word_count / 20, 10))

    resume_words = {"experience", "responsibilities", "proficient", "managed",
                    "developed", "implemented", "skills", "team", "led",
                    "achieved", "bachelor", "master", "certification"}
    resume_score = len(word_set & resume_words) / max(1, min(word_count / 20, 10))

    creative_words = {"whispered", "echoed", "shadows", "moonlight", "silence",
                      "breath", "trembling", "darkness", "heart", "soul", "dream",
                      "murmured", "gaze", "softly"}
    creative_score = len(word_set & creative_words) / max(1, min(word_count / 20, 10))

    scores = {
        "academic": academic_score,
        "casual": casual_score,
        "business": business_score,
        "resume": resume_score,
        "creative": creative_score,
    }

    best = max(scores, key=scores.get)
    if scores[best] > 0.15:
        return best
    return "general"
