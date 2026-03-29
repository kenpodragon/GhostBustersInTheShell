# tools/format_experiments.py
"""Prompt templates for voice format experiments.

Each experiment defines how to format voice elements into a Claude prompt.
The harness runs each experiment, scores the output, and compares.
"""


def build_self_assessment_prompt(elements_json: str) -> str:
    """E.1: Ask Claude which elements it can control."""
    return f"""Here are 65 quantitative style elements extracted from a specific author's writing.
Each has a name, category, element_type, and target_value.

{elements_json}

For each element, assess:
1. Can you directly control this when writing text? (yes/partially/no)
2. If yes or partially: how would you implement it? Be specific.
3. If no: why not? Is it emergent from other factors?

Return ONLY valid JSON:
{{
  "assessments": [
    {{
      "element": "element_name",
      "controllable": "yes|partially|no",
      "implementation": "how you would target this value",
      "notes": "any caveats or dependencies"
    }}
  ]
}}"""


def build_json_only_prompt(elements_json: str, input_text: str) -> str:
    """E.2: Generate text using raw JSON targets only."""
    return f"""Rewrite the following text to match this author's voice profile.
The profile is defined as quantitative style elements with target values.
Match each target as closely as possible.

Voice Profile (JSON):
{elements_json}

Text to rewrite:
{input_text}

Return ONLY valid JSON:
{{
  "rewritten_text": "your rewritten version",
  "notes": "brief notes on which targets you prioritized"
}}"""


def build_json_enforced_prompt(elements_json: str, input_text: str) -> str:
    """E.2b: JSON targets with enforcement language."""
    return f"""Rewrite the following text. You MUST match the voice profile targets below.
These are hard constraints, not suggestions. After writing, mentally verify
each metric against the targets before returning.

Voice Profile Targets (MANDATORY):
{elements_json}

Text to rewrite:
{input_text}

Return ONLY valid JSON:
{{
  "rewritten_text": "your rewritten version",
  "verification": "brief check of key metrics you targeted"
}}"""


def build_english_only_prompt(english_instructions: str, input_text: str) -> str:
    """E.3a: Current-style English instructions only."""
    return f"""Rewrite the following text to match this author's voice.

Voice instructions:
{english_instructions}

Text to rewrite:
{input_text}

Return ONLY valid JSON:
{{
  "rewritten_text": "your rewritten version"
}}"""


def build_categorized_prompt(
    controllable_json: str,
    english_for_indirect: str,
    input_text: str,
) -> str:
    """E.3b: Hybrid — JSON for controllable, English for indirect."""
    return f"""Rewrite the following text to match this author's voice profile.

## Hard Targets (match these values):
{controllable_json}

## Style Guidance (follow these patterns):
{english_for_indirect}

Text to rewrite:
{input_text}

Return ONLY valid JSON:
{{
  "rewritten_text": "your rewritten version"
}}"""
