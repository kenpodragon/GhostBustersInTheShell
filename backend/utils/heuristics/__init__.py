"""Advanced AI detection heuristics.

Phase 2.3: Lexical, structural, and stylometric analysis.
"""
from utils.heuristics.lexical import (
    check_yules_k,
    check_hapax_legomena,
    check_function_word_deviation,
    check_mattr,
)
from utils.heuristics.structural import (
    check_zipf_deviation,
    check_compression_ratio,
    check_sentence_opener_pos,
    check_word_length_distribution,
    check_char_ngram_profile,
)
from utils.heuristics.stylometric import check_burrows_delta
from utils.heuristics.scoring import combine_signals, estimate_confidence, detect_genre
from utils.heuristics.crowdsourced import (
    check_em_dash_overuse, check_ai_opening_phrases,
    check_closing_summary, check_question_exclamation_absence,
    check_oxford_comma_consistency, check_bullet_subheading_overuse,
    check_digression_absence, check_consensus_middle,
)
from utils.heuristics.ai_phrases import check_ai_phrases, check_ai_phrases_sentence
from utils.heuristics.classification import classify_category, CATEGORIES
from utils.heuristics.lm_signals import (
    check_compression_ratio_sentence, check_compression_ratio_document,
    check_repetition_density, check_ngram_perplexity, check_ngram_burstiness,
    check_zipf_deviation_v2, check_mattr_v2, check_ttr_variance,
    load_corpus, get_genre_baselines,
)

__all__ = [
    "check_yules_k", "check_hapax_legomena",
    "check_function_word_deviation", "check_mattr",
    "check_zipf_deviation", "check_compression_ratio",
    "check_sentence_opener_pos", "check_word_length_distribution",
    "check_char_ngram_profile", "check_burrows_delta",
    "combine_signals", "estimate_confidence", "detect_genre",
    "check_em_dash_overuse", "check_ai_opening_phrases",
    "check_closing_summary", "check_question_exclamation_absence",
    "check_oxford_comma_consistency", "check_bullet_subheading_overuse",
    "check_digression_absence", "check_consensus_middle",
    "check_ai_phrases", "check_ai_phrases_sentence",
    "classify_category", "CATEGORIES",
    "check_compression_ratio_sentence", "check_compression_ratio_document",
    "check_repetition_density", "check_ngram_perplexity", "check_ngram_burstiness",
    "check_zipf_deviation_v2", "check_mattr_v2", "check_ttr_variance",
    "load_corpus", "get_genre_baselines",
]
