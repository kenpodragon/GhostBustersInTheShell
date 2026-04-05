"""Human-readable descriptions for detection patterns.

Used by the /api/analyze response to provide frontend tooltips.
"""

PATTERN_DESCRIPTIONS = {
    # --- Sentence-level ---
    "buzzword": {
        "display_name": "Buzzword Usage",
        "description": "Sentence contains overused AI-favored buzzwords (e.g. 'leverage', 'robust', 'seamless') that inflate perceived sophistication without adding meaning.",
    },
    "uniform_length": {
        "display_name": "Uniform Sentence Length",
        "description": "Sentences in this passage are suspiciously similar in length, lacking the natural variation found in human writing.",
    },
    "hedge_word": {
        "display_name": "Hedge Word",
        "description": "Sentence uses hedging language ('often', 'may', 'can', 'sometimes') that softens claims — a common AI strategy to avoid being wrong.",
    },
    "ai_transition": {
        "display_name": "AI Transition Phrase",
        "description": "Sentence opens with a formulaic transition ('Furthermore,', 'Moreover,', 'In addition,') that AI models use to chain ideas mechanically.",
    },
    "not_only_but_also": {
        "display_name": "Not Only… But Also",
        "description": "Uses the 'not only X but also Y' construction — a rhetorical structure AI models reach for when padding parallel points.",
    },
    "it_is_adj_to": {
        "display_name": "It Is [Adjective] To",
        "description": "Opens with an impersonal 'It is important/essential/crucial to…' construction — a distancing pattern common in AI-generated text.",
    },
    "rule_of_three": {
        "display_name": "Rule of Three",
        "description": "Lists exactly three items or ideas — AI models default to tricolon structure when enumerating points, creating artificial rhythm.",
    },
    "hedging_sandwich": {
        "display_name": "Hedging Sandwich",
        "description": "Hedges appear at both the start and end of the sentence, bracketing the claim with disclaimers to project balance without substance.",
    },
    "front_loaded_description": {
        "display_name": "Front-Loaded Description",
        "description": "Sentence begins with a long descriptive or qualifying phrase before the main clause — a structural pattern AI uses to sound thorough.",
    },
    "dual_adjective_pair": {
        "display_name": "Dual Adjective Pair",
        "description": "Uses two adjectives together (e.g. 'clear and concise', 'robust and scalable') — AI often doubles up modifiers to fill weight.",
    },
    "trailing_participial": {
        "display_name": "Trailing Participial Phrase",
        "description": "Ends with a participial phrase ('…enabling X', '…creating Y') that tacks on an effect — a filler construction common in AI text.",
    },
    "confident_declaration": {
        "display_name": "Confident Declaration",
        "description": "Makes a sweeping declarative statement with high certainty but little evidence — AI tends to assert rather than argue.",
    },
    "false_dichotomy": {
        "display_name": "False Dichotomy",
        "description": "Presents only two options when more exist ('either X or Y', 'without X, Y fails') — a simplifying rhetorical move common in AI outputs.",
    },
    "emotional_exposition": {
        "display_name": "Emotional Exposition",
        "description": "Describes emotional states from the outside ('this can feel overwhelming', 'many people struggle with') instead of expressing them directly.",
    },
    "ai_phrase": {
        "display_name": "AI Phrase",
        "description": "Contains a phrase strongly associated with AI-generated text — a fixed expression that appears disproportionately in model outputs.",
    },
    "ai_opening_phrase": {
        "display_name": "AI Opening Phrase",
        "description": "Sentence starts with a phrase characteristically used by AI models to open paragraphs or responses (e.g. 'It is worth noting that…').",
    },

    # --- Paragraph-level ---
    "para_uniform_sentences": {
        "display_name": "Uniform Sentence Structure (Paragraph)",
        "description": "Sentences within this paragraph follow similar structural templates, suggesting machine generation rather than organic composition.",
    },
    "para_low_vocab": {
        "display_name": "Low Vocabulary Variety (Paragraph)",
        "description": "This paragraph reuses the same words at a higher rate than natural writing — a sign of limited lexical range typical of AI output.",
    },
    "uniform_paragraphs": {
        "display_name": "Uniform Paragraph Length",
        "description": "Paragraphs across the document are suspiciously close in length, lacking the organic variation of human writing.",
    },
    "low_paragraph_variance": {
        "display_name": "Low Paragraph Variance",
        "description": "The document's paragraphs show low variance in structure and content density — consistent with AI's tendency to generate even, balanced sections.",
    },
    "uniform_para_sentences": {
        "display_name": "Uniform Sentence Count per Paragraph",
        "description": "Each paragraph contains nearly the same number of sentences — a mechanical regularity not typical of human writing.",
    },

    # --- Document-level ---
    "mid_range_readability": {
        "display_name": "Mid-Range Readability",
        "description": "The document scores in a narrow mid-range on readability metrics — AI tends to target accessible, general-audience prose by default.",
    },
    "uniform_reading_ease": {
        "display_name": "Uniform Reading Ease",
        "description": "Reading ease scores are suspiciously consistent across sections — human writing naturally varies in complexity and rhythm.",
    },
    "no_contractions": {
        "display_name": "No Contractions",
        "description": "The text contains no contractions (don't, it's, we're) — an absence that makes prose feel formal and AI-like rather than conversational.",
    },
    "low_contractions": {
        "display_name": "Low Contraction Rate",
        "description": "Very few contractions appear in the text — below what is typical for natural informal or semi-formal writing.",
    },
    "no_first_person": {
        "display_name": "No First-Person Voice",
        "description": "No first-person pronouns (I, me, my, we) appear — AI avoids personal voice by default, producing detached, impersonal text.",
    },
    "low_first_person": {
        "display_name": "Low First-Person Usage",
        "description": "First-person pronouns are used rarely — below the rate typical for writing with a genuine personal perspective.",
    },
    "high_passive_voice": {
        "display_name": "High Passive Voice",
        "description": "Passive constructions dominate — AI frequently uses passive voice to maintain a neutral, authoritative tone.",
    },
    "elevated_passive_voice": {
        "display_name": "Elevated Passive Voice",
        "description": "Passive voice appears more than expected for this writing type — a mild but notable signal of AI phrasing patterns.",
    },
    "high_adverb_density": {
        "display_name": "High Adverb Density",
        "description": "Adverbs are heavily used ('significantly', 'particularly', 'effectively') — AI pads confidence and precision with adverb overuse.",
    },
    "elevated_adverb_density": {
        "display_name": "Elevated Adverb Density",
        "description": "Adverb usage is above average — a moderate signal of AI-generated prose that over-modifies verbs and adjectives.",
    },
    "ai_intensifiers": {
        "display_name": "AI Intensifiers",
        "description": "Overuse of intensifying adverbs ('crucial', 'vital', 'incredibly', 'highly') that AI uses to signal importance without substantiation.",
    },
    "no_specifics": {
        "display_name": "No Specific Details",
        "description": "The text contains no concrete specifics — no dates, names, numbers, or examples — relying entirely on abstractions.",
    },
    "low_specifics": {
        "display_name": "Low Specificity",
        "description": "Specific details are sparse — the text stays at a general level, which is common when AI generates content without grounded knowledge.",
    },
    "high_comma_density": {
        "display_name": "High Comma Density",
        "description": "Commas appear at an unusually high rate — AI tends to construct long, clause-heavy sentences that require heavy punctuation.",
    },
    "semicolon_overuse": {
        "display_name": "Semicolon Overuse",
        "description": "Semicolons appear more frequently than in typical human writing — AI uses them to create an academic register.",
    },
    "no_irregular_punctuation": {
        "display_name": "No Irregular Punctuation",
        "description": "The text uses only standard punctuation with no dashes, ellipses, parentheticals, or stylistic choices — human writing is rarely this clean.",
    },
    "hedge_cluster": {
        "display_name": "Hedge Cluster",
        "description": "Multiple hedging expressions appear in close proximity — AI stacks qualifiers to cover uncertainty across a section.",
    },
    "hedge_regular_spacing": {
        "display_name": "Regularly Spaced Hedges",
        "description": "Hedging language is distributed at regular intervals throughout the text — a mechanical pattern unlike human uncertainty expression.",
    },
    "transition_stacks": {
        "display_name": "Transition Stacking",
        "description": "Multiple transition phrases appear in sequence or at high density — AI over-signals logical flow between ideas.",
    },
    "synonym_treadmill": {
        "display_name": "Synonym Treadmill",
        "description": "The text rotates through synonyms for the same concept rather than varying its approach — a vocabulary-spreading technique AI uses to appear non-repetitive.",
    },
    "emoji_overuse": {
        "display_name": "Emoji Overuse",
        "description": "Emojis appear at an unusually high density — AI sometimes uses emojis strategically to simulate warmth or engagement.",
    },
    "elevated_emoji": {
        "display_name": "Elevated Emoji Usage",
        "description": "Emoji usage is above average for the context — a mild signal that the text may be optimizing for perceived friendliness.",
    },
    "sensory_checklist": {
        "display_name": "Sensory Checklist",
        "description": "The text touches multiple senses (sight, sound, smell, taste, touch) in a formulaic sweep — AI often includes sensory variety as a writing quality checkbox.",
    },
    "sensory_rotation": {
        "display_name": "Sensory Rotation",
        "description": "Sensory references rotate through senses in a patterned way rather than arising organically from the content.",
    },
    "self_contained_paragraphs": {
        "display_name": "Self-Contained Paragraphs",
        "description": "Each paragraph is fully self-contained with minimal cross-reference — AI structures text as modular units rather than building continuous arguments.",
    },
    "rhetorical_question_chain": {
        "display_name": "Rhetorical Question Chain",
        "description": "Multiple rhetorical questions appear in sequence — AI uses this technique to simulate engagement and set up structured answers.",
    },
    "circular_repetition": {
        "display_name": "Circular Repetition",
        "description": "Ideas introduced early are restated at the end without development — AI defaults to intro-body-conclusion loops that circle back rather than advance.",
    },
    "hollow_informality": {
        "display_name": "Hollow Informality",
        "description": "The text uses casual markers ('you know', 'of course', 'let's face it') without genuine informal rhythm — simulated friendliness that doesn't land.",
    },
    "as_you_know_exposition": {
        "display_name": "As-You-Know Exposition",
        "description": "Explains obvious context as if the reader doesn't know it ('As you probably know…', 'It's no secret that…') — AI front-loads background to appear thorough.",
    },
    "tricolon_density": {
        "display_name": "Tricolon Density",
        "description": "Three-part parallel structures appear at high density across the document — AI relies on tricolons to create rhythm and completeness.",
    },
    "fragment_list": {
        "display_name": "Fragment List",
        "description": "Paragraph consists of short punchy fragments forming a list pattern — AI uses staccato one-word or two-word sentences for motivational effect.",
    },
    "staccato_rhythm": {
        "display_name": "Staccato Rhythm",
        "description": "Mix of very short fragments and longer explanatory sentences — AI-typical punchy motivational rhythm pattern.",
    },
    "buzzword_density": {
        "display_name": "Buzzword Density",
        "description": "AI-favored buzzwords appear at high frequency across the document — a systemic pattern of corporate or tech jargon overuse.",
    },
    "low_vocabulary_richness": {
        "display_name": "Low Vocabulary Richness",
        "description": "The type-token ratio is low — the text reuses a small vocabulary pool, typical of AI models optimizing for clarity over variety.",
    },
    "em_dash_heavy": {
        "display_name": "Em Dash Heavy",
        "description": "Em dashes appear at high frequency — AI models have recently over-indexed on em dashes as a stylistic marker of thoughtful writing.",
    },
    "em_dash_elevated": {
        "display_name": "Em Dash Elevated",
        "description": "Em dash usage is above average — a moderate signal associated with AI writing style in recent model generations.",
    },
    "ai_opening_phrases": {
        "display_name": "AI Opening Phrases",
        "description": "Paragraphs open with phrases strongly associated with AI models — formulaic starters that signal machine-generated structure.",
    },
    "ai_opening_phrases_heavy": {
        "display_name": "AI Opening Phrases (Heavy)",
        "description": "AI opening phrases appear at high density across the document — a strong systemic pattern of formulaic paragraph starts.",
    },
    "closing_summary": {
        "display_name": "Closing Summary",
        "description": "The document ends with a summary section restating earlier points — AI reliably produces recap conclusions as a structural default.",
    },
    "closing_summary_heavy": {
        "display_name": "Closing Summary (Heavy)",
        "description": "The closing section is heavily summary-focused, with extensive restatement of earlier content — a strong AI structural signal.",
    },
    "no_questions_exclamations": {
        "display_name": "No Questions or Exclamations",
        "description": "The text contains no question marks or exclamation points — complete absence of interrogative or emphatic punctuation is atypical in human writing.",
    },
    "rare_questions_exclamations": {
        "display_name": "Rare Questions or Exclamations",
        "description": "Questions and exclamations are nearly absent — below the rate found in naturally expressive human writing.",
    },
    "oxford_comma_perfect_consistency": {
        "display_name": "Perfect Oxford Comma Consistency",
        "description": "Oxford comma usage is perfectly consistent throughout — human writers occasionally slip, making perfect consistency a subtle AI signal.",
    },
    "heavy_structure": {
        "display_name": "Heavy Structural Formatting",
        "description": "The document uses extensive headers, bullets, and numbered lists — AI defaults to heavy formatting to organize information visibly.",
    },
    "moderate_structure": {
        "display_name": "Moderate Structural Formatting",
        "description": "Structural formatting (headers, lists) appears at a moderate level — above what is typical for natural flowing prose.",
    },
    "no_digressions": {
        "display_name": "No Digressions",
        "description": "The text stays strictly on topic with no tangents or digressions — human writers naturally wander; AI optimizes for focus.",
    },
    "few_digressions": {
        "display_name": "Few Digressions",
        "description": "The text rarely departs from its central topic — below the digression rate typical of genuine human writing.",
    },
    "consensus_middle": {
        "display_name": "Consensus Middle Ground",
        "description": "The text positions itself in the moderate center of any topic, avoiding strong stances — AI defaults to balance to minimize controversy.",
    },
    "consensus_middle_strong": {
        "display_name": "Consensus Middle Ground (Strong)",
        "description": "The text strongly avoids taking sides, consistently offering balanced perspectives — a pronounced AI pattern of controversy avoidance.",
    },
}


def get_pattern_info(name: str) -> dict:
    """Return display name and description for a detection pattern.

    Args:
        name: Internal pattern identifier.

    Returns:
        Dict with keys: name, display_name, description.
        Unknown patterns return display_name=name, description="".
    """
    entry = PATTERN_DESCRIPTIONS.get(name)
    if entry:
        return {
            "name": name,
            "display_name": entry["display_name"],
            "description": entry["description"],
        }
    return {
        "name": name,
        "display_name": name,
        "description": "",
    }
