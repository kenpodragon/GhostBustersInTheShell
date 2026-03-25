"""Style Brief Generator — translates detection output into rewrite prompts.

Takes AI detection results and builds a targeted, model-specific prompt
that eliminates detected AI signals. Core humanization engine.

Research: docs/research/humanize_generation_research_session12.md
Spec: docs/superpowers/specs/2026-03-24-style-brief-generator-design.md
"""
import re
from utils.heuristics.reference_data import BUZZWORDS, HARD_BAN_FILLER_PHRASES


# Pattern prefix → rewrite instruction.
# Uses prefix matching: "em_dash" matches "em_dash_heavy", "em_dash_elevated", etc.
PATTERN_RULES = {
    "buzzword": "BANNED WORDS (see list below). Replace every one with plain English.",
    "no_contractions": "Use contractions naturally (don't, can't, it's, I've, we're).",
    "low_contractions": "Use contractions naturally (don't, can't, it's, I've, we're).",
    "uniform_length": "Vary sentence lengths dramatically: mix short punchy sentences (<6 words) with long flowing ones (25+).",
    "rule_of_three": "Never list exactly 3 things. Use 2 or 4+.",
    "tricolon": "Never list exactly 3 things. Use 2 or 4+.",
    "ai_transition": "Don't open sentences with Furthermore/Moreover/Additionally/Consequently.",
    "transition_stack": "Don't open sentences with Furthermore/Moreover/Additionally/Consequently.",
    "hedge_word": "Cut hedge words. State things directly instead of hedging.",
    "hedge_cluster": "Cut hedge words. State things directly instead of hedging.",
    "hedge_regular": "Cut hedge words. State things directly instead of hedging.",
    "trailing_participial": "Never end a sentence with an -ing participial phrase.",
    "no_digressions": "Include one brief tangent or personal aside.",
    "few_digressions": "Include one brief tangent or personal aside.",
    "no_irregular_punctuation": "Use at least 1 rhetorical question and 1 exclamation or ellipsis.",
    "no_questions_exclamations": "Use at least 1 rhetorical question and 1 exclamation or ellipsis.",
    "rare_questions_exclamations": "Use at least 1 rhetorical question and 1 exclamation or ellipsis.",
    "self_contained": "Reference something from early in the text later — create a thread.",
    "ai_opening_phrase": "Don't open with 'In today's world' or similar AI cliché openers.",
    "closing_summary": "Don't summarize at the end. End mid-thought or with a question.",
    "em_dash": "NO em dashes (—). Use commas, periods, or parentheses instead.",
    "ai_phrase": "Avoid these AI phrases: {phrases}.",
    "emotional_exposition": "Show emotions through actions and dialogue, not 'felt a pang of' or 'a wave of sadness'.",
    "dual_adjective": "Don't pair adjectives ('rich and complex'). Pick one strong word.",
    "uniform_paragraph": "Vary paragraph lengths — some 1-2 sentences, some 5+.",
    "low_paragraph_variance": "Vary paragraph lengths — some 1-2 sentences, some 5+.",
    "uniform_para": "Vary paragraph lengths — some 1-2 sentences, some 5+.",
    "synonym_treadmill": "Don't rotate fancy synonyms for the same concept. Pick one word and reuse it.",
    "false_dichotomy": "Don't use 'It's not about X, it's about Y' constructions.",
    "not_only_but_also": "Don't use 'not only X but also Y' constructions.",
    "hedging_sandwich": "Don't hedge-bold-hedge. Commit to your point.",
    "confident_declaration": "Don't make sweeping declarations. Be specific with evidence.",
    "circular_repetition": "Don't repeat intro phrases in your conclusion.",
    "rhetorical_question_chain": "Don't chain multiple rhetorical questions in a row.",
    "hollow_informality": "If you use casual markers like 'honestly' or 'look', follow through with something genuinely personal.",
    "front_loaded_description": "Don't front-load heavy descriptions before the action.",
    "it_is_adj_to": "Don't use impersonal 'It is [adjective] to [verb]' constructions.",
    "heavy_structure": "Use fewer bullet points and subheadings. Write in flowing prose.",
    "moderate_structure": "Use fewer bullet points and subheadings. Write in flowing prose.",
    "high_comma_density": "Use fewer commas. Break long sentences into shorter ones instead.",
    "semicolon_overuse": "Avoid semicolons. Use periods instead.",
    "low_vocabulary_richness": "Use more varied vocabulary — don't repeat the same words.",
}

