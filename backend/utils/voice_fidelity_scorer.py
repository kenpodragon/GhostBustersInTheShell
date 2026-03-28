"""Voice fidelity scoring — measures how closely generated text matches a voice profile.

Pure processor. No DB access, no document fetching.
Three modes:
  - quantitative: re-parse generated text, compare element values to profile
  - qualitative: AI comparison of generated vs original sample text
  - both: quantitative first, then qualitative with element scores as context
"""
from utils.voice_generator import generate_voice_profile

VALID_MODES = {"quantitative", "qualitative", "both"}
EPSILON = 0.001


def score_fidelity(
    generated_text: str,
    profile_elements: list[dict] | None = None,
    sample_text: str | None = None,
    mode: str = "quantitative",
) -> dict:
    """Score how closely generated text matches a voice profile.

    Args:
        generated_text: The AI-rewritten output to evaluate.
        profile_elements: Already-parsed voice profile baseline (list of element dicts).
            Required for 'quantitative' and 'both' modes.
        sample_text: Original author writing for AI comparison.
            Required for 'qualitative' and 'both' modes.
        mode: 'quantitative', 'qualitative', or 'both'.

    Returns:
        Dict with scoring results keyed by mode.

    Raises:
        ValueError: If required inputs missing for the given mode.
    """
    if mode not in VALID_MODES:
        raise ValueError(f"mode must be one of {VALID_MODES}, got '{mode}'")
    if not generated_text:
        raise ValueError("generated_text is required")
    if mode in ("quantitative", "both") and not profile_elements:
        raise ValueError("profile_elements required for mode '{}'".format(mode))
    if mode in ("qualitative", "both") and not sample_text:
        raise ValueError("sample_text required for mode '{}'".format(mode))

    if mode == "quantitative":
        return _score_quantitative(generated_text, profile_elements)
    elif mode == "qualitative":
        return _score_qualitative(generated_text, sample_text)
    else:
        quant = _score_quantitative(generated_text, profile_elements)
        qual = _score_qualitative(generated_text, sample_text, quant_scores=quant)
        return {"mode": "both", "quantitative": quant, "qualitative": qual}


def _score_quantitative(generated_text: str, profile_elements: list[dict]) -> dict:
    """Parse generated text and compare element values against profile baseline."""
    parsed = generate_voice_profile(generated_text)

    per_element = []
    weighted_sum = 0.0
    weight_sum = 0.0
    matched = 0
    missing = 0

    for elem in profile_elements:
        name = elem["name"]
        weight = elem.get("weight", 0.5)

        if name not in parsed:
            missing += 1
            per_element.append({
                "name": name,
                "category": elem.get("category", ""),
                "element_type": elem.get("element_type", ""),
                "profile_value": _get_profile_value(elem),
                "generated_value": None,
                "similarity": 0.0,
                "weight": weight,
            })
            # Missing elements penalize the aggregate (similarity=0, weight counted)
            weight_sum += weight
            continue

        matched += 1
        parsed_elem = parsed[name]
        profile_value = _get_profile_value(elem)
        generated_value = _get_profile_value(parsed_elem)
        similarity = _compute_similarity(profile_value, generated_value)

        per_element.append({
            "name": name,
            "category": elem.get("category", ""),
            "element_type": elem.get("element_type", ""),
            "profile_value": profile_value,
            "generated_value": generated_value,
            "similarity": round(similarity, 4),
            "weight": weight,
        })
        weighted_sum += similarity * weight
        weight_sum += weight

    aggregate = round(weighted_sum / max(weight_sum, EPSILON), 4)

    return {
        "mode": "quantitative",
        "aggregate_similarity": aggregate,
        "element_count": len(profile_elements),
        "elements_matched": matched,
        "elements_missing": missing,
        "per_element": per_element,
    }


def _get_profile_value(elem: dict) -> float:
    """Extract the comparable numeric value from an element.

    Metric elements use target_value. Directional elements use weight.
    """
    if elem.get("element_type") == "metric" and elem.get("target_value") is not None:
        return elem["target_value"]
    return elem.get("weight", 0.0)


def _compute_similarity(profile_value: float, generated_value: float) -> float:
    """Compute similarity between two values as 1 - normalized deviation."""
    if profile_value is None or generated_value is None:
        return 0.0
    denom = max(abs(profile_value), EPSILON)
    deviation = abs(generated_value - profile_value) / denom
    return max(0.0, 1.0 - deviation)


def _score_qualitative(generated_text, sample_text, quant_scores=None):
    """Qualitative scoring — implemented in Task 3."""
    raise NotImplementedError("Qualitative scoring implemented in Task 3")
