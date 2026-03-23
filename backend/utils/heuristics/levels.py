"""Heuristic-to-level classification and level-specific runners.

Each heuristic is assigned to one analysis level:
- document: runs once on the full text (vocabulary richness, compression, genre stats)
- paragraph: runs per-paragraph (self-containment, transition stacking, uniformity)
- sentence: runs per-sentence (buzzwords, hedge words, structural tells)
- cross: computed at one level but informed by others (contractions, opener diversity)
"""

# Level assignment for every active heuristic (weight > 0 in reference_data.py)
HEURISTIC_LEVELS = {
    # Document-only: whole-text statistics
    "compression_ratio": "document",
    "yules_k": "document",
    "hapax_legomena": "document",
    "vocabulary_richness": "document",
    "word_length_distribution": "document",
    "char_ngram_profile": "document",
    "synonym_treadmill": "document",
    "emoji_density": "document",
    "bullet_subheading_overuse": "document",

    # Paragraph-level: per-paragraph analysis
    "paragraph_uniformity": "paragraph",
    "self_contained_paragraphs": "paragraph",
    "transition_stacks": "paragraph",
    "hedge_clusters": "paragraph",
    "digression_absence": "paragraph",

    # Sentence-level: per-sentence pattern matching
    "buzzwords": "sentence",
    "hedge_words": "sentence",
    "structural_patterns": "sentence",
    "dual_adjectives": "sentence",
    "trailing_participial": "sentence",
    "confident_declarations": "sentence",
    "false_dichotomy": "sentence",
    "emotional_exposition": "sentence",
    "length_uniformity": "sentence",
    "transitions": "sentence",
    "punctuation_fingerprint": "sentence",

    # Sentence + document: multi-word AI phrases (Phase 3.6)
    "ai_phrases": "sentence",

    # Cross-level: computed doc-wide but inform sentence/paragraph scoring
    "contractions": "cross",
    "first_person": "cross",
    "entity_density": "cross",
    "sentence_opener_pos": "cross",
    "ai_opening_phrases": "cross",
    "opening_diversity": "cross",
    "adverb_density": "cross",
}


def get_heuristics_for_level(level: str) -> set[str]:
    """Return set of heuristic names assigned to a given level."""
    return {name for name, lvl in HEURISTIC_LEVELS.items() if lvl == level}
