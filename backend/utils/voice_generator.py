"""Generate voice profiles from sample content.

Outputs profile_elements format: dict[str, dict] where each key is an element
name and each value contains category, element_type, weight, tags, and
optionally direction and target_value.
"""
import re
import math
import statistics
from collections import Counter


def generate_voice_profile(text: str) -> dict:
    """Analyze writing sample and return profile_elements dict.

    Minimum 500 words required. 2000+ words recommended for accuracy.
    Returns a dict where keys are element names and values are element dicts
    with: category, element_type, weight, tags, and optionally direction/target_value.
    """
    words = re.findall(r"\b[a-zA-Z']+\b", text)
    word_count = len(words)

    if word_count < 500:
        raise ValueError(f"Text must be at least 500 words for analysis (got {word_count}). "
                         "Provide a longer sample.")

    alpha_words = re.findall(r"\b[a-zA-Z]+\b", text)
    sentences = _split_sentences(text)
    n_sentences = max(len(sentences), 1)

    profile = {}

    # --- Lexical ---
    _add_lexical(profile, alpha_words)

    # --- Syntactic ---
    _add_syntactic(profile, text, sentences, alpha_words)

    # --- Idiosyncratic ---
    _add_idiosyncratic(profile, text, sentences, alpha_words, n_sentences)

    # --- Readability ---
    _add_readability(profile, text, alpha_words, sentences)

    return profile


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _split_sentences(text: str) -> list:
    """Split text into sentences on .!? boundaries."""
    parts = re.split(r'(?<=[.!?])\s+', text.strip())
    return [s for s in parts if s.strip()]


def _count_syllables(word: str) -> int:
    """Estimate syllable count via vowel-group heuristic."""
    word = word.lower().strip("'")
    if not word:
        return 1
    vowels = "aeiouy"
    count = len(re.findall(r'[aeiouy]+', word))
    # Subtract silent-e at end
    if word.endswith('e') and len(word) > 2 and word[-2] not in vowels:
        count -= 1
    return max(1, count)


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))


def _directional_element(category: str, direction: str, weight: float,
                          tags: list) -> dict:
    return {
        "category": category,
        "element_type": "directional",
        "direction": direction,
        "weight": round(_clamp(weight), 4),
        "tags": tags,
    }


def _metric_element(category: str, target_value: float, tags: list,
                    weight: float = 0.0) -> dict:
    return {
        "category": category,
        "element_type": "metric",
        "weight": round(_clamp(weight), 4),
        "target_value": round(target_value, 4),
        "tags": tags,
    }


# ---------------------------------------------------------------------------
# Lexical
# ---------------------------------------------------------------------------

