"""Shared text processing utilities for heuristic modules."""
import re


def tokenize(text: str) -> list[str]:
    """Extract lowercase word tokens, stripping punctuation."""
    return re.findall(r"[a-z']+", text.lower())


def split_sentences(text: str) -> list[str]:
    """Split text into sentences."""
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    return [s.strip() for s in sentences if len(s.strip()) > 5]


# Minimum word count for reliable heuristic analysis
MIN_WORDS = 50
# Minimum character count for compression-based analysis
MIN_CHARS = 200