# Always included in every rewrite brief regardless of detected patterns.
ALWAYS_ON_RULES = [
    "Preserve the original point of view exactly. Do not change first/second/third person.",
    "Vary sentence lengths: mix short (<6 words) with long (25+).",
    "Include 1-2 sentence fragments for natural rhythm.",
    "Use at least one parenthetical aside (in parentheses).",
    "Ask at least 1 rhetorical question.",
    "NO em dashes (—). Use commas, periods, or parentheses instead.",
    "Never end a sentence with an -ing participial phrase.",
    "Never list exactly 3 things. Use 2 or 4+.",
    "Reference something from early in the text later — create a callback.",
    "Include one brief digression or tangent.",
    "Name real specifics (companies, dates, numbers) instead of vague generalities.",
]

TONE_REFERENCES = {
    "academic": "Write like a sharp grad student explaining to a peer, not a textbook.",
    "casual": "Write like you're texting a friend who's also an expert.",
    "business": "Write like a direct memo, not a consultant's slide deck.",
    "creative": "Write like you're telling a story to one person at a bar.",
    "literary": "Write like you're telling a story to one person at a bar.",
    "memoir": "Write like you're remembering, not reporting.",
    "poetry": "Write with raw emotional honesty, not polished performance.",
    "resume": "Write with confident specifics, not corporate buzzwords.",
    "cover_letter": "Write with confident specifics, not corporate buzzwords.",
    "general": "Write like a smart person talking, not a smart person writing.",
}


def map_patterns_to_rules(patterns: list[dict]) -> list[str]:
    """Map detected pattern names to rewrite instructions using prefix matching.

    Deduplicates: if multiple patterns map to the same instruction, it appears once.
    Skips patterns not in PATTERN_RULES (unknown or informational-only like no_first_person).
    """
    seen_instructions = set()
    rules = []

    for p in patterns:
        pattern_name = p.get("pattern", "")
        # Try exact match first, then prefix match
        instruction = PATTERN_RULES.get(pattern_name)
        if not instruction:
            # Prefix match: find longest prefix key that matches
            for key in sorted(PATTERN_RULES.keys(), key=len, reverse=True):
                if pattern_name.startswith(key):
                    instruction = PATTERN_RULES[key]
                    break
        if instruction and instruction not in seen_instructions:
            # Handle template instructions with detail data
            if "{phrases}" in instruction:
                detail = p.get("detail", "")
                phrases = re.findall(r'"([^"]+)"', detail)
                if phrases:
                    instruction = instruction.replace("{phrases}", ", ".join(phrases))
                else:
                    instruction = instruction.replace("{phrases}", detail)
            seen_instructions.add(instruction)
            rules.append(instruction)

    return rules


def build_banned_words(detection_result: dict, voice_profile_id: int = None) -> list[str]:
    """Build a merged, deduplicated banned word list.

    Sources:
    1. Global BUZZWORDS set from reference_data.py
    2. Multi-word filler phrases from reference_data.py
    3. Buzzwords actually found in this text (from detection patterns)
    4. Voice profile banned words from DB (if voice_profile_id provided)
    """
    banned = set(BUZZWORDS)
    banned.update(HARD_BAN_FILLER_PHRASES)

    # Extract specific buzzwords found in detection
    for p in detection_result.get("patterns", []):
        if p.get("pattern") == "buzzword":
            detail = p.get("detail", "")
            match = re.search(r"'([^']+)'", detail)
            if match:
                banned.add(match.group(1).lower())

    # Voice profile banned words (from rules_json in voice_profiles table)
    if voice_profile_id:
        try:
            import json as _json
            from db import query_one
            profile = query_one(
                "SELECT rules_json FROM voice_profiles WHERE id = %s",
                (voice_profile_id,)
            )
            if profile and profile.get("rules_json"):
                rules = profile["rules_json"]
                if isinstance(rules, str):
                    rules = _json.loads(rules)
                for word in rules.get("banned_words", []):
                    banned.add(word.strip().lower())
        except Exception:
            pass

    return sorted(banned)


def get_tone_reference(genre: str) -> str:
    """Get a tone guidance string for the detected genre."""
    if not genre:
        return TONE_REFERENCES["general"]
    return TONE_REFERENCES.get(genre, TONE_REFERENCES["general"])


