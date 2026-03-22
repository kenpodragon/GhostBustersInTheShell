"""Python-based AI text detection heuristics (no AI provider needed).

Implements multiple detection signals:
- Perplexity estimation (vocabulary predictability)
- Burstiness analysis (sentence length variance)
- Stylometric patterns (word choice, structure)
- Voice guide violations (banned words/constructions)
"""
import re
import math
from collections import Counter


def detect_ai_patterns(text: str) -> dict:
    """Run all heuristic detectors on text. Returns sentence-level scores."""
    sentences = _split_sentences(text)
    if not sentences:
        return {"overall_score": 0, "sentences": [], "detected_patterns": []}

    sentence_results = []
    all_patterns = []

    for i, sentence in enumerate(sentences):
        score, patterns = _score_sentence(sentence, sentences)
        sentence_results.append({
            "index": i,
            "text": sentence,
            "score": score,
            "patterns": patterns,
        })
        all_patterns.extend(patterns)

    # Aggregate overall score (weighted average favoring high-scoring sentences)
    scores = [s["score"] for s in sentence_results]
    overall = _weighted_overall(scores)

    # Document-level patterns
    doc_patterns = _document_level_patterns(text, sentences)
    all_patterns.extend(doc_patterns)

    # Deduplicate pattern names
    unique_patterns = []
    seen = set()
    for p in all_patterns:
        if p["pattern"] not in seen:
            unique_patterns.append(p)
            seen.add(p["pattern"])

    return {
        "overall_score": round(overall, 1),
        "sentences": sentence_results,
        "detected_patterns": unique_patterns,
    }


def _split_sentences(text: str) -> list:
    """Split text into sentences."""
    # Simple sentence splitter - handles common cases
    parts = re.split(r'(?<=[.!?])\s+', text.strip())
    return [p.strip() for p in parts if p.strip()]


def _score_sentence(sentence: str, all_sentences: list) -> tuple:
    """Score a single sentence for AI likelihood. Returns (score, patterns)."""
    scores = []
    patterns = []

    # 1. Vocabulary predictability (banned buzzwords)
    buzz_score, buzz_patterns = _check_buzzwords(sentence)
    scores.append(buzz_score)
    patterns.extend(buzz_patterns)

    # 2. Sentence length relative to document
    length_score = _check_length_uniformity(sentence, all_sentences)
    if length_score > 30:
        scores.append(length_score)
        patterns.append({"pattern": "uniform_length", "detail": "Sentence length is very uniform across document"})

    # 3. Hedge word density
    hedge_score, hedge_patterns = _check_hedge_words(sentence)
    scores.append(hedge_score)
    patterns.extend(hedge_patterns)

    # 4. Transition word overuse
    trans_score, trans_patterns = _check_transitions(sentence)
    scores.append(trans_score)
    patterns.extend(trans_patterns)

    # 5. Structural patterns
    struct_score, struct_patterns = _check_structural_patterns(sentence)
    scores.append(struct_score)
    patterns.extend(struct_patterns)

    # Combine scores (max 100)
    combined = min(100, sum(scores) / max(len(scores), 1) * 1.5)
    return round(combined, 1), patterns


def _check_buzzwords(sentence: str) -> tuple:
    """Check for AI-typical buzzwords."""
    buzzwords = {
        "leverage", "utilize", "spearhead", "synergize", "operationalize",
        "revolutionize", "supercharge", "harness", "empower", "elevate",
        "amplify", "streamline", "champion", "evangelize", "pioneer",
        "robust", "holistic", "innovative", "cutting-edge", "game-changing",
        "best-in-class", "world-class", "state-of-the-art", "mission-critical",
        "enterprise-grade", "dynamic", "furthermore", "moreover", "additionally",
        "consequently", "nevertheless", "comprehensive", "facilitate", "paradigm",
    }
    words = set(re.findall(r'\b\w+\b', sentence.lower()))
    found = words & buzzwords
    score = min(80, len(found) * 25)
    patterns = [{"pattern": "buzzword", "detail": f"AI-typical word: '{w}'"} for w in found]
    return score, patterns


