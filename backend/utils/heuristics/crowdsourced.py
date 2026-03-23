"""Crowdsourced AI tell heuristics.

Pattern-matching heuristics identified from community observations:
articles, Reddit, forums, teacher/editor reports, and AI self-analysis.
See docs/research/crowdsourced_ai_tells.md for sources.
"""
import re
from utils.heuristics.text_utils import tokenize, split_sentences, MIN_WORDS


def check_em_dash_overuse(text: str) -> tuple[float, list[dict]]:
    """Detect em dash overuse — a post-GPT-4 AI writing pattern.

    AI (especially GPT-4+) heavily overuses em dashes (—) for parenthetical
    asides. Humans typically use 0-2 per 1000 words; AI uses 5-15+.
    """
    words = tokenize(text)
    if len(words) < MIN_WORDS:
        return 0, []

    em_dashes = text.count('\u2014') + text.count('--')

    # Need at least 3 em dashes to flag — one or two is normal human usage
    if em_dashes < 3:
        return 0, []

    rate_per_1000 = (em_dashes / len(words)) * 1000

    patterns = []
    score = 0

    if rate_per_1000 > 10:
        score = 40
        patterns.append({
            "pattern": "em_dash_heavy",
            "detail": f"Em dash rate {rate_per_1000:.1f}/1000 words — heavy AI pattern (post-GPT-4)"
        })
    elif rate_per_1000 > 5:
        score = 20
        patterns.append({
            "pattern": "em_dash_elevated",
            "detail": f"Em dash rate {rate_per_1000:.1f}/1000 words — elevated, possibly AI"
        })

    return score, patterns


def check_ai_opening_phrases(text: str) -> tuple[float, list[dict]]:
    """Detect AI-typical opening phrases."""
    sentences = split_sentences(text)
    if len(sentences) < 3:
        return 0, []

    ai_openers = [
        r"^In today'?s\s+(rapidly\s+)?(evolving|changing|digital|modern|fast-paced|competitive)",
        r"^In the (world|realm|age|era|field|domain) of\b",
        r"^When it comes to\b",
        r"^In an (era|age|world) (of|where)\b",
        r"^As we (navigate|explore|delve|embark|look at)\b",
        r"^In the (ever-evolving|ever-changing|fast-paced)\b",
        r"^(The|This) (landscape|realm|domain|world) of\b",
        r"^It'?s no (secret|surprise|coincidence) that\b",
        r"^Have you ever (wondered|thought|considered)\b",
        r"^In (recent years|today's society|the modern world)\b",
    ]

    found_count = 0
    for s in sentences:
        for pattern in ai_openers:
            if re.search(pattern, s.strip(), re.IGNORECASE):
                found_count += 1
                break

    ratio = found_count / len(sentences)
    patterns = []
    score = 0

    if ratio > 0.2:
        score = 45
        patterns.append({
            "pattern": "ai_opening_phrases_heavy",
            "detail": f"{found_count}/{len(sentences)} sentences use AI-typical opening phrases"
        })
    elif found_count >= 2:
        score = 25
        patterns.append({
            "pattern": "ai_opening_phrases",
            "detail": f"{found_count} AI-typical opening phrases detected"
        })
    elif found_count == 1:
        score = 10
        patterns.append({
            "pattern": "ai_opening_phrase",
            "detail": "AI-typical opening phrase detected"
        })

    return score, patterns


def check_closing_summary(text: str) -> tuple[float, list[dict]]:
    """Detect AI-typical closing/summary patterns."""
    sentences = split_sentences(text)
    if len(sentences) < 3:
        return 0, []

    last_sentences = ' '.join(sentences[-2:]).lower()

    closing_patterns = [
        r"in conclusion", r"to summarize", r"in summary",
        r"overall,?\s+(by|through|with)",
        r"by (leveraging|embracing|adopting|implementing|utilizing)",
        r"(position|prepare) (themselves|yourself|ourselves) for",
        r"long-term (success|growth|sustainability)",
        r"(paramount|essential|crucial|vital) to (achieving|ensuring|driving)",
        r"the (key|path|road|journey) to (success|growth)",
        r"moving forward", r"at the end of the day", r"all things considered",
    ]

    found = [p for p in closing_patterns if re.search(p, last_sentences)]
    patterns = []
    score = 0

    if len(found) >= 2:
        score = 40
        patterns.append({
            "pattern": "closing_summary_heavy",
            "detail": "Multiple AI-typical closing phrases in final sentences"
        })
    elif len(found) == 1:
        score = 20
        patterns.append({
            "pattern": "closing_summary",
            "detail": "AI-typical closing/summary phrase detected"
        })

    return score, patterns


def check_question_exclamation_absence(text: str) -> tuple[float, list[dict]]:
    """Detect absence of questions and exclamations."""
    sentences = split_sentences(text)
    if len(sentences) < 8:
        return 0, []

    questions = sum(1 for s in sentences if s.strip().endswith('?'))
    exclamations = sum(1 for s in sentences if s.strip().endswith('!'))
    total = len(sentences)
    varied_ratio = (questions + exclamations) / total

    patterns = []
    score = 0

    if varied_ratio == 0 and total >= 8:
        score = 25
        patterns.append({
            "pattern": "no_questions_exclamations",
            "detail": f"All {total} sentences are declarative — no questions or exclamations (AI pattern)"
        })
    elif varied_ratio < 0.05 and total >= 10:
        score = 10
        patterns.append({
            "pattern": "rare_questions_exclamations",
            "detail": f"Only {questions + exclamations}/{total} sentences use ? or !"
        })

    return score, patterns


