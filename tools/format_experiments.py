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

IMPORTANT: Your rewritten text MUST be at least 600 words. Expand and elaborate
on the ideas in the source text to reach this length while maintaining the voice profile.

Voice Profile (JSON):
{elements_json}

Text to rewrite:
{input_text}

Return ONLY valid JSON:
{{
  "rewritten_text": "your rewritten version (minimum 600 words)",
  "notes": "brief notes on which targets you prioritized"
}}"""


def build_json_enforced_prompt(elements_json: str, input_text: str) -> str:
    """E.2b: JSON targets with enforcement language."""
    return f"""Rewrite the following text. You MUST match the voice profile targets below.
These are hard constraints, not suggestions. After writing, mentally verify
each metric against the targets before returning.

IMPORTANT: Your rewritten text MUST be at least 600 words. Expand and elaborate
on the ideas in the source text to reach this length while maintaining the voice profile.

Voice Profile Targets (MANDATORY):
{elements_json}

Text to rewrite:
{input_text}

Return ONLY valid JSON:
{{
  "rewritten_text": "your rewritten version (minimum 600 words)",
  "verification": "brief check of key metrics you targeted"
}}"""


def build_english_only_prompt(english_instructions: str, input_text: str) -> str:
    """E.3a: Current-style English instructions only."""
    return f"""Rewrite the following text to match this author's voice.

IMPORTANT: Your rewritten text MUST be at least 600 words. Expand and elaborate
on the ideas in the source text to reach this length while maintaining the voice.

Voice instructions:
{english_instructions}

Text to rewrite:
{input_text}

Return ONLY valid JSON:
{{
  "rewritten_text": "your rewritten version (minimum 600 words)"
}}"""


def build_categorized_prompt(
    controllable_json: str,
    english_for_indirect: str,
    input_text: str,
) -> str:
    """E.3b: Hybrid — JSON for controllable, English for indirect."""
    return f"""Rewrite the following text to match this author's voice profile.

IMPORTANT: Your rewritten text MUST be at least 600 words. Expand and elaborate
on the ideas in the source text to reach this length while maintaining the voice profile.

## Hard Targets (match these values):
{controllable_json}

## Style Guidance (follow these patterns):
{english_for_indirect}

Text to rewrite:
{input_text}

Return ONLY valid JSON:
{{
  "rewritten_text": "your rewritten version (minimum 600 words)"
}}"""


# ---------------------------------------------------------------------------
# E.4: Targeted enforcement for low-fidelity elements
# ---------------------------------------------------------------------------

TARGETED_ENFORCEMENT_BLOCK = """
## MANDATORY Style Fingerprint Rules

These specific patterns are NON-NEGOTIABLE. The author's voice depends on them.
Verify each one before returning your text.

1. **Em dashes (—)**: Include 1-2 em dashes. Use them for asides or emphasis — like this.
2. **Ellipses (...)**: Include 1-2 ellipses. Use them for trailing thoughts or pauses... like so.
3. **Exclamation**: Exactly 1 sentence should end with an exclamation mark!
4. **First person**: Use first-person pronouns (I, me, my, we, our) approximately 10-12 times
   throughout the text. The author writes from personal experience.
5. **Quotes**: Include 2-3 short direct quotes or cited phrases in quotation marks.
6. **Single-sentence paragraphs**: About 30% of your paragraphs should be just one sentence.
   Use them for emphasis or transitions.
7. **Paragraph variety**: Mix long analytical paragraphs (8-20 sentences) with short punchy ones
   (1-2 sentences). Average around 5-6 sentences per paragraph overall.
8. **Analytical tone**: Write 80% analytical, 20% narrative/anecdotal. Lead with analysis
   but weave in brief personal stories or examples.
"""


def build_targeted_enforcement_prompt(
    elements_json: str,
    input_text: str,
) -> str:
    """E.4: Best format (JSON-enforced) + targeted enforcement for problem elements."""
    return f"""Rewrite the following text. You MUST match the voice profile targets below.
These are hard constraints, not suggestions. After writing, mentally verify
each metric against the targets before returning.

IMPORTANT: Your rewritten text MUST be at least 600 words. Expand and elaborate
on the ideas in the source text to reach this length while maintaining the voice profile.

Voice Profile Targets (MANDATORY):
{elements_json}
{TARGETED_ENFORCEMENT_BLOCK}
Text to rewrite:
{input_text}

Return ONLY valid JSON:
{{
  "rewritten_text": "your rewritten version (minimum 600 words)",
  "verification": "count of: em dashes, ellipses, exclamations, first-person pronouns, quotes, single-sentence paragraphs"
}}"""


def build_hybrid_targeted_prompt(
    controllable_json: str,
    english_for_indirect: str,
    input_text: str,
) -> str:
    """E.4b: Hybrid format + targeted enforcement for problem elements."""
    return f"""Rewrite the following text to match this author's voice profile.

IMPORTANT: Your rewritten text MUST be at least 600 words. Expand and elaborate
on the ideas in the source text to reach this length while maintaining the voice profile.

## Hard Targets (match these values):
{controllable_json}

## Style Guidance (follow these patterns):
{english_for_indirect}
{TARGETED_ENFORCEMENT_BLOCK}
Text to rewrite:
{input_text}

Return ONLY valid JSON:
{{
  "rewritten_text": "your rewritten version (minimum 600 words)",
  "verification": "count of: em dashes, ellipses, exclamations, first-person pronouns, quotes, single-sentence paragraphs"
}}"""
