"""Phase 3.8: Statistical Language Model Signals.

Provides 8 signal functions for AI text detection based on n-gram perplexity,
compression entropy, and statistical distribution analysis.
"""
import gzip
import json
import math
import re
import zlib
from collections import Counter
from pathlib import Path

import numpy as np
from scipy import stats as scipy_stats

# Module-level cache for loaded corpora
_corpus_cache = {}
_genre_baselines_cache = None

DATA_DIR = Path(__file__).parent / "data"


def load_corpus(name="combined"):
    """Load a pre-computed trigram corpus. Returns None if file missing.

    Caches in module-level variable for subsequent calls.
    """
    if name in _corpus_cache:
        return _corpus_cache[name]

    path = DATA_DIR / f"{name}_trigrams.json.gz"
    if not path.exists():
        return None

    try:
        with gzip.open(path, "rb") as f:
            data = json.loads(f.read().decode("utf-8"))
        _corpus_cache[name] = data
        return data
    except Exception:
        return None


def get_genre_baselines():
    """Load genre baseline statistics for MATTR/TTR comparison."""
    global _genre_baselines_cache
    if _genre_baselines_cache is not None:
        return _genre_baselines_cache

    path = DATA_DIR / "genre_baselines.json"
    if not path.exists():
        return {}

    try:
        with open(path) as f:
            _genre_baselines_cache = json.load(f)
        return _genre_baselines_cache
    except Exception:
        return {}


def preprocess_text(text):
    """Clean text for trigram analysis.

    Strips URLs, code blocks, emails, non-Latin chars. Lowercases.
    """
    if not text:
        return ""

    # Strip code blocks (triple backtick)
    text = re.sub(r"```[\s\S]*?```", " ", text)

    # Strip URLs
    text = re.sub(r"https?://\S+", " ", text)

    # Strip email addresses
    text = re.sub(r"\S+@\S+\.\S+", " ", text)

    # Lowercase
    text = text.lower()

    # Keep only Latin alphabet, digits, basic punctuation, spaces
    text = re.sub(r"[^\x20-\x7E]", " ", text)

    # Collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()

    return text


def _split_sentences(text):
    """Simple sentence splitter."""
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    return [s.strip() for s in sentences if s.strip()]


def _get_words(text):
    """Extract words from text."""
    return re.findall(r"[a-z']+", text.lower())


# === Category A: Internal Entropy ===

