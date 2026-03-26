"""Python-based heuristic text rewriter (fallback when AI unavailable)."""
import re
import random


def heuristic_rewrite(text: str, voice_profile_id: int = None, voice_elements: list = None) -> dict:
    """Rewrite text using rule-based transformations.

    This is the fallback when no AI provider is available.
    Applies basic transformations to reduce AI detection signals.

    voice_elements: resolved element dicts from VoiceProfileService stack.
        Accepted for future use — not yet applied in heuristic logic.
    """
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    changes = []
    rewritten = []

    for sentence in sentences:
        new_sentence, applied = _apply_transforms(sentence)
        rewritten.append(new_sentence)
        if applied:
            changes.append({
                "original": sentence,
                "rewritten": new_sentence,
                "reason": ", ".join(applied),
            })

    return {
        "rewritten_text": " ".join(rewritten),
        "changes": changes,
        "method": "heuristic_fallback",
        "note": "Basic rule-based rewriting. Connect an AI provider for better results.",
    }


def _apply_transforms(sentence: str) -> tuple:
    """Apply rule-based transformations to a sentence."""
    applied = []
    result = sentence

    # Replace common AI buzzwords
    replacements = {
        r'\butilize\b': 'use',
        r'\bleverage\b': 'use',
        r'\bfacilitate\b': 'help',
        r'\bimplement\b': 'build',
        r'\brobust\b': 'strong',
        r'\bcomprehensive\b': 'full',
        r'\bfurthermore\b': 'also',
        r'\bmoreover\b': 'also',
        r'\badditionally\b': 'also',
        r'\bconsequently\b': 'so',
        r'\bnevertheless\b': 'still',
        r'\benhance\b': 'improve',
        r'\boptimize\b': 'improve',
        r'\bstreamline\b': 'simplify',
        r'\binnovative\b': 'new',
        r'\bholistic\b': 'complete',
    }
    for pattern, replacement in replacements.items():
        if re.search(pattern, result, re.IGNORECASE):
            result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
            applied.append(f"replaced buzzword with '{replacement}'")

    # Remove weak openings
    weak_openings = [
        r'^It is (worth noting|important to note|essential to understand) that ',
        r'^(In conclusion|To summarize|In summary|Overall), ',
        r'^This (demonstrates|illustrates|highlights|underscores|showcases) ',
    ]
    for pattern in weak_openings:
        if re.search(pattern, result, re.IGNORECASE):
            result = re.sub(pattern, '', result, flags=re.IGNORECASE)
            applied.append("removed weak opening")

    return result, applied
