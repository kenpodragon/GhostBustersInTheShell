"""AI-enhanced voice extraction — runs alongside Python parsing.

Given a document's text and the 65 quantitative element values extracted by Python,
asks AI to produce:
1. Qualitative prompts — voice directives Python can't extract
2. Metric descriptions — natural language interpretation of each quantitative value
3. Discovered patterns — potential new elements not in the current set

The raw AI response is preserved for Phase E research.
"""

MAX_TEXT_CHARS = 20000  # ~4000 words at 5 chars/word

AI_EXTRACTION_PROMPT = """Given this writing sample and its extracted style metrics, analyze the author's voice.

## Writing Sample:
{document_text}

## Extracted Quantitative Metrics:
{element_values}

Analyze the writing voice. For each quantitative metric, describe what that value
means in the context of this specific writing. Also identify qualitative voice
patterns that the metrics cannot capture.

Return ONLY valid JSON:
{{
  "qualitative_prompts": [
    {{"prompt": "concise voice directive (2-3 sentences max)", "confidence": 0.0-1.0}}
  ],
  "metric_descriptions": [
    {{
      "element": "element_name",
      "value": 0.0,
      "description": "what this value means for this writer's style",
      "ai_assessment": "accurate|misleading|insufficient_data"
    }}
  ],
  "discovered_patterns": [
    {{
      "pattern": "description of a pattern not captured by existing metrics",
      "suggested_element_name": "snake_case_name",
      "description": "how this pattern manifests in the writing"
    }}
  ]
}}"""


def _get_provider():
    """Get AI provider using the existing router pattern."""
    from ai_providers.router import _get_provider as router_get_provider, should_use_ai
    if not should_use_ai():
        return None
    return router_get_provider()


def _format_elements(parsed_elements: dict) -> str:
    """Format parsed element dict into name: value lines for the prompt."""
    lines = []
    for name, data in sorted(parsed_elements.items()):
        value = data.get("target_value") or data.get("weight", 0.5)
        # Cast numpy types to plain float
        if hasattr(value, 'item'):
            value = value.item()
        lines.append(f"{name}: {value}")
    return "\n".join(lines)


def extract_voice_with_ai(text: str, parsed_elements: dict) -> dict:
    """Extract voice characteristics using AI alongside Python parsing.

    Args:
        text: The document text to analyze.
        parsed_elements: Dict of element_name -> {category, weight, target_value, ...}
            as returned by generate_voice_profile().

    Returns:
        Dict with keys: status, qualitative_prompts, metric_descriptions,
        discovered_patterns, raw_ai_response, error (if any).
    """
    provider = _get_provider()
    if not provider:
        return {
            "status": "skipped",
            "qualitative_prompts": [],
            "metric_descriptions": [],
            "discovered_patterns": [],
            "raw_ai_response": None,
        }

    # Truncate text to stay within context limits
    truncated_text = text[:MAX_TEXT_CHARS]

    element_values = _format_elements(parsed_elements)

    prompt = AI_EXTRACTION_PROMPT.format(
        document_text=truncated_text,
        element_values=element_values,
    )

    try:
        raw_response = provider._run_cli(prompt)

        return {
            "status": "success",
            "qualitative_prompts": raw_response.get("qualitative_prompts", []),
            "metric_descriptions": raw_response.get("metric_descriptions", []),
            "discovered_patterns": raw_response.get("discovered_patterns", []),
            "raw_ai_response": raw_response,
        }
    except Exception as e:
        return {
            "status": "error",
            "qualitative_prompts": [],
            "metric_descriptions": [],
            "discovered_patterns": [],
            "raw_ai_response": None,
            "error": str(e),
        }
