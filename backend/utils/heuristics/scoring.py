"""Scoring engine for AI text detection.

Replaces simple averaging with weighted Bayesian signal combination,
genre-aware baselines, and confidence interval estimation.
"""
import re
from utils.heuristics.reference_data import HEURISTIC_WEIGHTS, GENRE_BASELINES
from utils.rules_config import rules_config


def combine_signals(signals: dict[str, float]) -> float:
    """Combine heuristic signals using weighted averaging with signal count bonus.

    Each signal's contribution is weighted by its discriminative power
    (from HEURISTIC_WEIGHTS). Signals scoring 0 are excluded entirely.

    Args:
        signals: dict of {heuristic_name: score} where score is 0-100

    Returns:
        Combined score 0-100
    """
    # Filter out signals with zero weight (killed heuristics)
    active = {}
    for k, v in signals.items():
        if v > 0 and (rules_config.weights or HEURISTIC_WEIGHTS).get(k, 0.5) > 0:
            active[k] = v

    if not active:
        return 0

    weighted_sum = 0
    weight_total = 0
    for name, score in active.items():
        w = (rules_config.weights or HEURISTIC_WEIGHTS).get(name, 0.5)
        weighted_sum += score * w
        weight_total += w

    if weight_total == 0:
        return 0

    base_score = weighted_sum / weight_total

    # Signal count bonus: convergence of evidence
    # Only count signals with meaningful weight (>= 0.3) to avoid
    # inflating scores from many weak/noisy signals
    meaningful_signals = [n for n in active if (rules_config.weights or HEURISTIC_WEIGHTS).get(n, 0) >= 0.3]
    count_bonus = min(15, max(0, len(meaningful_signals) - 2) * 3)

    # Extra boost when multiple high-confidence signals agree
    high_conf_signals = [s for n, s in active.items()
                         if (rules_config.weights or HEURISTIC_WEIGHTS).get(n, 0) >= 0.7]
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

    # Memoir/personal narrative detection
    memoir_words = {"remember", "remembered", "childhood", "grew", "father", "mother",
                    "years", "old", "family", "home", "school", "friends", "life",
                    "story", "stories", "decided", "realized", "felt", "thought"}
    memoir_score = len(word_set & memoir_words) / max(1, min(word_count / 20, 10))
    # Memoir often uses first-person past tense
    first_person_past = len(re.findall(r"\bI\s+(?:was|had|went|saw|felt|thought|knew|decided|remember)", text))
    memoir_score += min(0.5, first_person_past / max(1, word_count / 100))

    # Poetry detection
    lines = text.strip().split('\n')
    non_empty_lines = [l for l in lines if l.strip()]
    if non_empty_lines:
        avg_line_len = sum(len(l.strip()) for l in non_empty_lines) / len(non_empty_lines)
        # Poetry has short lines (< 60 chars avg) and many line breaks relative to words
        line_ratio = len(non_empty_lines) / max(1, word_count / 10)
        poetry_score = 0
        if avg_line_len < 60 and line_ratio > 0.5:
            poetry_score = 0.5
        if avg_line_len < 40:
            poetry_score += 0.3
        # No sentence-ending punctuation on most lines = poetry
        lines_without_period = sum(1 for l in non_empty_lines if not l.strip().endswith(('.', '!', '?')))
        if lines_without_period / max(1, len(non_empty_lines)) > 0.6:
            poetry_score += 0.2
    else:
        poetry_score = 0

    # Literary fiction — older/classic style with formal 3rd person narrative
    literary_words = {"whom", "whilst", "hitherto", "wherein", "countenance",
                      "therefore", "indeed", "manner", "exclaimed", "replied",
                      "observed", "remarked", "henceforth", "accordingly"}
    literary_score = len(word_set & literary_words) / max(1, min(word_count / 20, 10))
    # High semicolon or em-dash usage + 3rd person = literary
    semicolons = text.count(';')
    em_dashes = text.count('—') + text.count(' - ')
    if semicolons > 2 or em_dashes > 3:
        literary_score += 0.15

    scores = {
        "academic": academic_score,
        "casual": casual_score,
        "business": business_score,
        "resume": resume_score,
        "creative": creative_score,
        "memoir": memoir_score,
        "poetry": poetry_score,
        "literary": literary_score,
    }

    best = max(scores, key=scores.get)
    if scores[best] > 0.15:
        return best
    return "general"


