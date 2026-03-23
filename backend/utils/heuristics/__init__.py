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

__all__ = [
    "check_yules_k", "check_hapax_legomena",
    "check_function_word_deviation", "check_mattr",
    "check_zipf_deviation", "check_compression_ratio",
    "check_sentence_opener_pos", "check_word_length_distribution",
    "check_char_ngram_profile", "check_burrows_delta",
    "combine_signals", "estimate_confidence", "detect_genre",
]
