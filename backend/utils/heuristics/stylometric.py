"""Stylometric analysis heuristics for AI text detection.

Uses authorship attribution techniques adapted for AI vs human distinction.
Based on Burrows' Delta (2002) and subsequent refinements.
"""
from collections import Counter
from utils.heuristics.text_utils import tokenize, MIN_WORDS

HUMAN_PROFILE = {
    "the": (69.97, 15.0), "of": (36.41, 10.0), "and": (28.85, 8.0),
    "to": (26.15, 7.5), "a": (23.08, 7.0), "in": (21.34, 6.5),
    "that": (10.59, 5.0), "is": (10.10, 4.5), "was": (9.78, 5.0),
    "it": (9.97, 4.5), "for": (9.49, 4.0), "as": (7.70, 3.5),
    "with": (7.17, 3.5), "his": (6.50, 4.0), "on": (6.09, 3.0),
    "be": (6.39, 3.5), "at": (5.30, 2.5), "by": (5.07, 2.5),
    "i": (5.16, 4.0), "this": (4.57, 3.0), "had": (4.89, 3.5),
    "not": (4.60, 2.5), "are": (4.39, 2.5), "but": (4.15, 2.5),
    "from": (3.97, 2.0), "or": (3.57, 2.0), "have": (3.57, 2.5),
    "an": (3.28, 2.0), "they": (2.77, 2.5), "which": (2.90, 2.0),
}


def check_burrows_delta(text: str) -> tuple[float, list[dict]]:
    """Burrows' Delta — stylometric distance from human writing profile.

    For each of the top 30 function words, compute:
    z_i = |observed_freq - expected_mean| / expected_std
    Delta = mean(z_i)

    Human text: Delta 0.5-1.2
    AI text: Delta 1.0-2.5+
    """
    words = tokenize(text)
    n = len(words)
    if n < MIN_WORDS:
        return 0, []

    word_freq = Counter(words)

    z_scores = []
    for word, (mean_rate, std_dev) in HUMAN_PROFILE.items():
        observed_rate = (word_freq.get(word, 0) / n) * 1000
        z = abs(observed_rate - mean_rate) / std_dev if std_dev > 0 else 0
        z_scores.append(z)

    if not z_scores:
        return 0, []

    delta = sum(z_scores) / len(z_scores)

    patterns = []
    score = 0

    if delta > 2.0:
        score = 45
        patterns.append({
            "pattern": "burrows_delta_high",
            "detail": f"Burrows' Delta = {delta:.2f} — writing style is far from natural human norms"
        })
    elif delta > 1.5:
        score = 25
        patterns.append({
            "pattern": "burrows_delta_moderate",
            "detail": f"Burrows' Delta = {delta:.2f} — writing style deviates from human norms"
        })
    elif delta > 1.2:
        score = 10
        patterns.append({
            "pattern": "burrows_delta_mild",
            "detail": f"Burrows' Delta = {delta:.2f} — slight stylistic deviation from human norms"
        })

    return score, patterns
