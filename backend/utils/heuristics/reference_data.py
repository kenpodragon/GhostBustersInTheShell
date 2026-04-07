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
    # Phase 3.4 calibrated baselines (from 116-sample corpus, 2026-03-23)
    "general": {"ai_floor": 30, "human_ceil": 25, "description": "General prose"},
    "academic": {"ai_floor": 30, "human_ceil": 40, "description": "Academic/formal writing — inherently formal, higher human ceiling"},
    "casual": {"ai_floor": 25, "human_ceil": 22, "description": "Casual/conversational — AI casual harder to detect"},
    "business": {"ai_floor": 35, "human_ceil": 25, "description": "Business communications"},
    "creative": {"ai_floor": 22, "human_ceil": 28, "description": "Creative/fiction — literary style triggers false positives"},
    "resume": {"ai_floor": 30, "human_ceil": 25, "description": "Resume/cover letter"},
    "memoir": {"ai_floor": 25, "human_ceil": 30, "description": "Memoir/personal narrative — literary but personal"},
    "poetry": {"ai_floor": 20, "human_ceil": 40, "description": "Poetry — highly variable style, many false positive triggers"},
    "literary": {"ai_floor": 22, "human_ceil": 35, "description": "Literary fiction — classic and modern literary prose"},
}

# Hard-ban buzzword lists (moved from detector.py Phase 3.12 A5)
HARD_BAN_VERBS = {
    "delve", "navigate", "foster", "leverage", "harness", "empower",
    "unlock", "catalyze", "galvanize", "utilize", "spearhead", "synergize",
    "operationalize", "revolutionize", "supercharge", "elevate", "amplify",
    "streamline", "champion", "evangelize", "pioneer", "facilitate",
    "optimize", "incentivize", "conceptualize", "contextualize",
    "problematize", "underscore", "showcase", "illuminate",
    # Crowdsourced additions
    "bolster", "reimagine", "transcend", "demystify",
    "unpack", "unravel", "embark", "endeavor", "resonate",
    "captivate", "cultivate", "envision", "propel",
    "augment", "orchestrate", "curate", "architect", "ideate",
    # Phase 3.12 expansion (web research + Claude/Gemini cross-ref)
    "accelerate", "align", "democratize", "deploy", "elucidate",
    "enable", "iterate", "reshape", "synthesize", "tackle",
}

HARD_BAN_ADJ = {
    "robust", "holistic", "paramount", "transformative", "cutting-edge",
    "seamless", "innovative", "groundbreaking", "comprehensive", "dynamic",
    "game-changing", "best-in-class", "world-class", "state-of-the-art",
    "mission-critical", "enterprise-grade", "multifaceted", "nuanced",
    "pivotal", "compelling", "invaluable", "indispensable", "unparalleled",
    "unprecedented", "myriad",
    # Crowdsourced additions
    "meticulous", "intricate", "vibrant", "bustling", "nestled",
    "thoughtful", "noteworthy", "commendable", "remarkable", "insightful",
    "profound", "impactful", "actionable", "scalable", "bespoke",
    "granular", "overarching", "undeniable", "instrumental",
    "versatile", "ubiquitous", "burgeoning", "nascent",
    "seminal", "salient", "cogent", "astute", "discerning",
    # Phase 3.12 expansion
    "crucial", "data-driven", "disruptive", "ever-evolving", "integral",
    "proactive", "purpose-driven", "resilient", "strategic",
}

HARD_BAN_FILLER = {
    "furthermore", "moreover", "additionally", "consequently", "nevertheless",
    "paradigm", "ecosystem", "synergy", "landscape", "realm", "tapestry",
    "underpinning", "bedrock", "cornerstone", "linchpin", "crucible",
    "zeitgeist", "ethos", "nexus", "interplay", "juxtaposition",
    # Crowdsourced additions
    "plethora", "gamut", "spectrum",
    "confluence", "dichotomy", "trajectory", "framework", "methodology",
    "stakeholder", "deliverable", "bandwidth", "synergistic", "proactive",
    "aforementioned", "henceforth", "notwithstanding", "thereof", "whereby",
}

# Multi-word filler phrases (checked separately via regex in detector)
HARD_BAN_FILLER_PHRASES = [
    "a testament to", "as such", "at its core", "at the forefront",
    "best practices", "building blocks", "deep dive", "double-edged sword",
    "in essence", "in light of", "key takeaway", "moving forward",
    "to this end", "what's more",
]

# NOTE: BUZZWORDS and HEURISTIC_WEIGHTS are also available via rules_config singleton
# (from utils.rules_config import rules_config). These constants are kept for backward
# compatibility during migration. Prefer rules_config in new code.
BUZZWORDS = HARD_BAN_VERBS | HARD_BAN_ADJ | HARD_BAN_FILLER