def _add_lexical(profile: dict, alpha_words: list) -> None:
    total = len(alpha_words)
    unique = len(set(w.lower() for w in alpha_words))
    ttr = unique / total if total else 0.0

    # vocabulary_richness — directional, weight = normalized TTR (expected max ~0.8)
    profile["vocabulary_richness"] = _directional_element(
        "lexical",
        "more" if ttr >= 0.4 else "less",
        ttr / 0.8,
        ["python-extractable"],
    )

    # avg_word_length — metric
    avg_len = sum(len(w) for w in alpha_words) / total if total else 0.0
    profile["avg_word_length"] = _metric_element(
        "lexical", avg_len, ["python-extractable"], weight=_clamp(avg_len / 10.0)
    )

    # contraction_rate
    contractions = re.findall(
        r"\b\w+(?:n't|'re|'ll|'ve|'d|'m|'s)\b", " ".join(alpha_words), re.IGNORECASE
    )
    rate = len(contractions) / total if total else 0.0
    profile["contraction_rate"] = _directional_element(
        "lexical",
        "more" if rate > 0.02 else "less",
        min(1.0, rate / 0.1),
        ["python-extractable"],
    )

    # long_word_frequency — ratio of words > 6 chars
    long_ratio = sum(1 for w in alpha_words if len(w) > 6) / total if total else 0.0
    profile["long_word_frequency"] = _directional_element(
        "lexical",
        "more" if long_ratio >= 0.2 else "less",
        long_ratio,
        ["python-extractable"],
    )

    # archaic_vocabulary_rate — frequency of Early Modern English words
    _ARCHAIC_WORDS = {
        "thee", "thou", "thy", "thine", "hath", "doth", "dost", "hast",
        "wherefore", "hence", "thence", "whence", "ere", "oft", "tis",
        "twas", "nay", "aye", "forsooth", "prithee", "methinks",
        "perchance", "mayhap", "verily", "betwixt", "amongst", "hither",
        "thither", "whither",
    }
    archaic_count = sum(1 for w in alpha_words if w.lower() in _ARCHAIC_WORDS)
    archaic_rate = archaic_count / total if total else 0.0
    profile["archaic_vocabulary_rate"] = _directional_element(
        "lexical",
        "more" if archaic_rate > 0 else "less",
        min(1.0, archaic_rate / 0.05),
        ["python-extractable"],
    )

    # rare_word_rate — ratio of long words appearing only once
    word_counts = Counter(w.lower() for w in alpha_words)
    rare_count = sum(1 for w, c in word_counts.items() if len(w) > 8 and c == 1)
    rare_rate = rare_count / total if total else 0.0
    profile["rare_word_rate"] = _directional_element(
        "lexical",
        "more" if rare_rate >= 0.05 else "less",
        rare_rate / 0.3,
        ["python-extractable"],
    )


# ---------------------------------------------------------------------------
# Syntactic
# ---------------------------------------------------------------------------

def _add_syntactic(profile: dict, text: str, sentences: list,
                   alpha_words: list) -> None:
    lengths = [len(re.findall(r"\b[a-zA-Z']+\b", s)) for s in sentences]
    n = len(lengths) if lengths else 1

    avg_len = statistics.mean(lengths) if lengths else 0.0
    stddev = statistics.stdev(lengths) if len(lengths) > 1 else 0.0

    profile["avg_sentence_length"] = _metric_element(
        "syntactic", avg_len, ["python-extractable"],
        weight=_clamp(avg_len / 40.0)
    )

    profile["sentence_length_stddev"] = _metric_element(
        "syntactic", stddev, ["python-extractable"],
        weight=_clamp(stddev / 20.0)
    )

    short_ratio = sum(1 for l in lengths if l < 10) / n
    profile["short_sentence_ratio"] = _directional_element(
        "syntactic",
        "more" if short_ratio >= 0.3 else "less",
        short_ratio,
        ["python-extractable"],
    )

    long_ratio = sum(1 for l in lengths if l > 25) / n
    profile["long_sentence_ratio"] = _directional_element(
        "syntactic",
        "more" if long_ratio >= 0.2 else "less",
        long_ratio,
        ["python-extractable"],
    )

    # Passive voice: "was/were/been/being + past participle (word ending in -ed or irregular)"
    passive_pattern = re.compile(
        r'\b(was|were|been|being|is|are)\s+\w+ed\b', re.IGNORECASE
    )
    passive_count = len(passive_pattern.findall(text))
    passive_rate = passive_count / n
    profile["passive_voice_rate"] = _directional_element(
        "syntactic",
        "less",
        min(1.0, passive_rate / 0.3),
        ["python-extractable"],
    )

    # inverted_syntax_rate — sentences starting with verb or adverb before subject
    _INVERSION_VERBS = {
        "is", "are", "was", "were", "do", "did", "shall", "will", "would",
        "could", "should", "may", "might", "have", "has", "had", "let",
        "come", "go", "speak", "think", "know", "see", "hear", "give",
        "take", "make",
    }
    _INVERSION_ADVERBS = {
        "never", "yet", "thus", "hence", "now", "then", "here", "there",
        "so", "well", "oft",
    }
    _INVERSION_STARTERS = _INVERSION_VERBS | _INVERSION_ADVERBS
    inv_count = 0
    for s in sentences:
        first_word = re.match(r'\b([a-zA-Z]+)\b', s.strip())
        if first_word and first_word.group(1).lower() in _INVERSION_STARTERS:
            inv_count += 1
    inv_rate = inv_count / n
    profile["inverted_syntax_rate"] = _directional_element(
        "syntactic",
        "more" if inv_rate >= 0.05 else "less",
        min(1.0, inv_rate / 0.2),
        ["python-extractable"],
    )


