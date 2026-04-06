"""EditLens-Style Soft N-gram Overlap Scoring.

Measures literal text reuse between original and rewrite using
overlapping n-gram precision with fuzzy matching.
"""
import re
from rapidfuzz import fuzz


def _tokenize(text: str) -> list[str]:
    return re.findall(r'\b\w+\b', text.lower())


def _extract_ngrams(tokens: list[str], min_n: int = 2, max_n: int = 6) -> list[tuple[str, ...]]:
    ngrams = []
    for n in range(min_n, max_n + 1):
        for i in range(len(tokens) - n + 1):
            ngrams.append(tuple(tokens[i:i + n]))
    return ngrams


def _ngram_to_str(ngram: tuple[str, ...]) -> str:
    return ' '.join(ngram)


def _token_overlap(orig_tokens: list[str], rewrite_tokens: list[str]) -> float:
    """Compute fraction of rewrite tokens that fuzzy-match any original token (>=70 ratio)."""
    if not orig_tokens or not rewrite_tokens:
        return 0.0
    matched = 0
    for rw_tok in rewrite_tokens:
        for orig_tok in orig_tokens:
            if fuzz.ratio(rw_tok, orig_tok) >= 70:
                matched += 1
                break
    return matched / len(rewrite_tokens)


def compute_ngram_overlap(original: str, rewrite: str) -> tuple[float, str, str]:
    """Compute soft n-gram overlap between original and rewrite.

    Blends n-gram precision (structural reuse) with token-level fuzzy
    matching (synonym/near-synonym reuse) to catch both literal copies
    and lightly paraphrased text.

    Returns (overlap: 0.0-1.0, label: str, warning: str).
    """
    orig_tokens = _tokenize(original)
    rewrite_tokens = _tokenize(rewrite)

    if not orig_tokens or not rewrite_tokens:
        return 0.0, "low", ""

    orig_ngrams = _extract_ngrams(orig_tokens)
    rewrite_ngrams = _extract_ngrams(rewrite_tokens)

    # N-gram precision score
    if rewrite_ngrams:
        matched = 0
        orig_set = set(orig_ngrams)
        orig_strings = [_ngram_to_str(ng) for ng in orig_ngrams]
        for rw_ngram in rewrite_ngrams:
            rw_str = _ngram_to_str(rw_ngram)
            if rw_ngram in orig_set:
                matched += 1
                continue
            for orig_str in orig_strings:
                if fuzz.ratio(rw_str, orig_str) > 80:
                    matched += 1
                    break
        ngram_score = matched / len(rewrite_ngrams)
    else:
        ngram_score = 0.0

    # Token-level fuzzy overlap score (catches synonym swaps)
    tok_score = _token_overlap(orig_tokens, rewrite_tokens)

    # Blend: token score weighted more heavily to catch synonym-level rewrites
    overlap = 0.3 * ngram_score + 0.7 * tok_score

    if overlap > 0.7:
        label = "high"
        warning = "Surface-level rewrite, original structure preserved"
    elif overlap > 0.4:
        label = "moderate"
        warning = "Partial restructuring"
    else:
        label = "low"
        warning = "Substantial restructuring"

    return round(overlap, 4), label, warning
