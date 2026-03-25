"""AI Phrase detection — multi-word collocations that appear mid-sentence.

Copyleaks-style phrase matching for AI-characteristic multi-word phrases.
Unlike buzzwords (single words) or ai_opening_phrases (sentence starters),
these catch connective-tissue phrases anywhere in the text.

Sources:
- docs/research/crowdsourced_ai_tells.md
- docs/research/claude_self_analysis_ai_tells.md
- docs/research/gemini_self_analysis_ai_tells.md
- local_data/investigations/ (Copyleaks AI Phrases feature)
"""
import re
from utils.heuristics.text_utils import tokenize, split_sentences, MIN_WORDS
from utils.heuristics.severity import classify_severity, apply_severity


# --- AI Phrase Dictionary ---
# Multi-word phrases grouped by category.
# Each phrase is matched case-insensitively anywhere in text.
# Order: longest phrases first within each category to avoid partial matches.

VAGUE_ABSTRACTIONS = [
    "the intricacies of",
    "the complexities of",
    "the nuances of",
    "the fabric of",
    "the landscape of",
    "the realm of",
    "the tapestry of",
    "the intersection of",
    "the forefront of",
    "the cornerstone of",
    "the bedrock of",
    "the linchpin of",
    "the hallmark of",
    "the crux of",
    "the heart of the matter",
    "a wide range of",
    "a myriad of",
    "a plethora of",
    "a wealth of",
    "a diverse range of",
    "a broad spectrum of",
    "a multitude of",
    "a variety of factors",
    "an array of",
    "an integral part of",
]

FALSE_DEPTH = [
    "it's worth noting that",
    "it is worth noting that",
    "it's important to note that",
    "it is important to note that",
    "it's important to understand that",
    "it is important to understand that",
    "it's essential to consider",
    "it is essential to consider",
    "it's crucial to understand",
    "it is crucial to understand",
    "this raises important questions about",
    "this raises interesting questions about",
    "the implications are far-reaching",
    "the implications of this",
    "given the fact that",
    "due to the fact that",
    "in light of the fact that",
    "based on the information provided",
    "there's no one-size-fits-all",
    "there is no one-size-fits-all",
    "the answer is nuanced",
    "both sides have valid points",
    "reasonable people can disagree",
    "this is particularly true",
    "this is especially true",
]

METAPHOR_CLICHES = [
    "serves as a testament to",
    "a testament to the",
    "a testament to",
    "stands as a beacon of",
    "serves as a reminder",
    "serves as a catalyst",
    "serves as a foundation",
    "a double-edged sword",
    "the tip of the iceberg",
    "paves the way for",
    "paving the way for",
    "bridges the gap between",
    "bridging the gap between",
    "strikes a balance between",
    "striking a balance between",
    "sheds light on",
    "shedding light on",
    "plays a crucial role",
    "plays a vital role",
    "plays a pivotal role",
    "plays an important role",
    "a key role in",
    "a driving force behind",
    "at the forefront of",
    "at the heart of",
    "on the cutting edge of",
    "a game changer for",
    "a stepping stone",
    "a stark reminder",
]

CORPORATE_ACTION = [
    "unlock the potential of",
    "unlock the power of",
    "unlock the secrets of",
    "unleash the power of",
    "harness the power of",
    "embark on a journey",
    "embarking on a journey",
    "push the boundaries of",
    "pushing the boundaries of",
    "capitalize on the opportunities",
    "navigate the complexities",
    "navigating the complexities",
    "navigate the challenges",
    "lay the groundwork for",
    "laying the groundwork for",
    "foster a culture of",
    "fostering a culture of",
    "drive meaningful change",
    "driving meaningful change",
    "delve into the world of",
    "delve into the intricacies",
    "spearhead the initiative",
    "take it to the next level",
    "a gateway to",
    "the key to success",
]

HEDGING_FILLERS = [
    "one could argue that",
    "one might argue that",
    "it could be argued that",
    "it depends on various factors",
    "while there's no definitive answer",
    "while there is no definitive answer",
    "it goes without saying",
    "it is important to understand",
    "bearing in mind that",
    "with that in mind",
    "in light of this",
    "in light of these",
    "it's a complex issue",
    "it is a complex issue",
    "can potentially",
    "might arguably",
    "to some extent",
    "in many ways",
    "at the end of the day",
    "when all is said and done",
    "all things considered",
    "to put it simply",
    "simply put",
    "in other words",
    "that being said",
    "having said that",
    "with that said",
]

