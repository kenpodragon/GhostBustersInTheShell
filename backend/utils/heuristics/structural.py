"""Structural analysis heuristics for AI text detection.

Analyzes text structure, word distributions, and information density
using statistical methods from computational linguistics.
"""
import re
import math
import zlib
from collections import Counter
from utils.heuristics.text_utils import tokenize, split_sentences, MIN_WORDS, MIN_CHARS

# Sentence openers that AI over-uses
AI_OPENER_WORDS = {
    "furthermore", "moreover", "additionally", "consequently", "nevertheless",
    "however", "therefore", "ultimately", "notably", "importantly",
    "significantly", "interestingly", "accordingly", "subsequently",
    "this", "these", "the", "it", "in",
}

HUMAN_OPENER_WORDS = {
    "i", "we", "you", "he", "she", "they", "my", "so", "but", "and",
    "well", "yeah", "ok", "look", "honestly", "basically",
}


def check_zipf_deviation(text: str) -> tuple[float, list[dict]]:
    """Measure deviation from Zipf's law.

    Zipf's law: frequency of word rank r ~ 1/r^alpha.
    Natural English: alpha ~ 1.0. AI often deviates.
    We fit log-log regression and measure alpha and R².
    """
    words = tokenize(text)
    if len(words) < MIN_WORDS:
        return 0, []

    freq = Counter(words)
    sorted_freqs = sorted(freq.values(), reverse=True)

    if len(sorted_freqs) < 10:
        return 0, []

    n = len(sorted_freqs)
    log_ranks = [math.log(i + 1) for i in range(n)]
    log_freqs = [math.log(f) for f in sorted_freqs]

    mean_x = sum(log_ranks) / n
    mean_y = sum(log_freqs) / n
    ss_xx = sum((x - mean_x) ** 2 for x in log_ranks)
    ss_xy = sum((x - mean_x) * (y - mean_y) for x, y in zip(log_ranks, log_freqs))

    if ss_xx == 0:
        return 0, []

    alpha = -ss_xy / ss_xx
    ss_yy = sum((y - mean_y) ** 2 for y in log_freqs)
    r_squared = (ss_xy ** 2) / (ss_xx * ss_yy) if ss_yy > 0 else 0

    patterns = []
    score = 0
    alpha_deviation = abs(alpha - 1.0)

    if alpha_deviation > 0.3:
        score = 35
        patterns.append({
            "pattern": "zipf_high_deviation",
            "detail": f"Zipf exponent α={alpha:.2f} (expected ~1.0), R²={r_squared:.2f} — unnatural word frequency distribution"
        })
    elif alpha_deviation > 0.15:
        score = 15
        patterns.append({
            "pattern": "zipf_moderate_deviation",
            "detail": f"Zipf exponent α={alpha:.2f}, R²={r_squared:.2f} — mild deviation from natural word distribution"
        })

    if r_squared < 0.75 and alpha_deviation <= 0.15:
        score += 10
        patterns.append({
            "pattern": "zipf_poor_fit",
            "detail": f"Zipf R²={r_squared:.2f} — word distribution doesn't follow natural language patterns well"
        })

    return min(score, 45), patterns


def check_compression_ratio(text: str) -> tuple[float, list[dict]]:
    """Kolmogorov complexity proxy via zlib compression.

    AI text compresses better (more predictable/repetitive).
    compression_ratio = len(compressed) / len(original_bytes)
    AI: ~0.30-0.45, Human: ~0.45-0.65
    """
    if len(text) < MIN_CHARS:
        return 0, []

    text_bytes = text.encode("utf-8")
    compressed = zlib.compress(text_bytes, level=9)
    ratio = len(compressed) / len(text_bytes)

    patterns = []
    score = 0

    if ratio < 0.35:
        score = 40
        patterns.append({
            "pattern": "compression_very_high",
            "detail": f"Compression ratio {ratio:.3f} — text is highly predictable/repetitive (strong AI signal)"
        })
    elif ratio < 0.45:
        score = 20
        patterns.append({
            "pattern": "compression_high",
            "detail": f"Compression ratio {ratio:.3f} — text compresses well, suggesting repetitive patterns"
        })

    return score, patterns


