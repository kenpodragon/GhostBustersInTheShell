"""Generate voice profiles from sample content.

Outputs profile_elements format: dict[str, dict] where each key is an element
name and each value contains category, element_type, weight, tags, and
optionally direction and target_value.

60 elements across 6 categories (51 regex + 6 spaCy + 3 VADER sentiment):
- Lexical (12 + 1 spaCy): vocabulary, word choice, function words, NER
- Syntactic (10 + 5 spaCy): sentence structure, clause patterns, POS ratios
- Structural (3): paragraph organization, quotation density
- Idiosyncratic (13): punctuation, pronoun, figurative patterns
- Voice/Tone (3 + 3 VADER): hedging, intensifiers, transitions, sentiment
- Readability (6+4 metric): grade levels, reading ease, readability indices

Tier 2 elements require spaCy + en_core_web_sm. If unavailable, gracefully
falls back to 54 elements (51 regex + 3 VADER sentiment).
Tier 3 elements require nltk + vader_lexicon. If unavailable, gracefully
falls back to 57 elements (51 regex + 6 spaCy) or 51 regex-only.
"""
import re
import math
import statistics
from collections import Counter

# ---------------------------------------------------------------------------
# spaCy lazy loading — Tier 2 elements require spaCy + en_core_web_sm
# ---------------------------------------------------------------------------

_nlp = None
_spacy_available = None


def _get_spacy_nlp():
    """Lazy-load spaCy model. Returns None if spaCy isn't installed."""
    global _nlp, _spacy_available
    if _spacy_available is None:
        try:
            import spacy
            _nlp = spacy.load("en_core_web_sm")
            _spacy_available = True
        except (ImportError, OSError):
            _spacy_available = False
    return _nlp


# ---------------------------------------------------------------------------
# Tier 3 lazy loaders
# ---------------------------------------------------------------------------

_vader_analyzer = None
_vader_available = None


def _get_vader():
    """Lazy-load VADER sentiment analyzer. Returns None if unavailable."""
    global _vader_analyzer, _vader_available
    if _vader_available is None:
        try:
            from nltk.sentiment.vader import SentimentIntensityAnalyzer
            _vader_analyzer = SentimentIntensityAnalyzer()
            _vader_available = True
        except (ImportError, LookupError):
            _vader_available = False
    return _vader_analyzer


_tfidf_available = None


def _check_tfidf():
    """Check if scikit-learn TF-IDF is available."""
    global _tfidf_available
    if _tfidf_available is None:
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer  # noqa: F401
            from sklearn.metrics.pairwise import cosine_similarity  # noqa: F401
            _tfidf_available = True
        except ImportError:
            _tfidf_available = False
    return _tfidf_available


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
    paragraphs = _split_paragraphs(text)
    n_sentences = max(len(sentences), 1)

    profile = {}

    # --- Lexical ---
    _add_lexical(profile, alpha_words)

    # --- Syntactic ---
    _add_syntactic(profile, text, sentences, alpha_words)

    # --- Structural ---
    _add_structural(profile, text, sentences, paragraphs, n_sentences)

    # --- Idiosyncratic ---
    _add_idiosyncratic(profile, text, sentences, alpha_words, n_sentences)

    # --- Voice / Tone ---
    _add_voice_tone(profile, alpha_words, n_sentences)

    # --- Readability ---
    _add_readability(profile, text, alpha_words, sentences)

    # --- Tier 2: spaCy-based (optional) ---
    _add_spacy_elements(profile, text)

    # --- Tier 3: Sentiment, Topic Coherence, Discourse (optional) ---
    _add_tier3_elements(profile, text, sentences, paragraphs)

    return profile


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _split_sentences(text: str) -> list:
    """Split text into sentences on .!? boundaries."""
    parts = re.split(r'(?<=[.!?])\s+', text.strip())
    return [s for s in parts if s.strip()]