# ---------------------------------------------------------------------------
# Idiosyncratic
# ---------------------------------------------------------------------------

def _add_idiosyncratic(profile: dict, text: str, sentences: list,
                       alpha_words: list, n_sentences: int) -> None:
    total_words = len(alpha_words)

    # em_dash_usage
    em_count = text.count("\u2014") + text.count("--")
    profile["em_dash_usage"] = _directional_element(
        "idiosyncratic",
        "more" if em_count > 0 else "less",
        min(1.0, (em_count / n_sentences) / 0.3),
        ["python-extractable", "punctuation"],
    )

    # semicolon_usage
    semi_count = text.count(";")
    profile["semicolon_usage"] = _directional_element(
        "idiosyncratic",
        "more" if semi_count > 0 else "less",
        min(1.0, (semi_count / n_sentences) / 0.3),
        ["python-extractable", "punctuation"],
    )

    # ellipsis_usage
    ellipsis_count = text.count("...")
    profile["ellipsis_usage"] = _directional_element(
        "idiosyncratic",
        "more" if ellipsis_count > 0 else "less",
        min(1.0, (ellipsis_count / n_sentences) / 0.3),
        ["python-extractable", "punctuation"],
    )

    # exclamation_rate
    excl_sentences = sum(1 for s in sentences if s.rstrip().endswith("!"))
    excl_rate = excl_sentences / n_sentences
    profile["exclamation_rate"] = _directional_element(
        "idiosyncratic",
        "more" if excl_rate >= 0.05 else "less",
        excl_rate,
        ["python-extractable", "punctuation"],
    )

    # parenthetical_usage
    paren_count = text.count("(")
    profile["parenthetical_usage"] = _directional_element(
        "idiosyncratic",
        "more" if paren_count > 0 else "less",
        min(1.0, (paren_count / n_sentences) / 0.3),
        ["python-extractable", "punctuation"],
    )

    # rhetorical_question_rate
    q_sentences = sum(1 for s in sentences if s.rstrip().endswith("?"))
    q_rate = q_sentences / n_sentences
    profile["rhetorical_question_rate"] = _directional_element(
        "idiosyncratic",
        "more" if q_rate >= 0.05 else "less",
        q_rate,
        ["python-extractable"],
    )

    # first_person_usage
    first_person = re.findall(r'\b(I|me|my|mine|myself|we|us|our|ours|ourselves)\b',
                              text, re.IGNORECASE)
    fp_rate = len(first_person) / total_words if total_words else 0.0
    profile["first_person_usage"] = _directional_element(
        "idiosyncratic",
        "more" if fp_rate >= 0.03 else "less",
        min(1.0, fp_rate / 0.1),
        ["python-extractable"],
    )

    # second_person_usage
    second_person = re.findall(r'\b(you|your|yours|yourself|yourselves)\b',
                               text, re.IGNORECASE)
    sp_rate = len(second_person) / total_words if total_words else 0.0
    profile["second_person_usage"] = _directional_element(
        "idiosyncratic",
        "more" if sp_rate >= 0.02 else "less",
        min(1.0, sp_rate / 0.1),
        ["python-extractable"],
    )

    # figurative_language_markers — simile/metaphor indicators per sentence
    fig_patterns = re.findall(
        r"\blike a\b|\bas a\b|\bas if\b|\bas though\b|'tis\b|\bseems\b|\bappears\b",
        text, re.IGNORECASE,
    )
    fig_rate = len(fig_patterns) / n_sentences
    profile["figurative_language_markers"] = _directional_element(
        "idiosyncratic",
        "more" if fig_rate >= 0.05 else "less",
        min(1.0, fig_rate / 0.15),
        ["python-extractable"],
    )

    # repetition_rate — repeated 2-word phrases appearing 3+ times
    lower_words = [w.lower() for w in alpha_words]
    bigrams = [f"{lower_words[i]} {lower_words[i+1]}" for i in range(len(lower_words) - 1)]
    bigram_counts = Counter(bigrams)
    repeated_bigrams = sum(1 for _, c in bigram_counts.items() if c >= 3)
    total_bigrams = max(len(bigrams), 1)
    rep_rate = repeated_bigrams / total_bigrams
    profile["repetition_rate"] = _directional_element(
        "idiosyncratic",
        "more" if rep_rate > 0 else "less",
        min(1.0, rep_rate / 0.02),
        ["python-extractable"],
    )

    # vocative_usage — direct address patterns per sentence
    vocative_patterns = re.findall(
        r'\bO \b|\bOh \b|\bHark\b|\bLo \b|\bAlas\b|\bCome,|\bGood \b|\bMy lord\b|\bMy lady\b|\bDear \b',
        text, re.IGNORECASE,
    )
    voc_rate = len(vocative_patterns) / n_sentences
    profile["vocative_usage"] = _directional_element(
        "idiosyncratic",
        "more" if voc_rate > 0 else "less",
        min(1.0, voc_rate / 0.1),
        ["python-extractable"],
    )


