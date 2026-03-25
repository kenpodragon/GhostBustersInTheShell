"""Tests for the style brief generator."""
import pytest
from utils.style_brief import PATTERN_RULES, ALWAYS_ON_RULES, TONE_REFERENCES, map_patterns_to_rules
from utils.style_brief import build_banned_words, get_tone_reference


class TestPatternRules:
    """Test the pattern-to-rule mapping."""

    def test_buzzword_pattern_maps_to_rule(self):
        patterns = [{"pattern": "buzzword", "detail": "AI-typical word: 'leverage'"}]
        rules = map_patterns_to_rules(patterns)
        assert any("plain English" in r.lower() or "banned" in r.lower() for r in rules)

    def test_uniform_length_maps_to_vary_sentences(self):
        patterns = [{"pattern": "uniform_length", "detail": "..."}]
        rules = map_patterns_to_rules(patterns)
        assert any("sentence length" in r.lower() or "vary" in r.lower() for r in rules)

    def test_prefix_matching_catches_variants(self):
        for variant in ["em_dash_heavy", "em_dash_elevated"]:
            rules = map_patterns_to_rules([{"pattern": variant, "detail": "..."}])
            assert any("em dash" in r.lower() for r in rules), f"{variant} should match em dash rule"

    def test_ai_opening_phrase_variants(self):
        for variant in ["ai_opening_phrase", "ai_opening_phrases", "ai_opening_phrases_heavy"]:
            rules = map_patterns_to_rules([{"pattern": variant, "detail": "..."}])
            assert len(rules) > 0, f"{variant} should produce a rule"

    def test_duplicate_patterns_produce_single_rule(self):
        patterns = [
            {"pattern": "em_dash_heavy", "detail": "..."},
            {"pattern": "em_dash_elevated", "detail": "..."},
        ]
        rules = map_patterns_to_rules(patterns)
        em_dash_rules = [r for r in rules if "em dash" in r.lower()]
        assert len(em_dash_rules) == 1

    def test_unknown_pattern_produces_no_rule(self):
        patterns = [{"pattern": "some_unknown_thing", "detail": "..."}]
        rules = map_patterns_to_rules(patterns)
        assert len(rules) == 0

    def test_no_first_person_not_mapped(self):
        patterns = [{"pattern": "no_first_person", "detail": "..."}]
        rules = map_patterns_to_rules(patterns)
        assert len(rules) == 0


class TestAlwaysOnRules:
    def test_always_on_rules_not_empty(self):
        assert len(ALWAYS_ON_RULES) >= 10

    def test_preserve_pov_is_first_rule(self):
        assert "point of view" in ALWAYS_ON_RULES[0].lower() or "pov" in ALWAYS_ON_RULES[0].lower()


class TestToneReferences:
    def test_all_genres_have_tone(self):
        for genre in ["academic", "casual", "business", "creative", "literary", "memoir", "general"]:
            assert genre in TONE_REFERENCES, f"Missing tone for {genre}"


class TestBuildBannedWords:
    def test_includes_detected_buzzwords(self):
        detection = {
            "patterns": [
                {"pattern": "buzzword", "detail": "AI-typical word: 'leverage'"},
                {"pattern": "buzzword", "detail": "AI-typical word: 'synergy'"},
            ]
        }
        banned = build_banned_words(detection)
        assert "leverage" in banned
        assert "synergy" in banned

    def test_includes_global_buzzwords(self):
        detection = {"patterns": []}
        banned = build_banned_words(detection)
        assert "delve" in banned
        assert "holistic" in banned

    def test_no_duplicates(self):
        detection = {"patterns": [{"pattern": "buzzword", "detail": "AI-typical word: 'delve'"}]}
        banned = build_banned_words(detection)
        assert isinstance(banned, list)
        assert len(banned) == len(set(banned))

    def test_result_is_sorted(self):
        detection = {"patterns": []}
        banned = build_banned_words(detection)
        assert banned == sorted(banned)


class TestGetToneReference:
    def test_known_genre_returns_tone(self):
        tone = get_tone_reference("academic")
        assert "grad student" in tone.lower()

    def test_unknown_genre_returns_general(self):
        tone = get_tone_reference("unknown_genre")
        assert tone == TONE_REFERENCES["general"]

    def test_none_genre_returns_general(self):
        tone = get_tone_reference(None)
        assert tone == TONE_REFERENCES["general"]


from utils.style_brief import generate_style_brief


class TestGenerateStyleBrief:
    def _make_detection(self, patterns=None, score=45, genre="general"):
        return {
            "overall_score": score,
            "patterns": patterns or [],
            "sentences": [],
            "classification": {"category": "ghost_written"},
            "genre": genre,
        }

    def test_returns_string(self):
        result = generate_style_brief(self._make_detection())
        assert isinstance(result, str)
        assert len(result) > 100

    def test_includes_always_on_rules(self):
        brief = generate_style_brief(self._make_detection())
        assert "point of view" in brief.lower()
        assert "em dash" in brief.lower()
        assert "fragment" in brief.lower()

    def test_includes_banned_words(self):
        brief = generate_style_brief(self._make_detection())
        assert "BANNED WORDS" in brief
        assert "delve" in brief.lower()

    def test_includes_tone_reference(self):
        brief = generate_style_brief(self._make_detection(genre="academic"))
        assert "grad student" in brief.lower()

    def test_detected_patterns_add_extra_rules(self):
        patterns = [{"pattern": "synonym_treadmill", "detail": "2 synonym clusters"}]
        brief = generate_style_brief(self._make_detection(patterns=patterns))
        assert "synonym" in brief.lower()

    def test_includes_text_placeholder(self):
        brief = generate_style_brief(self._make_detection())
        assert "{text}" in brief

    def test_second_pass_is_targeted(self):
        patterns = [{"pattern": "hedge_cluster", "detail": "4 consecutive hedges"}]
        brief = generate_style_brief(self._make_detection(patterns=patterns), is_second_pass=True)
        assert "revision" in brief.lower()
        assert "hedge" in brief.lower()

    def test_gemini_includes_style_example(self):
        brief = generate_style_brief(self._make_detection(), model="gemini")
        assert "STYLE EXAMPLE" in brief

    def test_claude_no_style_example(self):
        brief = generate_style_brief(self._make_detection(), model="claude")
        assert "STYLE EXAMPLE" not in brief

    def test_returns_valid_json_instruction(self):
        brief = generate_style_brief(self._make_detection())
        assert "rewritten_text" in brief
        assert "JSON" in brief