def _split_paragraphs(text: str) -> list:
    """Split text into paragraphs on double-newline boundaries."""
    parts = re.split(r'\n\s*\n', text.strip())
    return [p.strip() for p in parts if p.strip()]


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

    # --- New lexical elements (Phase 4.5.3.2) ---

    lower_words = [w.lower() for w in alpha_words]

    # function_word_rate — top function words as % of total
    _FUNCTION_WORDS = {
        "the", "of", "and", "to", "a", "in", "is", "it", "that", "for",
        "was", "on", "with", "as", "at", "by", "from", "or", "but", "not",
        "be", "this", "which", "an", "are", "were", "been", "have", "has",
        "had", "do", "did", "will", "would", "could", "should", "may",
        "might", "can", "shall", "must", "if", "so", "than", "no", "when",
        "what", "who", "how", "all", "each", "every", "both", "few",
        "more", "most", "other", "some", "such", "any", "only", "same",
    }
    fw_count = sum(1 for w in lower_words if w in _FUNCTION_WORDS)
    fw_rate = fw_count / total if total else 0.0
    profile["function_word_rate"] = _metric_element(
        "lexical", fw_rate, ["python-extractable"],
        weight=_clamp(fw_rate / 0.6),
    )

    # article_rate — a/an/the as % of total
    article_count = sum(1 for w in lower_words if w in {"a", "an", "the"})
    art_rate = article_count / total if total else 0.0
    profile["article_rate"] = _metric_element(
        "lexical", art_rate, ["python-extractable"],
        weight=_clamp(art_rate / 0.1),
    )

    # preposition_rate — common prepositions as % of total
    _PREPOSITIONS = {
        "of", "in", "to", "for", "with", "on", "at", "by", "from",
        "about", "into", "through", "during", "before", "after",
        "above", "below", "between", "under", "over", "against",
        "among", "without", "within", "along", "across", "behind",
        "beyond", "toward", "towards", "upon", "around", "near",
    }
    prep_count = sum(1 for w in lower_words if w in _PREPOSITIONS)
    prep_rate = prep_count / total if total else 0.0
    profile["preposition_rate"] = _metric_element(
        "lexical", prep_rate, ["python-extractable"],
        weight=_clamp(prep_rate / 0.15),
    )

    # lexical_density — content words / total words (lower = more functional/grammatical)
    # Content words ≈ total - function words
    content_rate = 1.0 - fw_rate
    profile["lexical_density"] = _metric_element(
        "lexical", content_rate, ["python-extractable"],
        weight=_clamp(content_rate),
    )

    # hapax_legomena_ratio — words appearing exactly once / total unique words
    unique_count = len(word_counts)
    hapax_count = sum(1 for _, c in word_counts.items() if c == 1)
    hapax_ratio = hapax_count / unique_count if unique_count else 0.0
    profile["hapax_legomena_ratio"] = _metric_element(
        "lexical", hapax_ratio, ["python-extractable"],
        weight=_clamp(hapax_ratio),
    )

    # nominalization_rate — words ending in -tion/-sion/-ment/-ness/-ity/-ence/-ance
    _NOM_SUFFIXES = re.compile(r'(tion|sion|ment|ness|ity|ence|ance)$', re.IGNORECASE)
    nom_count = sum(1 for w in lower_words if len(w) > 4 and _NOM_SUFFIXES.search(w))
    nom_rate = nom_count / total if total else 0.0
    profile["nominalization_rate"] = _directional_element(
        "lexical",
        "more" if nom_rate >= 0.03 else "less",
        min(1.0, nom_rate / 0.08),
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

    # --- New syntactic elements (Phase 4.5.3.2) ---

    # conjunction_opening_rate — sentences starting with And/But/Or/So/Yet/Because
    _CONJ_OPENERS = {"and", "but", "or", "so", "yet", "because", "nor"}
    conj_open = 0
    for s in sentences:
        first_word = re.match(r'\b([a-zA-Z]+)\b', s.strip())
        if first_word and first_word.group(1).lower() in _CONJ_OPENERS:
            conj_open += 1
    conj_open_rate = conj_open / n
    profile["conjunction_opening_rate"] = _directional_element(
        "syntactic",
        "more" if conj_open_rate >= 0.05 else "less",
        min(1.0, conj_open_rate / 0.2),
        ["python-extractable"],
    )

    # sentence_opener_variety — Shannon entropy of first words (higher = more diverse)
    first_words = []
    for s in sentences:
        m = re.match(r'\b([a-zA-Z]+)\b', s.strip())
        if m:
            first_words.append(m.group(1).lower())
    if first_words:
        fw_counts = Counter(first_words)
        fw_total = len(first_words)
        entropy = -sum((c / fw_total) * math.log2(c / fw_total)
                       for c in fw_counts.values() if c > 0)
        max_entropy = math.log2(fw_total) if fw_total > 1 else 1.0
        norm_entropy = entropy / max_entropy if max_entropy > 0 else 0.0
    else:
        norm_entropy = 0.0
    profile["sentence_opener_variety"] = _metric_element(
        "syntactic", norm_entropy, ["python-extractable"],
        weight=_clamp(norm_entropy),
    )

    # coordinating_conjunction_rate — and/but/or/nor/for/yet/so per word
    _COORD_CONJ = {"and", "but", "or", "nor", "for", "yet", "so"}
    total_words = len(alpha_words)
    coord_count = sum(1 for w in [x.lower() for x in alpha_words] if w in _COORD_CONJ)
    coord_rate = coord_count / total_words if total_words else 0.0
    profile["coordinating_conjunction_rate"] = _metric_element(
        "syntactic", coord_rate, ["python-extractable"],
        weight=_clamp(coord_rate / 0.08),
    )

    # subordinating_conjunction_rate — because/although/while/since/if/unless/when/where/that/which
    _SUBORD_CONJ = {
        "because", "although", "though", "while", "since", "if", "unless",
        "when", "where", "whereas", "whenever", "wherever", "until",
        "after", "before", "once", "provided", "supposing",
    }
    subord_count = sum(1 for w in [x.lower() for x in alpha_words] if w in _SUBORD_CONJ)
    subord_rate = subord_count / total_words if total_words else 0.0
    profile["subordinating_conjunction_rate"] = _metric_element(
        "syntactic", subord_rate, ["python-extractable"],
        weight=_clamp(subord_rate / 0.05),
    )

    # avg_clause_complexity — commas + subordinating conjunctions per sentence (proxy)
    comma_count = text.count(",")
    clause_proxy = (comma_count + subord_count) / n
    profile["avg_clause_complexity"] = _metric_element(
        "syntactic", clause_proxy, ["python-extractable"],
        weight=_clamp(clause_proxy / 5.0),
    )


# ---------------------------------------------------------------------------
# Structural
# ---------------------------------------------------------------------------

def _add_structural(profile: dict, text: str, sentences: list,
                    paragraphs: list, n_sentences: int) -> None:
    """Paragraph-level and structural organization elements."""
    n_paras = max(len(paragraphs), 1)

    # paragraph_avg_length — average sentences per paragraph
    para_sent_counts = []
    for p in paragraphs:
        p_sents = _split_sentences(p)
        para_sent_counts.append(len(p_sents))
    avg_para_len = statistics.mean(para_sent_counts) if para_sent_counts else 1.0
    profile["paragraph_avg_length"] = _metric_element(
        "structural", avg_para_len, ["python-extractable"],
        weight=_clamp(avg_para_len / 10.0),
    )

    # single_sentence_paragraph_ratio — one-sentence paragraphs as %
    single_sent = sum(1 for c in para_sent_counts if c == 1)
    single_ratio = single_sent / n_paras
    profile["single_sentence_paragraph_ratio"] = _directional_element(
        "structural",
        "more" if single_ratio >= 0.2 else "less",
        single_ratio,
        ["python-extractable"],
    )

    # quotation_density — quoted material as approximate % of text
    # Count characters inside quotation marks
    quoted_chars = sum(len(m) for m in re.findall(
        r'["\u201c][^"\u201d]*["\u201d]', text
    ))
    total_chars = max(len(text), 1)
    quote_ratio = quoted_chars / total_chars
    profile["quotation_density"] = _directional_element(
        "structural",
        "more" if quote_ratio >= 0.05 else "less",
        min(1.0, quote_ratio / 0.3),
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

    # --- New idiosyncratic elements (Phase 4.5.3.2) ---

    # third_person_usage — he/she/they/them/his/her/their rate
    third_person = re.findall(
        r'\b(he|she|they|them|his|her|hers|their|theirs|him|himself|herself|themselves)\b',
        text, re.IGNORECASE,
    )
    tp_rate = len(third_person) / total_words if total_words else 0.0
    profile["third_person_usage"] = _directional_element(
        "idiosyncratic",
        "more" if tp_rate >= 0.02 else "less",
        min(1.0, tp_rate / 0.08),
        ["python-extractable"],
    )

    # modal_verb_rate — can/could/would/should/may/might/must/shall
    _MODALS = {"can", "could", "would", "should", "may", "might", "must", "shall"}
    modal_count = sum(1 for w in [x.lower() for x in alpha_words] if w in _MODALS)
    modal_rate = modal_count / total_words if total_words else 0.0
    profile["modal_verb_rate"] = _directional_element(
        "idiosyncratic",
        "more" if modal_rate >= 0.015 else "less",
        min(1.0, modal_rate / 0.04),
        ["python-extractable"],
    )

    # comma_rate — commas per sentence (major punctuation style indicator)
    comma_count = text.count(",")
    comma_per_sent = comma_count / n_sentences
    profile["comma_rate"] = _metric_element(
        "idiosyncratic", comma_per_sent,
        ["python-extractable", "punctuation"],
        weight=_clamp(comma_per_sent / 4.0),
    )

    # colon_usage — colons per sentence
    colon_count = text.count(":")
    colon_per_sent = colon_count / n_sentences
    profile["colon_usage"] = _directional_element(
        "idiosyncratic",
        "more" if colon_count > 0 else "less",
        min(1.0, colon_per_sent / 0.2),
        ["python-extractable", "punctuation"],
    )

    # discourse_marker_rate — informal connectors per word
    _DISCOURSE_MARKERS = {
        "well", "basically", "essentially", "actually", "literally",
        "honestly", "obviously", "clearly", "frankly", "naturally",
        "anyway", "anyhow", "indeed", "certainly", "definitely",
        "surely", "simply", "merely",
    }
    dm_count = sum(1 for w in [x.lower() for x in alpha_words] if w in _DISCOURSE_MARKERS)
    dm_rate = dm_count / total_words if total_words else 0.0
    profile["discourse_marker_rate"] = _directional_element(
        "idiosyncratic",
        "more" if dm_rate >= 0.005 else "less",
        min(1.0, dm_rate / 0.02),
        ["python-extractable"],
    )


# ---------------------------------------------------------------------------
# Voice / Tone
# ---------------------------------------------------------------------------

def _add_voice_tone(profile: dict, alpha_words: list,
                    n_sentences: int) -> None:
    """Hedging, intensifiers, and transition patterns that define authorial tone."""
    total_words = len(alpha_words)
    lower_words = [w.lower() for w in alpha_words]

    # hedging_language_rate — tentative/uncertain language per word
    _HEDGES = {
        "maybe", "perhaps", "might", "somewhat", "arguably", "possibly",
        "apparently", "relatively", "fairly", "likely", "unlikely",
        "probably", "presumably", "conceivably", "roughly", "approximately",
        "seemingly", "supposedly", "tends", "suggest", "suggests",
        "indicate", "indicates", "appear", "appears", "seem", "seems",
    }
    hedge_count = sum(1 for w in lower_words if w in _HEDGES)
    hedge_rate = hedge_count / total_words if total_words else 0.0
    profile["hedging_language_rate"] = _directional_element(
        "voice_tone",
        "more" if hedge_rate >= 0.005 else "less",
        min(1.0, hedge_rate / 0.02),
        ["python-extractable"],
    )

    # intensifier_rate — emphatic/amplifying words per word
    _INTENSIFIERS = {
        "very", "really", "extremely", "absolutely", "totally", "incredibly",
        "quite", "rather", "highly", "particularly", "especially",
        "remarkably", "utterly", "thoroughly", "deeply", "profoundly",
        "enormously", "vastly", "significantly", "considerably",
        "exceedingly", "terribly", "awfully", "entirely", "completely",
    }
    intens_count = sum(1 for w in lower_words if w in _INTENSIFIERS)
    intens_rate = intens_count / total_words if total_words else 0.0
    profile["intensifier_rate"] = _directional_element(
        "voice_tone",
        "more" if intens_rate >= 0.005 else "less",
        min(1.0, intens_rate / 0.02),
        ["python-extractable"],
    )

    # transition_word_rate — discourse connectors per sentence
    _TRANSITIONS = {
        "however", "therefore", "meanwhile", "furthermore", "moreover",
        "consequently", "nevertheless", "nonetheless", "additionally",
        "accordingly", "subsequently", "alternatively", "conversely",
        "similarly", "likewise", "otherwise", "hence", "thus",
        "instead", "regardless", "notwithstanding",
    }
    trans_count = sum(1 for w in lower_words if w in _TRANSITIONS)
    trans_per_sent = trans_count / n_sentences
    profile["transition_word_rate"] = _directional_element(
        "voice_tone",
        "more" if trans_per_sent >= 0.05 else "less",
        min(1.0, trans_per_sent / 0.2),
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


# ---------------------------------------------------------------------------
# Tier 2: spaCy-based elements (optional)
# ---------------------------------------------------------------------------

def _add_spacy_elements(profile: dict, text: str) -> None:
    """Extract POS/dependency/NER elements using spaCy. Skips if unavailable."""
    nlp = _get_spacy_nlp()
    if nlp is None:
        return

    # Truncate very long texts — voice elements stabilize well before 100K chars
    analysis_text = text[:100_000] if len(text) > 100_000 else text
    doc = nlp(analysis_text)

    # Count POS tags
    pos_counts = {}
    for token in doc:
        pos_counts[token.pos_] = pos_counts.get(token.pos_, 0) + 1
    total_tokens = len(doc)

    # --- adjective_to_noun_ratio ---
    adj_count = pos_counts.get("ADJ", 0)
    noun_count = pos_counts.get("NOUN", 0) + pos_counts.get("PROPN", 0)
    adj_noun_ratio = adj_count / noun_count if noun_count > 0 else 0.0
    profile["adjective_to_noun_ratio"] = _metric_element(
        "syntactic", adj_noun_ratio, ["spacy-extractable"],
        weight=_clamp(adj_noun_ratio / 1.0),
    )

    # --- adverb_density ---
    adv_count = pos_counts.get("ADV", 0)
    adv_density = adv_count / total_tokens if total_tokens > 0 else 0.0
    profile["adverb_density"] = _directional_element(
        "syntactic",
        "more" if adv_density >= 0.05 else "less",
        min(1.0, adv_density / 0.1),
        ["spacy-extractable"],
    )

    # --- verb_tense_past_ratio and verb_tense_present_ratio ---
    past_count = 0
    present_count = 0
    finite_verb_count = 0
    for token in doc:
        if token.pos_ in ("VERB", "AUX"):
            tense = token.morph.get("Tense")
            if tense:
                finite_verb_count += 1
                if "Past" in tense:
                    past_count += 1
                elif "Pres" in tense:
                    present_count += 1

    past_ratio = past_count / finite_verb_count if finite_verb_count > 0 else 0.0
    present_ratio = present_count / finite_verb_count if finite_verb_count > 0 else 0.0

    profile["verb_tense_past_ratio"] = _metric_element(
        "syntactic", past_ratio, ["spacy-extractable"],
        weight=_clamp(past_ratio),
    )
    profile["verb_tense_present_ratio"] = _metric_element(
        "syntactic", present_ratio, ["spacy-extractable"],
        weight=_clamp(present_ratio),
    )

    # --- clause_depth_avg ---
    def _tree_depth(token):
        depth = 0
        current = token
        while current.head != current:
            depth += 1
            current = current.head
        return depth

    sentence_max_depths = []
    for sent in doc.sents:
        max_depth = max((_tree_depth(token) for token in sent), default=0)
        sentence_max_depths.append(max_depth)

    avg_depth = (sum(sentence_max_depths) / len(sentence_max_depths)
                 if sentence_max_depths else 0.0)
    profile["clause_depth_avg"] = _metric_element(
        "syntactic", avg_depth, ["spacy-extractable"],
        weight=_clamp(avg_depth / 10.0),
    )

    # --- named_entity_density ---
    ner_count = len(doc.ents)
    ner_density = ner_count / total_tokens if total_tokens > 0 else 0.0
    profile["named_entity_density"] = _metric_element(
        "lexical", ner_density, ["spacy-extractable"],
        weight=_clamp(ner_density / 0.05),
    )

    # --- passive_voice_rate upgrade ---
    # Override the regex-based passive_voice_rate with spaCy nsubjpass detection
    n_sentences_spacy = max(len(list(doc.sents)), 1)
    passive_sents = set()
    for token in doc:
        if token.dep_ in ("nsubjpass", "auxpass"):
            passive_sents.add(token.sent.start)
    passive_rate = len(passive_sents) / n_sentences_spacy
    profile["passive_voice_rate"] = _directional_element(
        "syntactic",
        "less",
        min(1.0, passive_rate / 0.3),
        ["spacy-extractable"],
    )


# ---------------------------------------------------------------------------
# Tier 3: Sentiment, Topic Coherence, Discourse-Adjacent (optional)
# ---------------------------------------------------------------------------

def _add_tier3_elements(profile: dict, text: str, sentences: list,
                        paragraphs: list) -> None:
    """Extract Tier 3 NLP elements. Each sub-category fails independently."""
    _add_sentiment_elements(profile, sentences)
    _add_topic_elements(profile, paragraphs)
    _add_discourse_elements(profile, paragraphs)


def _add_sentiment_elements(profile: dict, sentences: list) -> None:
    """Extract sentiment elements using VADER. Skips if unavailable or <3 sentences."""
    analyzer = _get_vader()
    if analyzer is None:
        return
    if len(sentences) < 3:
        return

    scores = [analyzer.polarity_scores(s)["compound"] for s in sentences]

    # sentiment_mean — average emotional tone
    mean_score = sum(scores) / len(scores)
    profile["sentiment_mean"] = _metric_element(
        "voice_tone", mean_score, ["python-extractable", "tier3"],
        weight=_clamp(abs(mean_score)),
    )

    # sentiment_variance — emotional range
    variance = sum((s - mean_score) ** 2 for s in scores) / len(scores)
    profile["sentiment_variance"] = _metric_element(
        "voice_tone", variance, ["python-extractable", "tier3"],
        weight=_clamp(variance / 0.5),
    )

    # sentiment_shift_rate — polarity flip frequency
    threshold = 0.05
    shifts = 0
    for i in range(1, len(scores)):
        prev_pos = scores[i - 1] > threshold
        prev_neg = scores[i - 1] < -threshold
        curr_pos = scores[i] > threshold
        curr_neg = scores[i] < -threshold
        if (prev_pos and curr_neg) or (prev_neg and curr_pos):
            shifts += 1
    shift_rate = shifts / (len(scores) - 1) if len(scores) > 1 else 0.0
    profile["sentiment_shift_rate"] = _metric_element(
        "voice_tone", shift_rate, ["python-extractable", "tier3"],
        weight=_clamp(shift_rate),
    )


def _add_topic_elements(profile: dict, paragraphs: list) -> None:
    """Extract topic coherence elements. Placeholder for next task."""
    pass


def _add_discourse_elements(profile: dict, paragraphs: list) -> None:
    """Extract discourse-adjacent elements. Placeholder for next task."""
    pass