def check_sentence_opener_pos(text: str) -> tuple[float, list[dict]]:
    """Analyze sentence opening word patterns.

    AI over-uses: "Furthermore,", "Moreover,", "This", "The", "It is"
    Humans use: "I", "We", "So", "But", names, varied starters
    """
    sentences = split_sentences(text)
    if len(sentences) < 5:
        return 0, []

    ai_opener_count = 0
    human_opener_count = 0

    for s in sentences:
        first_word = s.split()[0].lower().rstrip(".,;:!?") if s.split() else ""
        if first_word in AI_OPENER_WORDS:
            ai_opener_count += 1
        if first_word in HUMAN_OPENER_WORDS:
            human_opener_count += 1

    total = len(sentences)
    ai_ratio = ai_opener_count / total
    human_ratio = human_opener_count / total

    patterns = []
    score = 0

    if ai_ratio > 0.4:
        score = 40
        patterns.append({
            "pattern": "sentence_opener_ai_heavy",
            "detail": f"{ai_ratio:.0%} of sentences start with AI-typical words (Furthermore, Moreover, This, etc.)"
        })
    elif ai_ratio > 0.25:
        score = 20
        patterns.append({
            "pattern": "sentence_opener_ai_moderate",
            "detail": f"{ai_ratio:.0%} of sentences start with AI-typical openers"
        })

    if human_ratio > 0.3 and score > 0:
        score = max(0, score - 15)

    return score, patterns


def check_word_length_distribution(text: str) -> tuple[float, list[dict]]:
    """Analyze word length distribution.

    AI clusters around 5-8 chars. Humans use more very short (1-3) and very long (10+) words.
    Low coefficient of variation (CV) = uniform lengths = AI signal.
    """
    words = tokenize(text)
    if len(words) < MIN_WORDS:
        return 0, []

    lengths = [len(w) for w in words]
    mean_len = sum(lengths) / len(lengths)
    if mean_len == 0:
        return 0, []

    variance = sum((l - mean_len) ** 2 for l in lengths) / len(lengths)
    std_dev = math.sqrt(variance)
    cv = std_dev / mean_len

    medium_words = sum(1 for l in lengths if 5 <= l <= 8) / len(lengths)

    patterns = []
    score = 0

    if cv < 0.45:
        score += 20
        patterns.append({
            "pattern": "word_length_uniform",
            "detail": f"Word length CV={cv:.2f} — unnaturally uniform word lengths"
        })

    if medium_words > 0.45:
        score += 15
        patterns.append({
            "pattern": "word_length_medium_cluster",
            "detail": f"{medium_words:.0%} of words are 5-8 chars — AI clusters in medium range"
        })

    return min(score, 35), patterns


def check_char_ngram_profile(text: str) -> tuple[float, list[dict]]:
    """Character trigram entropy analysis.

    AI text has LOWER character n-gram entropy (more predictable character sequences).
    """
    clean = re.sub(r'[^a-z ]', '', text.lower())
    if len(clean) < 100:
        return 0, []

    trigrams = [clean[i:i+3] for i in range(len(clean) - 2)]
    if not trigrams:
        return 0, []

    freq = Counter(trigrams)
    total = len(trigrams)

    entropy = -sum((c / total) * math.log2(c / total) for c in freq.values() if c > 0)
    max_entropy = math.log2(len(freq)) if len(freq) > 1 else 1
    normalized_entropy = entropy / max_entropy if max_entropy > 0 else 0

    patterns = []
    score = 0

    if normalized_entropy < 0.85:
        score = 25
        patterns.append({
            "pattern": "char_ngram_low_entropy",
            "detail": f"Character trigram entropy {normalized_entropy:.3f} — predictable character patterns"
        })
    elif normalized_entropy < 0.90:
        score = 10
        patterns.append({
            "pattern": "char_ngram_moderate_entropy",
            "detail": f"Character trigram entropy {normalized_entropy:.3f} — somewhat predictable"
        })

    return score, patterns