# Phase 3.12: False-insider phrases — fake relatability/empathy
FALSE_INSIDER = [
    "if you're like most",
    "if you are like most",
    "we've all been there",
    "we have all been there",
    "let's be honest",
    "let us be honest",
    "let's face it",
    "let us face it",
    "here's the thing",
    "here is the thing",
    "no one talks about this",
    "nobody talks about this",
    "you're not alone",
    "you are not alone",
    "whether you're a",
    "whether you are a",
    "here's what nobody tells you",
    "here is what nobody tells you",
    "i get it",
    "i understand your frustration",
    "i hear you",
    "that's a great question",
    "that is a great question",
    "we all know",
    "as we all understand",
    "i hope this email finds you well",
    "i wanted to reach out",
]

# Flatten all categories into a single list with metadata
AI_PHRASES = []
_CATEGORIES = {
    "vague_abstraction": VAGUE_ABSTRACTIONS,
    "false_depth": FALSE_DEPTH,
    "metaphor_cliche": METAPHOR_CLICHES,
    "corporate_action": CORPORATE_ACTION,
    "hedging_filler": HEDGING_FILLERS,
    "false_insider": FALSE_INSIDER,
}

for category, phrases in _CATEGORIES.items():
    for phrase in phrases:
        AI_PHRASES.append((phrase, category))

# Sort longest first to match greedily
AI_PHRASES.sort(key=lambda x: len(x[0]), reverse=True)

# Pre-compile regex patterns for each phrase (word-boundary aware)
_COMPILED_PATTERNS = []
for phrase, category in AI_PHRASES:
    # Escape regex special chars, then compile with word boundaries
    escaped = re.escape(phrase)
    # Allow flexible apostrophe matching (curly and straight)
    escaped = escaped.replace(r"\'", r"['\u2019]")
    pattern = re.compile(r'\b' + escaped + r'\b', re.IGNORECASE)
    _COMPILED_PATTERNS.append((pattern, phrase, category))


def check_ai_phrases(text: str) -> tuple[float, list[dict]]:
    """Detect AI-characteristic multi-word phrases anywhere in text.

    Returns (score, patterns) where score is 0-90 based on phrase count
    and patterns lists each matched phrase with its category.
    """
    words = tokenize(text)
    if len(words) < MIN_WORDS:
        return 0, []

    matches = []
    # Track matched spans to avoid double-counting overlapping phrases
    matched_positions = set()

    for pattern, phrase, category in _COMPILED_PATTERNS:
        for m in pattern.finditer(text):
            start, end = m.start(), m.end()
            # Skip if this span overlaps with an already-matched longer phrase
            span = range(start, end)
            if any(pos in matched_positions for pos in span):
                continue
            matched_positions.update(span)
            matches.append({
                "phrase": phrase,
                "category": category,
                "position": start,
            })

    if not matches:
        return 0, []

    count = len(matches)
    # Normalize by text length — more phrases per 100 words = higher score
    density = (count / len(words)) * 100  # phrases per 100 words

    # Scoring: count-based with density consideration
    # 1 phrase = mild signal, 3+ = strong signal, 5+ = very strong
    severity = classify_severity(count)
    base_score = min(90, count * 20)

    # Density bonus: high concentration amplifies score
    if density > 2.0:
        base_score = min(90, base_score + 15)
    elif density > 1.0:
        base_score = min(90, base_score + 8)

    score = apply_severity(base_score, severity) if severity else 0

    # Build pattern list with category info
    patterns = []
    # Group by category for cleaner output
    by_category = {}
    for m in matches:
        cat = m["category"]
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(m["phrase"])

    for cat, phrases in by_category.items():
        cat_label = cat.replace("_", " ")
        if len(phrases) == 1:
            patterns.append({
                "pattern": "ai_phrase",
                "detail": f"AI phrase ({cat_label}): \"{phrases[0]}\""
            })
        else:
            joined = '", "'.join(phrases)
            patterns.append({
                "pattern": "ai_phrase",
                "detail": f"AI phrases ({cat_label}): \"{joined}\""
            })

    return round(score, 1), patterns


def check_ai_phrases_sentence(sentence: str) -> tuple[float, list[dict]]:
    """Sentence-level AI phrase check — no minimum word count."""
    matches = []
    matched_positions = set()

    for pattern, phrase, category in _COMPILED_PATTERNS:
        for m in pattern.finditer(sentence):
            start, end = m.start(), m.end()
            span = range(start, end)
            if any(pos in matched_positions for pos in span):
                continue
            matched_positions.update(span)
            matches.append({
                "phrase": phrase,
                "category": category,
            })

    if not matches:
        return 0, []

    count = len(matches)
    severity = classify_severity(count)
    base_score = min(90, count * 25)
    score = apply_severity(base_score, severity) if severity else 0

    patterns = [{
        "pattern": "ai_phrase",
        "detail": f"AI phrase: \"{m['phrase']}\""
    } for m in matches]

    return round(score, 1), patterns
