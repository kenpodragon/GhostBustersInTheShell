"""Lexical analysis heuristics for AI text detection.

Measures vocabulary diversity and richness using established
forensic linguistics metrics.
"""
import math
from collections import Counter
from utils.heuristics.text_utils import tokenize, MIN_WORDS
from utils.heuristics.reference_data import FUNCTION_WORD_FREQS


def check_yules_k(text: str) -> tuple[float, list[dict]]:
    """Yule's K statistic — vocabulary constancy measure.

    K = 10^4 * (M2 - N) / N^2
    where N = total tokens, M2 = sum(i^2 * freq_spectrum(i))

    Higher K = more vocabulary repetition = AI signal.
    AI text: K typically 150-300+ (repetitive vocabulary, reuses words)
    Human text: K typically 80-150 (more diverse, one-off word choices)
    """
    words = tokenize(text)
    n = len(words)
    if n < MIN_WORDS:
        return 0, []

    freq = Counter(words)
    spectrum = Counter(freq.values())

    m2 = sum(i * i * count for i, count in spectrum.items())
    k = 10_000 * (m2 - n) / (n * n) if n > 0 else 0

    patterns = []
    score = 0

    if k > 250:
        score = 45
        patterns.append({
            "pattern": "yules_k_very_high",
            "detail": f"Yule's K = {k:.1f} (very high vocabulary repetition, typical of AI)"
        })
    elif k > 150:
        score = 25
        patterns.append({
            "pattern": "yules_k_high",
            "detail": f"Yule's K = {k:.1f} (elevated vocabulary repetition, possibly AI)"
        })

    return score, patterns


def check_hapax_legomena(text: str) -> tuple[float, list[dict]]:
    """Hapax legomena ratio — proportion of words used exactly once.

    Human text: ~50-65% of unique words are hapax (used only once)
    AI text: ~35-50% hapax (AI reuses vocabulary more)
    """
    words = tokenize(text)
    if len(words) < MIN_WORDS:
        return 0, []

    freq = Counter(words)
    unique_count = len(freq)
    hapax_count = sum(1 for count in freq.values() if count == 1)

    if unique_count == 0:
        return 0, []

    hapax_ratio = hapax_count / unique_count
    patterns = []
    score = 0

    if hapax_ratio < 0.35:
        score = 40
        patterns.append({
            "pattern": "hapax_very_low",
            "detail": f"Hapax ratio {hapax_ratio:.2f} — only {hapax_ratio*100:.0f}% of words used once (AI recycles vocabulary)"
        })
    elif hapax_ratio < 0.50:
        score = 20
        patterns.append({
            "pattern": "hapax_low",
            "detail": f"Hapax ratio {hapax_ratio:.2f} — vocabulary reuse higher than typical human writing"
        })

    return score, patterns


def check_function_word_deviation(text: str) -> tuple[float, list[dict]]:
    """Measure how text's function word distribution deviates from natural English.

    Computes average relative deviation between observed function word frequencies
    and Brown Corpus reference frequencies.
    """
    words = tokenize(text)
    n = len(words)
    if n < MIN_WORDS:
        return 0, []

    word_freq = Counter(words)
    deviations = []
    for fw, expected_rate in FUNCTION_WORD_FREQS.items():
        observed_rate = (word_freq.get(fw, 0) / n) * 1000
        if expected_rate > 0:
            deviation = abs(observed_rate - expected_rate) / expected_rate
            deviations.append(deviation)

    if not deviations:
        return 0, []

    avg_deviation = sum(deviations) / len(deviations)
    patterns = []
    score = 0

    if avg_deviation > 0.8:
        score = 40
        patterns.append({
            "pattern": "function_word_high_deviation",
            "detail": f"Function word distribution deviates {avg_deviation:.0%} from natural English"
        })
    elif avg_deviation > 0.6:
        score = 20
        patterns.append({
            "pattern": "function_word_moderate_deviation",
            "detail": f"Function word distribution deviates {avg_deviation:.0%} from natural English"
        })

    return score, patterns


def check_mattr(text: str, window_size: int = 50) -> tuple[float, list[dict]]:
    """Moving Average Type-Token Ratio (MATTR).

    Low MATTR + low variance = AI signal.
    AI: MATTR ~0.65-0.72, human ~0.72-0.85
    """
    words = tokenize(text)
    n = len(words)
    if n < window_size + 20:
        return 0, []

    ttrs = []
    for i in range(n - window_size + 1):
        window = words[i:i + window_size]
        ttr = len(set(window)) / len(window)
        ttrs.append(ttr)

    if not ttrs:
        return 0, []

    avg_mattr = sum(ttrs) / len(ttrs)
    variance = sum((t - avg_mattr) ** 2 for t in ttrs) / len(ttrs)

    patterns = []
    score = 0

    if avg_mattr < 0.65:
        score += 25
        patterns.append({
            "pattern": "mattr_low",
            "detail": f"MATTR {avg_mattr:.3f} — low vocabulary richness across text"
        })
    elif avg_mattr < 0.72:
        score += 10

    num_windows = len(ttrs)
    if variance < 0.001 and num_windows > 100:
        score += 20
        patterns.append({
            "pattern": "mattr_uniform",
            "detail": f"MATTR variance {variance:.5f} — unnaturally consistent vocabulary density"
        })

    score = min(score, 45)
    return score, patterns