def check_compression_ratio_sentence(text):
    """A1: Per-sentence compression ratio with sliding window entropy.

    AI text compresses more efficiently at sentence level.
    Min text: 20 characters.
    """
    if len(text) < 20:
        return 0.0, []

    original = text.encode("utf-8")
    if len(original) < 10:
        return 0.0, []

    compressed = zlib.compress(original)
    ratio = len(compressed) / len(original)

    # Sliding window entropy (256-char windows)
    window_size = 256
    window_ratios = []
    text_bytes = text.encode("utf-8")
    if len(text_bytes) >= window_size:
        for i in range(0, len(text_bytes) - window_size + 1, window_size // 2):
            chunk = text_bytes[i:i + window_size]
            c = zlib.compress(chunk)
            window_ratios.append(len(c) / len(chunk))

    # Score: lower ratio = more compressible = more AI-like
    if ratio < 0.35:
        score = 60.0
    elif ratio < 0.45:
        score = 40.0
    elif ratio < 0.55:
        score = 20.0
    else:
        score = 0.0

    # Window variance bonus: low variance = uniform = AI-like
    if len(window_ratios) >= 2:
        variance = float(np.var(window_ratios))
        if variance < 0.001:
            score = min(100, score + 20)

    patterns = []
    if score > 0:
        patterns.append({
            "pattern": "compression_ratio_sentence",
            "detail": f"Compression ratio {ratio:.3f} — text is highly compressible (AI-like)"
        })

    return score, patterns


def check_compression_ratio_document(text):
    """A2: Cross-sentence compression delta.

    Compresses each sentence individually vs. full text as one block.
    High delta = sentences share structure = AI-like.
    Min text: 3+ sentences.
    """
    sentences = _split_sentences(text)
    if len(sentences) < 3:
        return 0.0, []

    # Compress each sentence individually
    individual_sizes = []
    for sent in sentences:
        encoded = sent.encode("utf-8")
        if len(encoded) < 5:
            continue
        individual_sizes.append(len(zlib.compress(encoded)))

    if not individual_sizes:
        return 0.0, []

    sum_individual = sum(individual_sizes)

    # Compress full text as one block
    full_compressed = len(zlib.compress(text.encode("utf-8")))

    # Delta: how much better full compression is vs sum of parts
    delta = (sum_individual - full_compressed) / sum_individual if sum_individual > 0 else 0

    # Variance of per-sentence ratios
    sent_ratios = []
    for sent in sentences:
        encoded = sent.encode("utf-8")
        if len(encoded) < 5:
            continue
        ratio = len(zlib.compress(encoded)) / len(encoded)
        sent_ratios.append(ratio)

    ratio_variance = float(np.var(sent_ratios)) if len(sent_ratios) >= 2 else 0.5

    # Score based on delta
    if delta > 0.25:
        score = 60.0
    elif delta > 0.18:
        score = 40.0
    elif delta > 0.12:
        score = 20.0
    else:
        score = 0.0

    # Low variance bonus
    if ratio_variance < 0.002 and len(sent_ratios) >= 3:
        score = min(100, score + 15)

    patterns = []
    if score > 0:
        patterns.append({
            "pattern": "compression_ratio_document",
            "detail": f"Cross-sentence compression delta {delta:.3f}, ratio variance {ratio_variance:.4f}"
        })

    return score, patterns


def check_repetition_density(text):
    """A3: N-gram repetition density within text.

    AI recycles syntactic structures more consistently.
    Min text: 30 words.
    """
    words = _get_words(text)
    if len(words) < 30:
        return 0.0, []

    # Bigram repetition
    bigrams = [f"{words[i]} {words[i+1]}" for i in range(len(words) - 1)]
    bigram_counts = Counter(bigrams)
    repeated_bigrams = sum(1 for c in bigram_counts.values() if c > 1)
    bigram_ratio = repeated_bigrams / len(bigram_counts) if bigram_counts else 0

    # Trigram repetition
    trigrams = [f"{words[i]} {words[i+1]} {words[i+2]}" for i in range(len(words) - 2)]
    trigram_counts = Counter(trigrams)
    repeated_trigrams = sum(1 for c in trigram_counts.values() if c > 1)
    trigram_ratio = repeated_trigrams / len(trigram_counts) if trigram_counts else 0

    # Combined ratio
    combined = (bigram_ratio * 0.4 + trigram_ratio * 0.6)

    # Score: higher repetition = more AI-like
    if combined > 0.25:
        score = 60.0
    elif combined > 0.15:
        score = 40.0
    elif combined > 0.08:
        score = 20.0
    else:
        score = 0.0

    patterns = []
    if score > 0:
        patterns.append({
            "pattern": "repetition_density",
            "detail": f"N-gram repetition density {combined:.3f} (bigram {bigram_ratio:.3f}, trigram {trigram_ratio:.3f})"
        })

    return score, patterns


# === Category B: Corpus-Referenced Perplexity ===

def _sentence_perplexity(sentence, corpus):
    """Compute perplexity of a single sentence against corpus trigrams.

    Returns perplexity (float) or None if insufficient data.
    """
    words = _get_words(preprocess_text(sentence))
    if len(words) < 5:
        return None

    trigrams_table = corpus["trigrams"]
    floor_logprob = corpus["floor_logprob"]

    log_probs = []
    unseen_count = 0
    total_count = 0

    for i in range(len(words) - 2):
        tri = f"{words[i]} {words[i+1]} {words[i+2]}"
        total_count += 1
        if tri in trigrams_table:
            log_probs.append(trigrams_table[tri])
        else:
            log_probs.append(floor_logprob)
            unseen_count += 1

    if total_count == 0:
        return None

    # Coverage guard: if >60% unseen, skip
    if unseen_count / total_count > 0.6:
        return None

    # Perplexity = exp(-1/N * sum(log_probs))
    avg_log_prob = sum(log_probs) / len(log_probs)
    perplexity = math.exp(-avg_log_prob)

    return perplexity


def check_ngram_perplexity(text, corpus):
    """B1: Trigram perplexity against reference corpus.

    AI text follows high-frequency paths -> lower perplexity.
    Human text is more surprising -> higher perplexity.
    Min text: 5 words per sentence.
    """
    if corpus is None:
        return 0.0, []

    sentences = _split_sentences(text)
    perplexities = []

    for sent in sentences:
        ppl = _sentence_perplexity(sent, corpus)
        if ppl is not None:
            perplexities.append(ppl)

    if not perplexities:
        return 0.0, []

    avg_perplexity = float(np.mean(perplexities))

    # Score: lower perplexity = more predictable = more AI-like
    # These thresholds are initial estimates — calibration will refine
    if avg_perplexity < 800:
        score = 60.0
    elif avg_perplexity < 1500:
        score = 40.0
    elif avg_perplexity < 2500:
        score = 20.0
    else:
        score = 0.0

    patterns = []
    if score > 0:
        patterns.append({
            "pattern": "ngram_perplexity",
            "detail": f"Average trigram perplexity {avg_perplexity:.0f} — text follows predictable patterns"
        })

    return score, patterns


def check_ngram_burstiness(text, corpus):
    """B2: Coefficient of variation of per-sentence perplexity.

    AI maintains uniform predictability (low CV).
    Human writing is bursty (high CV).
    Min text: 5+ sentences.
    Recomputes perplexity internally (self-contained).
    """
    if corpus is None:
        return 0.0, []

    sentences = _split_sentences(text)
    perplexities = []

    for sent in sentences:
        ppl = _sentence_perplexity(sent, corpus)
        if ppl is not None:
            perplexities.append(ppl)

    if len(perplexities) < 5:
        return 0.0, []

    mean_ppl = float(np.mean(perplexities))
    std_ppl = float(np.std(perplexities))

    if mean_ppl == 0:
        return 0.0, []

    cv = std_ppl / mean_ppl  # Coefficient of variation

    # Score: low CV = uniform = AI-like
    if cv < 0.2:
        score = 60.0
    elif cv < 0.35:
        score = 40.0
    elif cv < 0.5:
        score = 20.0
    else:
        score = 0.0

    patterns = []
    if score > 0:
        patterns.append({
            "pattern": "ngram_burstiness",
            "detail": f"Perplexity CV {cv:.3f} — uniformly predictable across sentences (AI-like)"
        })

    return score, patterns


# === Category C: Rehabilitated Statistical Methods ===

def check_zipf_deviation_v2(text):
    """C1: Zipf's law R-squared goodness-of-fit.

    AI text adheres more closely to ideal Zipf distribution.
    Human text deviates, especially in the tail.
    Min text: 100 words.
    """
    words = _get_words(text)
    if len(words) < 100:
        return 0.0, []

    freq_counts = Counter(words)
    freqs = sorted(freq_counts.values(), reverse=True)
    ranks = list(range(1, len(freqs) + 1))

    if len(freqs) < 10:
        return 0.0, []

    log_ranks = np.log(ranks)
    log_freqs = np.log(freqs)

    slope, intercept, r_value, p_value, std_err = scipy_stats.linregress(log_ranks, log_freqs)
    r_squared = r_value ** 2

    # Residual analysis — AI has smaller residuals in the tail
    predicted = slope * log_ranks + intercept
    residuals = log_freqs - predicted
    tail_start = len(residuals) * 2 // 3
    tail_residual_std = float(np.std(residuals[tail_start:])) if tail_start < len(residuals) else 0

    score = 0.0
    if r_squared > 0.95 and tail_residual_std < 0.25:
        score = 60.0
    elif r_squared > 0.92 and tail_residual_std < 0.35:
        score = 40.0
    elif r_squared > 0.88 and tail_residual_std < 0.45:
        score = 20.0

    patterns = []
    if score > 0:
        patterns.append({
            "pattern": "zipf_deviation_v2",
            "detail": f"Zipf R²={r_squared:.3f}, tail residual std={tail_residual_std:.3f} — word frequencies follow ideal distribution (AI-like)"
        })

    return score, patterns


def check_mattr_v2(text, genre_baselines, genre="general"):
    """C2: Genre-aware Moving Average TTR.

    Compares MATTR against genre-specific baselines instead of universal threshold.
    Min text: 50 words.
    """
    words = _get_words(text)
    if len(words) < 50:
        return 0.0, []

    window_size = 50
    ttrs = []
    for i in range(len(words) - window_size + 1):
        chunk = words[i:i + window_size]
        ttr = len(set(chunk)) / len(chunk)
        ttrs.append(ttr)

    if not ttrs:
        return 0.0, []

    avg_mattr = float(np.mean(ttrs))
    mattr_std = float(np.std(ttrs))

    # Get genre baseline (fall back to general, then hardcoded defaults)
    baseline = genre_baselines.get(genre, genre_baselines.get("general", {
        "mattr_mean": 0.72, "mattr_std": 0.06
    }))

    baseline_mean = baseline.get("mattr_mean", 0.72)
    baseline_std = baseline.get("mattr_std", 0.06)

    # Z-score: how far is this text's MATTR from genre baseline
    if baseline_std > 0:
        z_score = (avg_mattr - baseline_mean) / baseline_std
    else:
        z_score = 0

    abs_z = abs(z_score)

    score = 0.0
    if abs_z < 0.3 and mattr_std < baseline_std * 0.7:
        score = 50.0
    elif abs_z < 0.5 and mattr_std < baseline_std * 0.85:
        score = 30.0
    elif abs_z < 0.8 and mattr_std < baseline_std:
        score = 15.0

    patterns = []
    if score > 0:
        patterns.append({
            "pattern": "mattr_v2",
            "detail": f"MATTR {avg_mattr:.3f} (genre baseline {baseline_mean:.3f}±{baseline_std:.3f}), z={z_score:.2f} — unnaturally close to genre norm"
        })

    return score, patterns


def check_ttr_variance(text):
    """C3: Type-Token Ratio variance across chunks.

    AI maintains consistent vocabulary diversity. Humans drift.
    Min text: 200 words / 2+ chunks.
    """
    words = _get_words(text)
    chunk_size = 100

    if len(words) < chunk_size * 2:
        return 0.0, []

    ttrs = []
    for i in range(0, len(words) - chunk_size + 1, chunk_size):
        chunk = words[i:i + chunk_size]
        ttr = len(set(chunk)) / len(chunk)
        ttrs.append(ttr)

    if len(ttrs) < 2:
        return 0.0, []

    variance = float(np.var(ttrs))
    cv = float(np.std(ttrs) / np.mean(ttrs)) if np.mean(ttrs) > 0 else 0

    if variance < 0.001 and cv < 0.03:
        score = 60.0
    elif variance < 0.002 and cv < 0.05:
        score = 40.0
    elif variance < 0.004 and cv < 0.08:
        score = 20.0
    else:
        score = 0.0

    patterns = []
    if score > 0:
        patterns.append({
            "pattern": "ttr_variance",
            "detail": f"TTR variance {variance:.4f} (CV {cv:.3f}) — vocabulary diversity is unnaturally uniform"
        })

    return score, patterns
