"""Tests for lexical analysis heuristics."""
import pytest
from utils.heuristics.lexical import (
    check_yules_k, check_hapax_legomena,
    check_function_word_deviation, check_mattr,
)


class TestYulesK:
    """Yule's K measures vocabulary constancy. AI text has HIGHER K (more repetitive)."""

    def test_returns_score_and_patterns(self, ai_text):
        score, patterns = check_yules_k(ai_text)
        assert isinstance(score, (int, float))
        assert isinstance(patterns, list)

    def test_ai_text_scores_higher(self, ai_text, human_text):
        ai_score, _ = check_yules_k(ai_text)
        human_score, _ = check_yules_k(human_text)
        assert ai_score >= human_score

    def test_short_text_returns_zero(self, short_text):
        score, _ = check_yules_k(short_text)
        assert score == 0

    def test_pattern_includes_k_value(self, ai_text):
        score, patterns = check_yules_k(ai_text)
        if score > 0:
            assert any("yules_k" in p.get("pattern", "") for p in patterns)


class TestHapaxLegomena:
    """Hapax ratio = words used exactly once / total unique words.
    Humans use MORE hapax legomena (one-off words)."""

    def test_returns_score_and_patterns(self, ai_text):
        score, patterns = check_hapax_legomena(ai_text)
        assert isinstance(score, (int, float))
        assert isinstance(patterns, list)

    def test_ai_text_scores_higher(self, ai_text, human_text):
        ai_score, _ = check_hapax_legomena(ai_text)
        human_score, _ = check_hapax_legomena(human_text)
        assert ai_score >= human_score

    def test_short_text_returns_zero(self, short_text):
        score, _ = check_hapax_legomena(short_text)
        assert score == 0


class TestFunctionWordDeviation:
    """AI text deviates from natural function word distributions."""

    def test_returns_score_and_patterns(self, ai_text):
        score, patterns = check_function_word_deviation(ai_text)
        assert isinstance(score, (int, float))
        assert isinstance(patterns, list)

    def test_ai_text_scores_higher(self, ai_text, human_text):
        ai_score, _ = check_function_word_deviation(ai_text)
        human_score, _ = check_function_word_deviation(human_text)
        assert ai_score >= human_score

    def test_short_text_returns_zero(self, short_text):
        score, _ = check_function_word_deviation(short_text)
        assert score == 0

    def test_pattern_shows_deviation(self, ai_text):
        score, patterns = check_function_word_deviation(ai_text)
        if score > 0:
            assert any("function_word" in p.get("pattern", "") for p in patterns)


class TestMATTR:
    """Moving Average TTR — windowed vocabulary richness.
    AI text has more CONSISTENT (less varied) MATTR across windows."""

    def test_returns_score_and_patterns(self, ai_text):
        score, patterns = check_mattr(ai_text)
        assert isinstance(score, (int, float))
        assert isinstance(patterns, list)

    def test_ai_text_scores_higher(self, ai_text, human_text):
        ai_score, _ = check_mattr(ai_text)
        human_score, _ = check_mattr(human_text)
        assert ai_score >= human_score

    def test_short_text_returns_zero(self, short_text):
        score, _ = check_mattr(short_text)
        assert score == 0