def _get_style_example(voice_profile_id: int = None) -> str:
    """Get a style example paragraph for Gemini prompts.

    Pulls from voice profile if available, otherwise returns built-in default.
    """
    if voice_profile_id:
        try:
            import json as _json
            from db import query_one
            profile = query_one(
                "SELECT rules_json FROM voice_profiles WHERE id = %s",
                (voice_profile_id,)
            )
            if profile and profile.get("rules_json"):
                rules = profile["rules_json"]
                if isinstance(rules, str):
                    rules = _json.loads(rules)
                example = rules.get("style_example", "")
                if example:
                    return example
        except Exception:
            pass

    return (
        "I didn't set out to write about sleep deprivation. It started because my "
        "neighbor — Greg, retired electrician, six cats — mentioned he hadn't slept "
        "more than four hours a night since 2019. That's wild, right? The CDC says "
        "a third of Americans don't get enough sleep, but hearing Greg say it while "
        "feeding Whiskers at 6am hit different. (He named all six cats Whiskers. "
        "Don't ask.) Anyway, turns out the research on this is both fascinating and "
        "terrifying."
    )


def generate_style_brief(
    detection_result: dict,
    voice_profile_id: int = None,
    model: str = "claude",
    is_second_pass: bool = False,
    comment: str = None,
) -> str:
    """Build a complete rewrite prompt from detection output.

    detection_result: dict from detect_ai_patterns() — expects keys:
        "overall_score", "patterns" (list of {"pattern": str, "detail": str}),
        "sentences", "classification". Genre from detection_result.get("genre").

    Returns a prompt string with {text} placeholder for the original text.
    """
    patterns = detection_result.get("patterns", [])
    genre = detection_result.get("genre") or "general"

    # Build components
    detected_rules = map_patterns_to_rules(patterns)
    banned = build_banned_words(detection_result, voice_profile_id)
    tone = get_tone_reference(genre)

    # Voice profile extra rules (from rules_json)
    voice_rules_text = ""
    if voice_profile_id:
        try:
            import json as _json
            from db import query_one
            profile = query_one(
                "SELECT rules_json FROM voice_profiles WHERE id = %s",
                (voice_profile_id,)
            )
            if profile and profile.get("rules_json"):
                rules = profile["rules_json"]
                if isinstance(rules, str):
                    rules = _json.loads(rules)
                style_rules = []
                for key, value in rules.items():
                    if key == "banned_words":
                        continue
                    if isinstance(value, list):
                        style_rules.extend(str(v) for v in value)
                    elif isinstance(value, str):
                        style_rules.append(value)
                if style_rules:
                    voice_rules_text = "\n".join(f"- {r}" for r in style_rules[:20])
        except Exception:
            pass

    # Assemble the brief
    if is_second_pass:
        sections = [
            "You are rewriting this text to fix remaining AI detection signals.",
            "This is a REVISION. The previous rewrite still has these issues:",
        ]
        if detected_rules:
            for rule in detected_rules:
                sections.append(f"- {rule}")
        else:
            sections.append("- General AI-like tone")
        sections.extend([
            "",
            "Fix ONLY these issues while preserving everything else that already sounds natural.",
            "Preserve the original point of view exactly.",
        ])
    else:
        sections = [
            "You are a text humanizer. Rewrite this text to eliminate AI detection signals while preserving the meaning.",
            "",
            f"TONE: {tone}",
            "",
            "STYLE RULES (follow ALL of these):",
        ]
        for i, rule in enumerate(ALWAYS_ON_RULES, 1):
            sections.append(f"{i}. {rule}")

        if detected_rules:
            sections.append("")
            sections.append("ADDITIONAL FIXES (these specific problems were detected):")
            for rule in detected_rules:
                sections.append(f"- {rule}")

    # Banned words (both passes) — limit to 80 to avoid prompt bloat
    banned_sample = banned[:80]
    sections.append("")
    sections.append(f"BANNED WORDS (never use these): {', '.join(banned_sample)}")

    # Voice profile rules
    if voice_rules_text:
        sections.append("")
        sections.append("VOICE PROFILE RULES (highest priority — follow these above all else):")
        sections.append(voice_rules_text)

    # Style example for Gemini
    if model.lower() in ("gemini", "gemini-flash", "gemini-pro"):
        example = _get_style_example(voice_profile_id)
        sections.append("")
        sections.append("STYLE EXAMPLE (match this voice and rhythm):")
        sections.append(f'"""{example}"""')

    # Output format
    sections.extend([
        "",
        'Return ONLY valid JSON: {{"rewritten_text": "the full rewritten text", "changes": [{{"original": "phrase", "rewritten": "phrase", "reason": "why"}}]}}',
        "",
        "Text to rewrite:",
        "---",
        "{text}",
        "---",
    ])

    brief = "\n".join(sections)

    if comment:
        brief += f"\n\n## USER INSTRUCTIONS (highest priority)\n{comment}\n"

    return brief
