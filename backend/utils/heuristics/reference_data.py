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
    # Phase 2.4 calibrated baselines (from 60-sample corpus, 2026-03-23)
    "general": {"ai_floor": 30, "human_ceil": 25, "description": "General prose"},
    "academic": {"ai_floor": 30, "human_ceil": 35, "description": "Academic/formal writing — inherently formal, higher human ceiling"},
    "casual": {"ai_floor": 25, "human_ceil": 22, "description": "Casual/conversational — AI casual harder to detect"},
    "business": {"ai_floor": 35, "human_ceil": 25, "description": "Business communications"},
    "creative": {"ai_floor": 22, "human_ceil": 22, "description": "Creative/fiction — AI creative is least detectable"},
    "resume": {"ai_floor": 30, "human_ceil": 25, "description": "Resume/cover letter"},
}

HEURISTIC_WEIGHTS = {
    # Phase 2.4 calibrated weights (optimized against 60-sample corpus, 2026-03-23)
    # Top discriminators (boosted)
    "sentence_opener_pos": 1.0,     # Best discriminator: +17.9 AI-Human gap
    "contractions": 1.0,            # AI avoids contractions: +12.5 gap
    "entity_density": 1.0,          # AI lacks specifics: +10.3 gap
    "ai_opening_phrases": 1.0,      # "In today's world..." dead giveaway
    "buzzwords": 0.9,               # Hard-ban vocabulary stays high
    "compression_ratio": 0.8,       # AI text compresses more uniformly
    # Good discriminators (kept or slightly adjusted)
    "dual_adjectives": 0.7, "false_dichotomy": 0.7, "synonym_treadmill": 0.7,
    "length_uniformity": 0.7, "opening_diversity": 0.7, "yules_k": 0.7,
    "function_word_deviation": 0.7,  # Fires broadly but still useful in combination
    "adverb_density": 0.7, "digression_absence": 0.67,
    "hedge_words": 0.6, "hedge_clusters": 0.6, "transition_stacks": 0.6,
    "trailing_participial": 0.6, "emotional_exposition": 0.6,
    "hapax_legomena": 0.6, "paragraph_uniformity": 0.6,
    # Moderate discriminators
    "structural_patterns": 0.5, "confident_declarations": 0.5,
    "self_contained_paragraphs": 0.5, "vocabulary_richness": 0.5,
    "transitions": 0.5, "char_ngram_profile": 0.5,
    "bullet_subheading_overuse": 0.5,
    "word_length_distribution": 0.48,
    "first_person": 0.35,           # Good gap but can fire on human casual text
    "punctuation_fingerprint": 0.3,  # Fires broadly, modest discrimination
    "emoji_density": 0.3,
    # Noise/harmful — crushed by optimizer (fire on both AI and human equally)
    "zipf_deviation": 0.1,          # Fires 100% on both — no discrimination
    "burrows_delta": 0.1,           # Fires 100% on both, scores human HIGHER
    "em_dash_overuse": 0.1,         # Humans use more em dashes than AI
    "passive_voice": 0.1,           # Near-zero discrimination
    "mattr": 0.1,                   # Fires broadly, weak discrimination
    "readability": 0.1,             # Near-zero discrimination
    "sensory_checklist": 0.1,       # Rarely fires
    "question_exclamation_absence": 0.1,  # Fires on both
    "oxford_comma_consistency": 0.1,      # Rarely fires
    "closing_summary": 0.1,         # Rarely fires
    "consensus_middle": 0.1,        # Rarely fires
}
