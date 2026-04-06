"""Cross-Model Phrase Fingerprinting — sentence-level heuristic.

Detects model-specific phrases and patterns to identify which AI model
likely generated the text. Provides both an AI signal and model attribution.
"""
import re

SCORE_PER_MATCH = 15

MODEL_SIGNATURES = {
    "claude": {
        "phrases": [
            "it's worth noting",
            "i'd be happy to",
            "i should note",
            "to be straightforward",
            "that said,",
            "i want to be direct",
            "let me be transparent",
            "it bears mentioning",
            "i'd suggest",
            "from my perspective",
        ],
        "patterns": [
            r"both .{3,40} and .{3,40} have (?:merit|value|strengths)",
            r"there are (?:multiple|several|various|different) perspectives",
            r"(?:nuanced|multifaceted) (?:issue|topic|question|situation)",
        ],
    },
    "gpt": {
        "phrases": [
            "certainly!",
            "absolutely!",
            "delve",
            "straightforward",
            "it's important to note",
            "in today's",
            "in conclusion,",
            "overall,",
            "game-changer",
            "navigate the",
            "landscape of",
            "in the realm of",
        ],
        "patterns": [
            r"\*\*\d+\.\s",
            r"(?:Key|Main|Important|Critical) (?:takeaway|point|consideration|factor)s?:",
            r"(?:Let's|Let us) (?:explore|examine|discuss|look at)",
        ],
    },
    "gemini": {
        "phrases": [
            "here's a breakdown",
            "key takeaways:",
            "let's break this down",
            "here are some",
            "it's also worth mentioning",
            "in summary,",
            "to put it simply",
        ],
        "patterns": [
            r"\*\s+\*\*.+\*\*",
            r"(?:First|Second|Third|Finally|Additionally),\s",
        ],
    },
}


def check_model_fingerprint(sentence: str) -> tuple[float, list[dict]]:
    """Check a sentence for model-specific AI phrases.

    Returns (score: 0-N*15, patterns: list[dict]).
    Each pattern dict includes: pattern, detail, model, matched.
    """
    sentence_lower = sentence.lower()
    matches = []

    for model_name, signatures in MODEL_SIGNATURES.items():
        for phrase in signatures["phrases"]:
            if phrase.lower() in sentence_lower:
                matches.append({
                    "pattern": "model_fingerprint",
                    "detail": f"Matches {model_name.upper()} signature phrase: \"{phrase}\"",
                    "model": model_name,
                    "matched": phrase,
                })

        for pattern in signatures["patterns"]:
            if re.search(pattern, sentence, re.IGNORECASE):
                matches.append({
                    "pattern": "model_fingerprint",
                    "detail": f"Matches {model_name.upper()} structural pattern",
                    "model": model_name,
                    "matched": pattern,
                })

    score = len(matches) * SCORE_PER_MATCH
    return score, matches
