"""Tests for stylometric analysis heuristics."""
import pytest
from utils.heuristics.stylometric import check_burrows_delta


class TestBurrowsDelta:
    """Burrows' Delta measures stylistic distance from a 'human writing' profile.
    AI text should have HIGHER delta (more distant from human profile)."""

    def test_returns_score_and_patterns(self, ai_text):
        score, patterns = check_burrows_delta(ai_text)
        assert isinstance(score, (int, float))
        assert isinstance(patterns, list)

    def test_ai_text_scores_higher(self, ai_text, human_text):
        ai_score, _ = check_burrows_delta(ai_text)
        human_score, _ = check_burrows_delta(human_text)
        assert ai_score >= human_score

    def test_short_text_returns_zero(self, short_text):
        score, _ = check_burrows_delta(short_text)
        assert score == 0

    def test_academic_text_not_false_positive(self, academic_text):
        score, _ = check_burrows_delta(academic_text)
        assert score < 40