def _check_hedge_words(sentence: str) -> tuple:
    """Check for AI hedging patterns."""
    hedges = [
        r'\bhowever\b', r'\bfurthermore\b', r'\bmoreover\b', r'\badditionally\b',
        r'\bconsequently\b', r'\bnevertheless\b', r'\bnotably\b', r'\bimportantly\b',
        r'\bsignificantly\b', r'\bundoubtedly\b', r'\bultimately\b',
    ]
    found = [h for h in hedges if re.search(h, sentence, re.IGNORECASE)]
    score = min(60, len(found) * 20)
    patterns = [{"pattern": "hedge_word", "detail": f"AI-typical hedge: {h}"} for h in found]
    return score, patterns


def _check_transitions(sentence: str) -> tuple:
    """Check for AI-typical transition patterns."""
    transitions = [
        r'^(In conclusion|To summarize|In summary|Overall|In essence)',
        r'^(It is worth noting|It should be noted|It is important to)',
        r'^(This (demonstrates|illustrates|highlights|underscores|showcases))',
        r'^(By (leveraging|utilizing|harnessing|implementing))',
    ]
    found = [t for t in transitions if re.search(t, sentence, re.IGNORECASE)]
    score = min(70, len(found) * 35)
    patterns = [{"pattern": "ai_transition", "detail": "AI-typical opening pattern"} for _ in found]
    return score, patterns


def _check_structural_patterns(sentence: str) -> tuple:
    """Check for structural AI tells."""
    patterns_found = []
    score = 0

    # "Not only X but also Y" pattern
    if re.search(r'not only .+ but also', sentence, re.IGNORECASE):
        patterns_found.append({"pattern": "not_only_but_also", "detail": "AI-typical parallel construction"})
        score += 25

    # "It is [adjective] to [verb]" pattern
    if re.search(r'it is \w+ to \w+', sentence, re.IGNORECASE):
        patterns_found.append({"pattern": "it_is_adj_to", "detail": "AI-typical impersonal construction"})
        score += 15

    # List of three with "and" (rule of three)
    if re.search(r'\w+, \w+, and \w+', sentence):
        patterns_found.append({"pattern": "rule_of_three", "detail": "AI favors triadic lists"})
        score += 10

    return score, patterns_found


def _check_length_uniformity(sentence: str, all_sentences: list) -> float:
    """Score based on how uniform sentence lengths are."""
    if len(all_sentences) < 3:
        return 0
    lengths = [len(s.split()) for s in all_sentences]
    mean_len = sum(lengths) / len(lengths)
    variance = sum((l - mean_len) ** 2 for l in lengths) / len(lengths)
    std_dev = math.sqrt(variance) if variance > 0 else 0

    # Low std_dev = uniform = AI-like
    cv = std_dev / mean_len if mean_len > 0 else 0
    if cv < 0.2:
        return 50  # Very uniform
    elif cv < 0.3:
        return 25  # Somewhat uniform
    return 0


def _document_level_patterns(text: str, sentences: list) -> list:
    """Check for document-level AI patterns."""
    patterns = []

    # Check paragraph length uniformity
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    if len(paragraphs) > 2:
        para_lengths = [len(p.split()) for p in paragraphs]
        mean_len = sum(para_lengths) / len(para_lengths)
        variance = sum((l - mean_len) ** 2 for l in para_lengths) / len(para_lengths)
        cv = math.sqrt(variance) / mean_len if mean_len > 0 else 0
        if cv < 0.25:
            patterns.append({
                "pattern": "uniform_paragraphs",
                "detail": "Paragraph lengths are suspiciously uniform"
            })

    # Check vocabulary richness (type-token ratio)
    words = re.findall(r'\b\w+\b', text.lower())
    if len(words) > 50:
        ttr = len(set(words)) / len(words)
        if ttr < 0.4:
            patterns.append({
                "pattern": "low_vocabulary_richness",
                "detail": f"Type-token ratio {ttr:.2f} suggests repetitive vocabulary"
            })

    return patterns


def _weighted_overall(scores: list) -> float:
    """Calculate weighted overall score, favoring high-scoring sentences."""
    if not scores:
        return 0
    # Weight high scores more heavily
    weighted = sum(s * (1 + s / 100) for s in scores)
    total_weight = sum(1 + s / 100 for s in scores)
    return weighted / total_weight if total_weight > 0 else 0
