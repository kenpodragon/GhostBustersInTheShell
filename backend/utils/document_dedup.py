"""Document deduplication utilities for voice corpus management."""
import hashlib
import re
import unicodedata
from difflib import SequenceMatcher


def normalize_text(text: str) -> str:
    """Normalize text for comparison: strip, lowercase, collapse whitespace, normalize unicode."""
    text = unicodedata.normalize("NFKC", text)
    text = text.strip().lower()
    text = re.sub(r'\s+', ' ', text)
    return text


def compute_content_hash(text: str) -> str:
    """Compute SHA-256 hash of normalized text."""
    normalized = normalize_text(text)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def check_exact_duplicate(content_hash: str, profile_id: int) -> dict | None:
    """Check if a document with this exact hash exists for the given profile.

    Returns the matching document row dict, or None if no match.
    """
    from db import query_one
    return query_one(
        """SELECT id, filename, created_at
           FROM documents
           WHERE content_hash = %s AND voice_profile_id = %s AND purpose = 'voice_corpus'
           LIMIT 1""",
        (content_hash, profile_id),
    )


def check_near_duplicate(text: str, profile_id: int, length_tolerance: float = 0.05, similarity_threshold: float = 0.9) -> dict | None:
    """Check for near-duplicate documents in the corpus.

    Compares text length (within tolerance %) and first 500 normalized chars
    using SequenceMatcher.ratio(). Returns the closest match or None.
    """
    from db import query_all
    normalized = normalize_text(text)
    text_len = len(normalized)
    prefix = normalized[:500]

    min_len = int(text_len * (1 - length_tolerance))
    max_len = int(text_len * (1 + length_tolerance))

    candidates = query_all(
        """SELECT id, filename, original_text, created_at
           FROM documents
           WHERE voice_profile_id = %s AND purpose = 'voice_corpus'
             AND length(original_text) BETWEEN %s AND %s""",
        (profile_id, min_len, max_len),
    )

    for doc in candidates:
        doc_prefix = normalize_text(doc["original_text"])[:500]
        ratio = SequenceMatcher(None, prefix, doc_prefix).ratio()
        if ratio >= similarity_threshold:
            return {"id": doc["id"], "filename": doc["filename"], "created_at": doc["created_at"], "similarity": round(ratio, 3)}

    return None


def count_same_filename(filename: str, profile_id: int) -> int:
    """Count how many corpus documents have the same filename for this profile."""
    from db import query_one
    row = query_one(
        """SELECT COUNT(*) as cnt
           FROM documents
           WHERE filename = %s AND voice_profile_id = %s AND purpose = 'voice_corpus'""",
        (filename, profile_id),
    )
    return row["cnt"] if row else 0
