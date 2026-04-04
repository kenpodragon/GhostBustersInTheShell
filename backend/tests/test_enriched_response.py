"""Tests for enriched analysis response (score_math, document_patterns, pattern attribution)."""
import pytest
from utils.heuristics.scoring import composite_score_detailed
from utils.detector import detect_ai_patterns


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


class TestEnrichedAnalyzeResponse:
    SAMPLE_AI_TEXT = (
        "In the rapidly evolving landscape of technology, it is essential to consider "
        "the multifaceted implications of artificial intelligence. Furthermore, the "
        "transformative potential of these innovations cannot be overstated. "
        "This paradigm shift represents a fundamental change in how we approach "
        "complex challenges.\n\n"
        "Moreover, organizations must leverage synergies to optimize their strategic "
        "initiatives. It is worth noting that these developments have far-reaching "
        "consequences for stakeholders across various sectors."
    )

    def test_response_has_score_math(self):
        result = detect_ai_patterns(self.SAMPLE_AI_TEXT)
        assert "score_math" in result["tiers"]
        math = result["tiers"]["score_math"]
        for key in ["sentence_weighted", "paragraph_weighted", "document_weighted", "convergence_bonus", "cross_tier_bonus", "final_score"]:
            assert key in math

    def test_response_has_document_patterns(self):
        result = detect_ai_patterns(self.SAMPLE_AI_TEXT)
        assert "document_patterns" in result
        assert isinstance(result["document_patterns"], list)
        if result["document_patterns"]:
            dp = result["document_patterns"][0]
            assert "name" in dp
            assert "display_name" in dp
            assert "description" in dp
            assert "severity" in dp

    def test_paragraphs_have_enriched_patterns(self):
        result = detect_ai_patterns(self.SAMPLE_AI_TEXT)
        assert len(result["paragraphs"]) > 0
        for para in result["paragraphs"]:
            for p in para["patterns"]:
                assert "name" in p
                assert "display_name" in p
                assert "description" in p

    def test_sentences_have_enriched_patterns(self):
        result = detect_ai_patterns(self.SAMPLE_AI_TEXT)
        sentences_with_patterns = [s for s in result["sentences"] if s["patterns"]]
        if sentences_with_patterns:
            p = sentences_with_patterns[0]["patterns"][0]
            assert "name" in p
            assert "display_name" in p
            assert "description" in p

    def test_paragraphs_have_sentence_count(self):
        result = detect_ai_patterns(self.SAMPLE_AI_TEXT)
        for para in result["paragraphs"]:
            assert "sentence_count" in para
            assert isinstance(para["sentence_count"], int)

    def test_paragraphs_have_sentences(self):
        result = detect_ai_patterns(self.SAMPLE_AI_TEXT)
        for para in result["paragraphs"]:
            assert "sentences" in para
            assert isinstance(para["sentences"], list)
            if para["sentences"]:
                s = para["sentences"][0]
                assert "text" in s
                assert "score" in s
                assert "patterns" in s

    def test_backward_compat_flat_sentences_still_present(self):
        result = detect_ai_patterns(self.SAMPLE_AI_TEXT)
        assert "sentences" in result
        assert isinstance(result["sentences"], list)
        assert len(result["sentences"]) > 0

    def test_score_math_final_matches_overall(self):
        result = detect_ai_patterns(self.SAMPLE_AI_TEXT)
        assert result["tiers"]["score_math"]["final_score"] == result["overall_score"]
