"""Generate voice profiles from sample content."""
import re
import json
from collections import Counter


def generate_voice_profile(content: str) -> str:
    """Analyze writing samples and generate a voice profile JSON.

    Minimum 500 words required. 2000+ words recommended for accuracy.
    Extracts: vocabulary patterns, sentence structure, punctuation habits,
    tone markers, and common constructions.
    """
    words = content.split()
    word_count = len(words)

    profile = {
        "word_count_analyzed": word_count,
        "vocabulary": _analyze_vocabulary(content),
        "sentence_structure": _analyze_sentences(content),
        "punctuation": _analyze_punctuation(content),
        "tone": _analyze_tone(content),
        "constructions": _extract_constructions(content),
        "banned_words": [],  # User can customize
        "preferred_words": [],  # User can customize
    }

    return json.dumps(profile, indent=2)


def _analyze_vocabulary(text: str) -> dict:
    """Analyze vocabulary patterns."""
    words = re.findall(r'\b[a-zA-Z]+\b', text.lower())
    word_freq = Counter(words)

    # Filter stop words
    stop_words = {"the", "a", "an", "is", "are", "was", "were", "in", "on", "at",
                  "to", "for", "of", "and", "or", "but", "not", "with", "this",
                  "that", "it", "i", "you", "we", "they", "he", "she", "my",
                  "your", "his", "her", "our", "their", "be", "have", "has",
                  "had", "do", "does", "did", "will", "would", "could", "should",
                  "can", "may", "might", "shall", "from", "by", "as", "if", "so"}
    content_words = {w: c for w, c in word_freq.items() if w not in stop_words and len(w) > 2}

    total = len(words)
    unique = len(set(words))

    return {
        "total_words": total,
        "unique_words": unique,
        "type_token_ratio": round(unique / total, 3) if total > 0 else 0,
        "top_content_words": dict(Counter(content_words).most_common(20)),
        "avg_word_length": round(sum(len(w) for w in words) / total, 1) if total else 0,
    }


def _analyze_sentences(text: str) -> dict:
    """Analyze sentence structure patterns."""
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    lengths = [len(s.split()) for s in sentences if s]

    if not lengths:
        return {}

    import statistics
    return {
        "count": len(lengths),
        "avg_length": round(statistics.mean(lengths), 1),
        "std_dev": round(statistics.stdev(lengths), 1) if len(lengths) > 1 else 0,
        "min_length": min(lengths),
        "max_length": max(lengths),
        "short_sentence_ratio": round(sum(1 for l in lengths if l < 8) / len(lengths), 2),
        "long_sentence_ratio": round(sum(1 for l in lengths if l > 25) / len(lengths), 2),
    }


def _analyze_punctuation(text: str) -> dict:
    """Analyze punctuation habits."""
    return {
        "uses_ellipsis": text.count("...") > 0,
        "ellipsis_count": text.count("..."),
        "uses_em_dash": text.count("--") > 0 or text.count("\u2014") > 0,
        "em_dash_count": text.count("--") + text.count("\u2014"),
        "uses_semicolons": text.count(";") > 0,
        "semicolon_count": text.count(";"),
        "exclamation_count": text.count("!"),
        "question_count": text.count("?"),
        "parenthetical_count": text.count("("),
    }


def _analyze_tone(text: str) -> dict:
    """Analyze tone markers."""
    text_lower = text.lower()
    return {
        "formality": _estimate_formality(text_lower),
        "uses_contractions": bool(re.search(r"\b\w+n't\b|\b\w+'re\b|\b\w+'ll\b|\b\w+'ve\b", text)),
        "uses_first_person": bool(re.search(r'\b(I|my|me|mine)\b', text)),
        "uses_second_person": bool(re.search(r'\b(you|your|yours)\b', text_lower)),
        "question_frequency": text.count("?") / max(len(re.split(r'(?<=[.!?])\s+', text)), 1),
    }


def _estimate_formality(text: str) -> str:
    """Estimate writing formality level."""
    formal_markers = ["therefore", "furthermore", "moreover", "consequently",
                      "nevertheless", "notwithstanding", "henceforth"]
    informal_markers = ["gonna", "wanna", "kinda", "sorta", "yeah", "nah",
                        "ok", "okay", "hey", "lol", "btw"]

    formal_count = sum(1 for m in formal_markers if m in text)
    informal_count = sum(1 for m in informal_markers if m in text)

    if formal_count > informal_count + 2:
        return "formal"
    elif informal_count > formal_count + 2:
        return "informal"
    return "moderate"


def _extract_constructions(text: str) -> list:
    """Extract recurring sentence constructions/patterns."""
    constructions = []
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())

    # Check for common opening patterns
    openings = Counter()
    for s in sentences:
        words = s.split()[:3]
        if len(words) >= 2:
            openings[" ".join(words[:2]).lower()] += 1

    for opening, count in openings.most_common(5):
        if count >= 2:
            constructions.append({
                "pattern": f"Opens with '{opening}'",
                "frequency": count,
            })

    return constructions
