"""Semantic Embedding Monotony — document-level heuristic.

AI text has more uniform sentence embeddings than human text.
Uses neural embeddings (MiniLM sidecar) with TF-IDF fallback.
"""
import math
import re
from collections import Counter

from utils.embedding_client import get_embedding_client

MIN_SENTENCES = 4
THRESHOLD = 0.75          # neural embedding threshold
THRESHOLD_TFIDF = 0.12    # TF-IDF fallback threshold (IDF penalizes shared terms, so values are lower)
MAX_SCORE = 40


def _split_into_sentences(text: str) -> list[str]:
    """Simple sentence splitter for this heuristic."""
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    return [s.strip() for s in sentences if len(s.strip()) > 5]


def _cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _mean_pairwise_similarity(vectors: list[list[float]]) -> float:
    """Compute mean pairwise cosine similarity across all vector pairs."""
    n = len(vectors)
    if n < 2:
        return 0.0
    total = 0.0
    count = 0
    for i in range(n):
        for j in range(i + 1, n):
            total += _cosine_similarity(vectors[i], vectors[j])
            count += 1
    return total / count if count > 0 else 0.0


def _tfidf_vectors(sentences: list[str]) -> list[list[float]]:
    """Build TF-IDF vectors for sentences (pure Python fallback)."""
    tokenized = []
    vocab = set()
    for s in sentences:
        words = re.findall(r'\b\w+\b', s.lower())
        tokenized.append(words)
        vocab.update(words)

    vocab = sorted(vocab)
    word_to_idx = {w: i for i, w in enumerate(vocab)}
    n_docs = len(sentences)

    df = Counter()
    for words in tokenized:
        for w in set(words):
            df[w] += 1

    vectors = []
    for words in tokenized:
        tf = Counter(words)
        vec = [0.0] * len(vocab)
        for word, count in tf.items():
            idx = word_to_idx[word]
            idf = math.log((n_docs + 1) / (df[word] + 1)) + 1
            vec[idx] = count * idf
        vectors.append(vec)

    return vectors


def check_semantic_monotony(text: str) -> tuple[float, list[dict]]:
    """Check for semantic embedding monotony across sentences.

    Returns (score: 0-40, patterns: list[dict]).
    """
    sentences = _split_into_sentences(text)
    if len(sentences) < MIN_SENTENCES:
        return 0, []

    client = get_embedding_client()
    vectors = None
    used_neural = False
    if client.is_available():
        vectors = client.embed(sentences)
        used_neural = True

    if vectors is None:
        vectors = _tfidf_vectors(sentences)

    mean_sim = _mean_pairwise_similarity(vectors)
    threshold = THRESHOLD if used_neural else THRESHOLD_TFIDF

    if mean_sim < threshold:
        return 0, []

    score_ratio = (mean_sim - threshold) / (1.0 - threshold)
    score = min(MAX_SCORE, round(score_ratio * MAX_SCORE))

    if score <= 0:
        return 0, []

    return score, [{
        "pattern": "semantic_monotony",
        "detail": f"Mean pairwise semantic similarity {mean_sim:.3f} exceeds threshold {THRESHOLD} — sentences are unusually uniform in meaning"
    }]