# ---------------------------------------------------------------------------
# Readability
# ---------------------------------------------------------------------------

def _add_readability(profile: dict, text: str, alpha_words: list,
                     sentences: list) -> None:
    words = alpha_words
    n_words = len(words)
    n_sentences = max(len(sentences), 1)
    n_chars = sum(len(w) for w in words)
    n_syllables = sum(_count_syllables(w) for w in words)
    complex_words = sum(1 for w in words if _count_syllables(w) >= 3)

    wps = n_words / n_sentences          # words per sentence
    spw = n_syllables / n_words if n_words else 0  # syllables per word
    cpw = n_chars / n_words if n_words else 0       # chars per word

    # Flesch-Kincaid Grade
    fk_grade = 0.39 * wps + 11.8 * spw - 15.59
    profile["flesch_kincaid_grade"] = _metric_element(
        "idiosyncratic", fk_grade,
        ["python-extractable", "readability"],
        weight=_clamp(fk_grade / 20.0),
    )

    # Flesch Reading Ease
    fre = 206.835 - 1.015 * wps - 84.6 * spw
    profile["flesch_reading_ease"] = _metric_element(
        "idiosyncratic", fre,
        ["python-extractable", "readability"],
        weight=_clamp(fre / 100.0),
    )

    # Gunning Fog
    fog = 0.4 * (wps + 100.0 * complex_words / n_words) if n_words else 0.0
    profile["gunning_fog_index"] = _metric_element(
        "idiosyncratic", fog,
        ["python-extractable", "readability"],
        weight=_clamp(fog / 20.0),
    )

    # Coleman-Liau
    L = (n_chars / n_words * 100) if n_words else 0   # avg chars per 100 words
    S = (n_sentences / n_words * 100) if n_words else 0  # avg sentences per 100 words
    cli = 0.0588 * L - 0.296 * S - 15.8
    profile["coleman_liau_index"] = _metric_element(
        "idiosyncratic", cli,
        ["python-extractable", "readability"],
        weight=_clamp(cli / 20.0),
    )

    # SMOG
    smog = 1.0430 * math.sqrt(complex_words * (30.0 / n_sentences)) + 3.1291
    profile["smog_index"] = _metric_element(
        "idiosyncratic", smog,
        ["python-extractable", "readability"],
        weight=_clamp(smog / 20.0),
    )

    # Automated Readability Index
    ari = 4.71 * cpw + 0.5 * wps - 21.43
    profile["automated_readability_index"] = _metric_element(
        "idiosyncratic", ari,
        ["python-extractable", "readability"],
        weight=_clamp(ari / 20.0),
    )
