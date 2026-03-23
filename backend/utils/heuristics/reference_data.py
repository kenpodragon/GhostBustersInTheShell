"""Reference distributions for heuristic analysis.

Sources:
- Function word frequencies: Brown Corpus (Francis & Kucera, 1982)
- Genre baselines: derived from research in docs/research/statistical_heuristics_algorithms.md
"""

FUNCTION_WORD_FREQS = {
    "the": 69.97, "of": 36.41, "and": 28.85, "to": 26.15, "a": 23.08,
    "in": 21.34, "that": 10.59, "is": 10.10, "was": 9.78, "it": 9.97,
    "for": 9.49, "as": 7.70, "with": 7.17, "his": 6.50, "on": 6.09,
    "be": 6.39, "at": 5.30, "by": 5.07, "i": 5.16, "this": 4.57,
    "had": 4.89, "not": 4.60, "are": 4.39, "but": 4.15, "from": 3.97,
    "or": 3.57, "have": 3.57, "an": 3.28, "they": 2.77, "which": 2.90,
    "one": 2.63, "you": 2.89, "were": 2.51, "her": 2.44, "all": 2.41,
    "she": 2.10, "there": 2.09, "would": 1.92, "their": 1.87, "we": 1.85,
    "him": 1.71, "been": 1.72, "has": 1.64, "when": 1.62, "who": 1.55,
    "will": 1.53, "no": 1.41, "more": 1.38, "if": 1.37, "out": 1.31,
}

GENRE_BASELINES = {
    "general": {"ai_floor": 35, "human_ceil": 25, "description": "General prose"},
    "academic": {"ai_floor": 30, "human_ceil": 30, "description": "Academic/formal writing"},
    "casual": {"ai_floor": 40, "human_ceil": 15, "description": "Casual/conversational"},
    "business": {"ai_floor": 35, "human_ceil": 28, "description": "Business communications"},
    "creative": {"ai_floor": 45, "human_ceil": 20, "description": "Creative/fiction writing"},
    "resume": {"ai_floor": 30, "human_ceil": 30, "description": "Resume/cover letter"},
}

HEURISTIC_WEIGHTS = {
    "buzzwords": 0.9, "hedge_words": 0.6, "transitions": 0.5,
    "structural_patterns": 0.5, "dual_adjectives": 0.7, "trailing_participial": 0.6,
    "confident_declarations": 0.5, "false_dichotomy": 0.7, "emotional_exposition": 0.6,
    "length_uniformity": 0.7, "readability": 0.4, "contractions": 0.6,
    "first_person": 0.5, "passive_voice": 0.4, "adverb_density": 0.5,
    "entity_density": 0.4, "punctuation_fingerprint": 0.5, "opening_diversity": 0.7,
    "hedge_clusters": 0.6, "transition_stacks": 0.6, "synonym_treadmill": 0.7,
    "emoji_density": 0.3, "sensory_checklist": 0.4, "self_contained_paragraphs": 0.5,
    "vocabulary_richness": 0.5, "paragraph_uniformity": 0.6,
    "yules_k": 0.7, "hapax_legomena": 0.6, "function_word_deviation": 0.7,
    "mattr": 0.6, "zipf_deviation": 0.7, "compression_ratio": 0.8,
    "sentence_opener_pos": 0.6, "burrows_delta": 0.8,
    "char_ngram_profile": 0.5, "word_length_distribution": 0.4,
}