def composite_score(
    sentence_score: float,
    paragraph_score: float,
    document_score: float,
    sentence_signals: int,
    paragraph_signals: int,
    document_signals: int,
) -> float:
    """Compute 3-tier composite AI detection score.

    Weights (calibrated against 126-sample corpus, Phase 3.5):
    - Sentence-level: 45% (best discriminator, +21.7 AI-human gap)
    - Paragraph-level: 30% (good intermediate signal, +18.0 gap)
    - Document-level: 25% (weakest discriminator, +8.5 gap — many heuristics fire on human literary text)

    Bonuses:
    - Convergence: if all three tiers agree (low variance), +5-10 points
    - Signal density: more signals across tiers = higher confidence

    Returns: composite score 0-100
    """
    if sentence_score == 0 and paragraph_score == 0 and document_score == 0:
        return 0.0

    # Weighted blend
    _pipe = rules_config.pipeline
    weighted = (
        sentence_score * _pipe.get("sentence_tier_weight", 0.45) +
        paragraph_score * _pipe.get("paragraph_tier_weight", 0.30) +
        document_score * _pipe.get("document_tier_weight", 0.25)
    )

    # Convergence bonus: all tiers agreeing boosts confidence
    scores = [sentence_score, paragraph_score, document_score]
    non_zero = [s for s in scores if s > 0]
    if len(non_zero) >= 2:
        mean = sum(non_zero) / len(non_zero)
        variance = sum((s - mean) ** 2 for s in non_zero) / len(non_zero)
        # Low variance = high agreement = bonus
        if variance < 100:  # scores within ~10 points of each other
            convergence_bonus = min(10, (100 - variance) / 10)
        else:
            convergence_bonus = 0
    else:
        convergence_bonus = 0

    # Cross-tier signal density bonus
    total_signals = sentence_signals + paragraph_signals + document_signals
    tiers_with_signals = sum(1 for s in [sentence_signals, paragraph_signals, document_signals] if s > 0)
    density_bonus = 0
    if tiers_with_signals >= 3 and total_signals >= 8:
        density_bonus = min(10, (total_signals - 8) * 2)
    elif tiers_with_signals >= 2 and total_signals >= 5:
        density_bonus = min(5, (total_signals - 5))

    return min(100, round(weighted + convergence_bonus + density_bonus, 1))


def composite_score_detailed(
    sentence_score: float, paragraph_score: float, document_score: float,
    sentence_signals: int, paragraph_signals: int, document_signals: int,
) -> dict:
    """Compute 3-tier composite score with full math breakdown."""
    if sentence_score == 0 and paragraph_score == 0 and document_score == 0:
        return {"score": 0.0, "score_math": {
            "sentence_weighted": 0.0, "paragraph_weighted": 0.0, "document_weighted": 0.0,
            "convergence_bonus": 0.0, "cross_tier_bonus": 0.0, "raw_composite": 0.0, "final_score": 0.0,
        }}

    _pipe = rules_config.pipeline
    sw = _pipe.get("sentence_tier_weight", 0.45)
    pw = _pipe.get("paragraph_tier_weight", 0.30)
    dw = _pipe.get("document_tier_weight", 0.25)

    sentence_weighted = round(sentence_score * sw, 1)
    paragraph_weighted = round(paragraph_score * pw, 1)
    document_weighted = round(document_score * dw, 1)
    weighted = sentence_weighted + paragraph_weighted + document_weighted

    scores = [sentence_score, paragraph_score, document_score]
    non_zero = [s for s in scores if s > 0]
    if len(non_zero) >= 2:
        mean = sum(non_zero) / len(non_zero)
        variance = sum((s - mean) ** 2 for s in non_zero) / len(non_zero)
        convergence_bonus = min(10, (100 - variance) / 10) if variance < 100 else 0
    else:
        convergence_bonus = 0

    total_signals = sentence_signals + paragraph_signals + document_signals
    tiers_with_signals = sum(1 for s in [sentence_signals, paragraph_signals, document_signals] if s > 0)
    density_bonus = 0
    if tiers_with_signals >= 3 and total_signals >= 8:
        density_bonus = min(10, (total_signals - 8) * 2)
    elif tiers_with_signals >= 2 and total_signals >= 5:
        density_bonus = min(5, (total_signals - 5))

    final = min(100, round(weighted + convergence_bonus + density_bonus, 1))

    return {"score": final, "score_math": {
        "sentence_weighted": sentence_weighted, "paragraph_weighted": paragraph_weighted,
        "document_weighted": document_weighted, "convergence_bonus": round(convergence_bonus, 1),
        "cross_tier_bonus": round(density_bonus, 1), "raw_composite": round(weighted, 1), "final_score": final,
    }}