def check_oxford_comma_consistency(text: str) -> tuple[float, list[dict]]:
    """Detect unnaturally consistent Oxford comma usage."""
    with_oxford = len(re.findall(r',\s+\w+,\s+and\s+', text, re.IGNORECASE))
    without_oxford = len(re.findall(r',\s+\w+\s+and\s+', text, re.IGNORECASE))

    total_lists = with_oxford + without_oxford
    if total_lists < 3:
        return 0, []

    patterns = []
    score = 0

    if with_oxford == total_lists or without_oxford == total_lists:
        score = 15
        style = "always uses" if with_oxford == total_lists else "never uses"
        patterns.append({
            "pattern": "oxford_comma_perfect_consistency",
            "detail": f"{style} Oxford comma across {total_lists} lists — unnaturally consistent"
        })

    return score, patterns


def check_bullet_subheading_overuse(text: str) -> tuple[float, list[dict]]:
    """Detect overuse of bullet points and subheadings."""
    lines = text.split('\n')
    total_lines = len([l for l in lines if l.strip()])
    if total_lines < 5:
        return 0, []

    bullet_lines = sum(1 for l in lines if re.match(r'\s*[-*\u2022]\s+', l.strip()))
    numbered_lines = sum(1 for l in lines if re.match(r'\s*\d+[.)]\s+', l.strip()))
    subheadings = sum(1 for l in lines if re.match(r'^#{1,4}\s+', l.strip()))

    structured = bullet_lines + numbered_lines + subheadings
    structured_ratio = structured / total_lines

    patterns = []
    score = 0

    if structured_ratio > 0.4:
        score = 35
        patterns.append({
            "pattern": "heavy_structure",
            "detail": f"{structured_ratio:.0%} of lines are bullets/numbered/subheadings — AI formatting pattern"
        })
    elif structured_ratio > 0.2:
        score = 15
        patterns.append({
            "pattern": "moderate_structure",
            "detail": f"{structured_ratio:.0%} of lines use structured formatting"
        })

    return score, patterns


def check_digression_absence(text: str) -> tuple[float, list[dict]]:
    """Detect absence of digressions and tangents."""
    words = tokenize(text)
    if len(words) < MIN_WORDS:
        return 0, []

    text_lower = text.lower()

    digression_markers = [
        r'\bby the way\b', r'\bspeaking of\b', r'\breminds me\b',
        r'\bside note\b', r'\bon a tangent\b', r'\banyway\b',
        r'\bactually,?\s', r'\boh,?\s', r'\bwell,?\s',
        r'\bbtw\b', r'\bfwiw\b', r'\bi mean\b', r'\byou know\b',
        r'\bfunny (thing|story|enough)\b', r'\brandom(ly)?\b',
        r'\b(which|that) reminds me\b', r'\bnow that i think\b',
        r'\bcome to think of it\b',
    ]

    parens = len(re.findall(r'\([^)]{10,}\)', text))
    marker_count = sum(1 for m in digression_markers if re.search(m, text_lower))
    total_markers = marker_count + parens
    markers_per_100_words = (total_markers / len(words)) * 100

    patterns = []
    score = 0

    if total_markers == 0 and len(words) > 100:
        score = 20
        patterns.append({
            "pattern": "no_digressions",
            "detail": "Zero digression markers in 100+ words — unnaturally focused (AI pattern)"
        })
    elif markers_per_100_words < 0.2 and len(words) > 150:
        score = 10
        patterns.append({
            "pattern": "few_digressions",
            "detail": "Very few tangents or asides — text is unusually on-topic"
        })

    return score, patterns


def check_consensus_middle(text: str) -> tuple[float, list[dict]]:
    """Detect 'consensus middle' tone — AI avoids strong positions."""
    words = tokenize(text)
    if len(words) < MIN_WORDS:
        return 0, []

    text_lower = text.lower()

    balance_patterns = [
        r'while .{5,50}, it\'?s (also|equally|important)',
        r'on (the )?one hand.{5,100}on the other',
        r'it\'?s (important|worth|essential) to (note|consider|acknowledge)',
        r'(that said|having said that|with that said)',
        r'(however|nevertheless),?\s+(it\'?s|we|the)',
    ]

    strong_opinion_markers = [
        r'\b(honestly|frankly|obviously|clearly)\b',
        r'\bi (think|believe|feel|hate|love)\b',
        r'\b(terrible|amazing|awful|brilliant|stupid|ridiculous)\b',
        r'\b(no way|absolutely not|definitely|hell no|damn)\b',
        r'\bshould (never|always)\b',
    ]

    balance_count = sum(1 for p in balance_patterns if re.search(p, text_lower))
    opinion_count = sum(1 for p in strong_opinion_markers if re.search(p, text_lower))

    patterns = []
    score = 0

    if balance_count >= 3 and opinion_count == 0:
        score = 35
        patterns.append({
            "pattern": "consensus_middle_strong",
            "detail": f"{balance_count} hedging constructions, zero strong opinions — AI consensus-seeking"
        })
    elif balance_count >= 2 and opinion_count == 0:
        score = 20
        patterns.append({
            "pattern": "consensus_middle",
            "detail": "Multiple hedging constructions without any strong personal opinions"
        })
    elif balance_count >= 1 and opinion_count == 0 and len(words) > 150:
        score = 10
        patterns.append({
            "pattern": "consensus_middle_mild",
            "detail": "Hedging present without counterbalancing personal opinions"
        })

    return score, patterns
