"""Translates numerical style element weights into precise English descriptors."""

# Weight-to-intensity mapping for directional elements
_MORE_DESCRIPTORS = {
    (0.0, 0.2): "occasionally",
    (0.2, 0.4): "sometimes",
    (0.4, 0.6): "moderately",
    (0.6, 0.8): "frequently",
    (0.8, 1.01): "consistently",
}

_LESS_DESCRIPTORS = {
    (0.0, 0.2): "slightly reduce",
    (0.2, 0.4): "limit",
    (0.4, 0.6): "minimize",
    (0.6, 0.8): "strongly avoid",
    (0.8, 1.01): "never use",
}

# Human-readable names for element identifiers
_ELEMENT_LABELS = {
    "contraction_rate": "contractions",
    "avg_sentence_length": "average sentence length",
    "sentence_length_stddev": "sentence length variety",
    "short_sentence_ratio": "short sentences",
    "long_sentence_ratio": "long sentences",
    "fragment_usage": "sentence fragments",
    "passive_voice_rate": "passive voice constructions",
    "em_dash_usage": "em dashes",
    "semicolon_usage": "semicolons",
    "ellipsis_usage": "ellipses",
    "exclamation_rate": "exclamation marks",
    "parenthetical_usage": "parenthetical asides",
    "rhetorical_question_rate": "rhetorical questions",
    "first_person_usage": "first-person pronouns (I, we, my)",
    "second_person_usage": "second-person pronouns (you, your)",
    "vocabulary_richness": "vocabulary diversity",
    "avg_word_length": "average word length",
    "long_word_frequency": "long words (6+ characters)",
    "jargon_level": "technical jargon",
    "flesch_kincaid_grade": "Flesch-Kincaid grade level",
    "flesch_reading_ease": "Flesch reading ease score",
    "gunning_fog_index": "Gunning Fog index",
    "coleman_liau_index": "Coleman-Liau index",
    "smog_index": "SMOG index",
    "automated_readability_index": "Automated Readability Index",
}


def _get_descriptor(weight, descriptors):
    for (lo, hi), desc in descriptors.items():
        if lo <= weight < hi:
            return desc
    return list(descriptors.values())[-1]


def translate_element(element):
    """Translate a single style element into an English instruction."""
    name = element["name"]
    label = _ELEMENT_LABELS.get(name, name.replace("_", " "))
    el_type = element["element_type"]

    if el_type == "metric":
        target = element.get("target_value", 0)
        weight = element.get("weight", 0.5)
        tolerance = "closely" if weight > 0.7 else "approximately" if weight > 0.4 else "roughly"
        return f"Target {tolerance} a {label} of {target:.1f}."

    direction = element.get("direction", "more")
    weight = element.get("weight", 0.5)

    if direction == "more":
        intensity = _get_descriptor(weight, _MORE_DESCRIPTORS)
        return f"Use {label} {intensity}."
    else:
        intensity = _get_descriptor(weight, _LESS_DESCRIPTORS)
        return f"{intensity.capitalize()} {label}."


def translate_elements_to_english(elements):
    """Translate a list of style elements into a combined English style guide."""
    if not elements:
        return ""
    lines = []
    by_category = {}
    for el in elements:
        cat = el.get("category", "other")
        by_category.setdefault(cat, []).append(el)
    for cat in sorted(by_category.keys()):
        for el in by_category[cat]:
            lines.append(translate_element(el))
    return "\n".join(lines)
