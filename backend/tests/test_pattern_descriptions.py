"""Tests for pattern_descriptions module."""
import pytest
from utils.heuristics.pattern_descriptions import PATTERN_DESCRIPTIONS, get_pattern_info

SENTENCE_PATTERNS = [
    "buzzword", "uniform_length", "hedge_word", "ai_transition",
    "not_only_but_also", "it_is_adj_to", "rule_of_three", "hedging_sandwich",
    "front_loaded_description", "dual_adjective_pair", "trailing_participial",
    "confident_declaration", "false_dichotomy", "emotional_exposition",
    "ai_phrase", "ai_opening_phrase",
]

PARAGRAPH_PATTERNS = [
    "para_uniform_sentences", "para_low_vocab", "uniform_paragraphs",
    "low_paragraph_variance", "uniform_para_sentences",
]

DOCUMENT_PATTERNS = [
    "mid_range_readability", "uniform_reading_ease", "no_contractions",
    "low_contractions", "no_first_person", "low_first_person",
    "high_passive_voice", "elevated_passive_voice", "high_adverb_density",
    "elevated_adverb_density", "ai_intensifiers", "no_specifics",
    "low_specifics", "high_comma_density", "semicolon_overuse",
    "no_irregular_punctuation", "hedge_cluster", "hedge_regular_spacing",
    "transition_stacks", "synonym_treadmill", "emoji_overuse",
    "elevated_emoji", "sensory_checklist", "sensory_rotation",
    "self_contained_paragraphs", "rhetorical_question_chain",
    "circular_repetition", "hollow_informality", "as_you_know_exposition",
    "tricolon_density", "buzzword_density", "low_vocabulary_richness",
    "em_dash_heavy", "em_dash_elevated", "ai_opening_phrases",
    "ai_opening_phrases_heavy", "closing_summary", "closing_summary_heavy",
    "no_questions_exclamations", "rare_questions_exclamations",
    "oxford_comma_perfect_consistency", "heavy_structure",
    "moderate_structure", "no_digressions", "few_digressions",
    "consensus_middle", "consensus_middle_strong",
]


def test_known_pattern_lookup():
    """Known pattern returns correct display_name and non-empty description."""
    result = get_pattern_info("buzzword")
    assert result["name"] == "buzzword"
    assert isinstance(result["display_name"], str) and result["display_name"]
    assert isinstance(result["description"], str) and result["description"]


def test_unknown_pattern_fallback():
    """Unknown pattern returns name as display_name and empty description."""
    result = get_pattern_info("nonexistent_pattern_xyz")
    assert result["name"] == "nonexistent_pattern_xyz"
    assert result["display_name"] == "nonexistent_pattern_xyz"
    assert result["description"] == ""


def test_sentence_patterns_all_have_descriptions():
    """All sentence-level patterns have entries with non-empty display_name and description."""
    for pattern in SENTENCE_PATTERNS:
        assert pattern in PATTERN_DESCRIPTIONS, f"Missing sentence pattern: {pattern}"
        info = PATTERN_DESCRIPTIONS[pattern]
        assert info.get("display_name"), f"Empty display_name for: {pattern}"
        assert info.get("description"), f"Empty description for: {pattern}"


def test_document_patterns_all_have_descriptions():
    """All document-level patterns have entries with non-empty display_name and description."""
    for pattern in DOCUMENT_PATTERNS:
        assert pattern in PATTERN_DESCRIPTIONS, f"Missing document pattern: {pattern}"
        info = PATTERN_DESCRIPTIONS[pattern]
        assert info.get("display_name"), f"Empty display_name for: {pattern}"
        assert info.get("description"), f"Empty description for: {pattern}"


def test_paragraph_patterns_all_have_descriptions():
    """All paragraph-level patterns have entries with non-empty display_name and description."""
    for pattern in PARAGRAPH_PATTERNS:
        assert pattern in PATTERN_DESCRIPTIONS, f"Missing paragraph pattern: {pattern}"
        info = PATTERN_DESCRIPTIONS[pattern]
        assert info.get("display_name"), f"Empty display_name for: {pattern}"
        assert info.get("description"), f"Empty description for: {pattern}"


def test_return_dict_shape():
    """get_pattern_info always returns dict with exactly the keys: name, display_name, description."""
    expected_keys = {"name", "display_name", "description"}
    for pattern in SENTENCE_PATTERNS[:3] + PARAGRAPH_PATTERNS[:2] + DOCUMENT_PATTERNS[:3]:
        result = get_pattern_info(pattern)
        assert set(result.keys()) == expected_keys, f"Wrong keys for: {pattern}"
    # Also test unknown
    result = get_pattern_info("unknown_xyz")
    assert set(result.keys()) == expected_keys