HEURISTIC_WEIGHTS = {
    # Phase 3.4 calibrated weights (optimized against 116-sample corpus, 2026-03-23)
    # Top discriminators — AI-ONLY patterns from corpus analysis
    "sentence_opener_pos": 1.0,     # Best discriminator: +17.9 AI-Human gap
    "contractions": 1.0,            # AI avoids contractions: +12.5 gap
    "entity_density": 1.0,          # AI lacks specifics: +10.3 gap
    "ai_opening_phrases": 1.0,      # "In today's world..." dead giveaway
    "ai_phrases": 0.9,              # Multi-word AI collocations (Phase 3.6)
    "buzzwords": 0.9,               # Hard-ban vocabulary stays high
    "compression_ratio": 0.8,       # AI text compresses more uniformly
    "length_uniformity": 0.8,       # uniform_length is AI-ONLY (+0.46 disc)
    "hedge_words": 0.8,             # AI-ONLY pattern (+0.46 disc)
    # Good discriminators
    "dual_adjectives": 0.7, "false_dichotomy": 0.7, "synonym_treadmill": 0.7,
    "opening_diversity": 0.7, "yules_k": 0.7,
    "adverb_density": 0.7, "digression_absence": 0.67,
    "hedge_clusters": 0.6, "transition_stacks": 0.6,
    "emotional_exposition": 0.6,
    "hapax_legomena": 0.6, "paragraph_uniformity": 0.6,
    # Moderate discriminators
    "structural_patterns": 0.5,
    "vocabulary_richness": 0.5,
    "transitions": 0.5, "char_ngram_profile": 0.5,
    "tricolon_density": 0.5,       # Phase 3.12 B2: rule-of-three aggregation
    "buzzword_density": 0.6,        # Phase 3.12 B3: unique buzzwords per 100 words
    "rhetorical_question_chain": 0.5,  # Phase 3.12 C1
    "circular_repetition": 0.4,        # Phase 3.12 C2
    "hollow_informality": 0.3,         # Phase 3.12 C3
    "as_you_know_exposition": 0.4,     # Phase 3.12 C4 (fiction only)
    "bullet_subheading_overuse": 0.5,
    "word_length_distribution": 0.48,
    "first_person": 0.35,           # Good gap but can fire on human casual text
    "emoji_density": 0.3,
    # Reduced — fire on human literary/memoir text too much
    "trailing_participial": 0.3,    # Was 0.6 — fires 22 human vs 20 AI (+0.22 disc only)
    "confident_declarations": 0.25, # Was 0.5 — fires more on human (-0.14 disc)
    "self_contained_paragraphs": 0.2,  # Was 0.5 — fires on human memoir/lit (-0.059 disc)
    "punctuation_fingerprint": 0.2, # Was 0.3 — fires broadly
    # KILLED — zero or negative discrimination on 116-sample corpus
    "zipf_deviation": 0.0,          # Fires 100% on ALL samples — zero discrimination
    "function_word_deviation": 0.0,  # Fires 100% on ALL samples — zero discrimination
    "burrows_delta": 0.0,           # Fires MORE on human (-0.185 disc) — actively harmful
    "readability": 0.0,             # mid_range_readability fires equally — zero disc
    "em_dash_overuse": 0.0,         # Fires 2x more on human (-0.031 disc)
    "passive_voice": 0.0,           # high_passive_voice is FP-ONLY
    "mattr": 0.0,                   # mattr_low is FP-ONLY, mattr_uniform weak
    "sensory_checklist": 0.0,       # sensory_rotation is FP-ONLY
    "question_exclamation_absence": 0.0,  # Fires on both
    "oxford_comma_consistency": 0.0,      # Rarely fires
    "closing_summary": 0.4,         # Re-enabled Phase 3.12 B4 with tone-contrast logic
    "consensus_middle": 0.0,        # Rarely fires
    # Phase 3.8: LM signals (active only when use_lm_signals=true)
    # Calibration 3.8.1: all set to 0.0 — n-gram corpus too coarse to discriminate.
    # Infrastructure kept for future improvement (neural perplexity, better corpus).
    "compression_ratio_sentence": 0.0,  # A1: fires broadly, no discrimination
    "compression_ratio_document": 0.0,  # A2: fires 100% AI, 93.9% human — noise
    "repetition_density": 0.0,          # A3: no discrimination
    "ngram_perplexity": 0.0,            # B1: slight signal but raises human scores
    "ngram_burstiness": 0.0,            # B2: barely fires (2.6% AI, 1.2% human)
    "zipf_deviation_v2": 0.0,           # C1: HARMFUL — fires more on human (-2.3 disc)
    "mattr_v2": 0.0,                    # C2: no discrimination
    "ttr_variance": 0.0,                # C3: no discrimination
    # Pangram-inspired heuristics (Phase 6) — calibrated 2026-04-07
    # semantic_monotony: threshold 0.30 — perfect separation (0/15 human FP, 3/3 AI TP)
    "semantic_monotony": 0.8,
    # chunked_consistency: CV<0.25 + mean>25 gate + 3 chunks min — long docs only
    "chunked_consistency": 0.4,
    # model_fingerprint: fires 50% AI (mean 33.8) vs 23% human (mean 17.1)
    "model_fingerprint": 0.7,
}
