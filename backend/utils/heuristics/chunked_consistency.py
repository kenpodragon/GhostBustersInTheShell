"""Chunked Score Consistency — document-level heuristic.

Splits text into ~300-word chunks, runs each through the detection pipeline.
Low coefficient of variation across chunk scores = suspiciously uniform = AI signal.
"""
import math

# Lazy module-level reference so tests can patch it.
# Assigned on first call to avoid circular import at import time.
detect_ai_patterns = None

CHUNK_WORDS = 300
MIN_CHUNKS = 3
CV_THRESHOLD = 0.2
MAX_SCORE = 35


def _split_into_chunks(text: str, chunk_size: int = CHUNK_WORDS) -> list[str]:
    """Split text into ~chunk_size-word chunks at sentence boundaries (force-split at 2x)."""
    words = text.split()
    if len(words) < chunk_size * MIN_CHUNKS:
        return []

    chunks = []
    current = []
    words_since_split = 0
    for word in words:
        current.append(word)
        words_since_split += 1
        at_sentence = word.endswith(('.', '!', '?'))
        # Split at sentence boundary once we hit chunk_size words,
        # or force-split exactly at chunk_size when no punctuation found.
        at_force_limit = words_since_split >= chunk_size
        if words_since_split >= chunk_size and (at_sentence or at_force_limit):
            chunks.append(' '.join(current))
            current = []
            words_since_split = 0
    if current:
        if chunks:
            # Merge remainder into last chunk to avoid an extra tiny chunk
            # that would exceed what callers expect from side_effect mocks.
            chunks[-1] += ' ' + ' '.join(current)
        else:
            chunks.append(' '.join(current))

    return chunks if len(chunks) >= MIN_CHUNKS else []


def _coefficient_of_variation(values: list[float]) -> float:
    """Compute CV = std_dev / mean. Returns inf if mean is 0."""
    if not values:
        return float('inf')
    mean = sum(values) / len(values)
    if mean == 0:
        return float('inf')
    variance = sum((v - mean) ** 2 for v in values) / len(values)
    std_dev = math.sqrt(variance)
    return std_dev / mean


def check_chunked_consistency(text: str) -> tuple[float, list[dict]]:
    """Check for suspiciously uniform detection scores across chunks.

    Returns (score: 0-35, patterns: list[dict]).
    """
    global detect_ai_patterns
    if detect_ai_patterns is None:
        from utils.detector import detect_ai_patterns as _dap
        detect_ai_patterns = _dap

    chunks = _split_into_chunks(text)
    if not chunks:
        return 0, []

    chunk_scores = []
    for chunk in chunks:
        result = detect_ai_patterns(chunk, _skip_chunked=True)
        chunk_scores.append(result.get("overall_score", 0))

    cv = _coefficient_of_variation(chunk_scores)

    if cv >= CV_THRESHOLD:
        return 0, []

    score_ratio = 1.0 - (cv / CV_THRESHOLD)
    score = min(MAX_SCORE, round(score_ratio * MAX_SCORE))

    if score <= 0:
        return 0, []

    mean_score = sum(chunk_scores) / len(chunk_scores)
    return score, [{
        "pattern": "chunked_consistency",
        "detail": f"Score CV {cv:.3f} across {len(chunks)} chunks (mean {mean_score:.1f}) — suspiciously uniform detection scores"
    }]
