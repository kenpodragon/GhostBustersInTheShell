"""Tests for enriched analysis response (score_math, document_patterns, pattern attribution)."""
import pytest
from utils.heuristics.scoring import composite_score_detailed


class TestScoreMathBreakdown:
    """composite_score_detailed returns score + math breakdown."""

    def test_returns_dict_with_score_and_math(self):
        result = composite_score_detailed(
            sentence_score=53.8, paragraph_score=53.7, document_score=54.0,
            sentence_signals=5, paragraph_signals=3, document_signals=4,
        )
        assert "score" in result
        assert "score_math" in result
        math = result["score_math"]
        assert "sentence_weighted" in math
        assert "paragraph_weighted" in math
        assert "document_weighted" in math
        assert "convergence_bonus" in math
        assert "cross_tier_bonus" in math
        assert "raw_composite" in math
        assert "final_score" in math

    def test_score_math_values_are_correct(self):
        result = composite_score_detailed(
            sentence_score=60.0, paragraph_score=40.0, document_score=20.0,
            sentence_signals=2, paragraph_signals=1, document_signals=1,
        )
        math = result["score_math"]
        assert math["sentence_weighted"] == 27.0
        assert math["paragraph_weighted"] == 12.0
        assert math["document_weighted"] == 5.0

    def test_score_math_zero_input(self):
        result = composite_score_detailed(
            sentence_score=0, paragraph_score=0, document_score=0,
            sentence_signals=0, paragraph_signals=0, document_signals=0,
        )
        assert result["score"] == 0.0
        assert result["score_math"]["final_score"] == 0.0

    def test_score_matches_original_composite_score(self):
        from utils.heuristics.scoring import composite_score
        args = dict(
            sentence_score=50.0, paragraph_score=45.0, document_score=55.0,
            sentence_signals=4, paragraph_signals=3, document_signals=5,
        )
        original = composite_score(**args)
        detailed = composite_score_detailed(**args)
        assert detailed["score"] == original
