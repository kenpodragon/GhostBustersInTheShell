"""Integration tests for the full detection pipeline."""
import pytest
from utils.detector import detect_ai_patterns


class TestDetectAIPatterns:
    """Full pipeline integration tests."""

    def test_returns_expected_structure(self, ai_text):
        result = detect_ai_patterns(ai_text)
        assert "overall_score" in result
        assert "sentences" in result
        assert "detected_patterns" in result
        assert "confidence" in result
        assert "genre" in result
        assert "signal_count" in result

    def test_ai_text_scores_above_35(self, ai_text):
        result = detect_ai_patterns(ai_text)
        assert result["overall_score"] > 35

    def test_human_text_scores_below_25(self, human_text):
        result = detect_ai_patterns(human_text)
        assert result["overall_score"] < 25

    def test_short_text_returns_low_confidence(self, short_text):
        result = detect_ai_patterns(short_text)
        low, high = result["confidence"]
        assert (high - low) > 5  # Short text = wide uncertainty

    def test_academic_text_not_over_flagged(self, academic_text):
        result = detect_ai_patterns(academic_text)
        assert result["overall_score"] < 40

    def test_genre_detected(self, academic_text):
        result = detect_ai_patterns(academic_text)
        assert result["genre"] == "academic"

    def test_confidence_bounds(self, ai_text):
        result = detect_ai_patterns(ai_text)
        low, high = result["confidence"]
        assert 0 <= low <= result["overall_score"]
        assert result["overall_score"] <= high <= 100

    def test_returns_3tier_structure(self, ai_text):
        result = detect_ai_patterns(ai_text)
        assert "overall_score" in result
        assert "sentences" in result
        assert "detected_patterns" in result
        assert "confidence" in result
        assert "genre" in result
        assert "signal_count" in result
        assert "tiers" in result
        assert "sentence_score" in result["tiers"]
        assert "paragraph_score" in result["tiers"]
        assert "document_score" in result["tiers"]
        assert "paragraphs" in result

    def test_paragraphs_array_present(self, ai_text_multipar):
        result = detect_ai_patterns(ai_text_multipar)
        assert len(result["paragraphs"]) >= 2
        for para in result["paragraphs"]:
            assert "index" in para
            assert "score" in para
            assert "text" in para
            assert "patterns" in para

    def test_tier_scores_are_numeric(self, ai_text):
        result = detect_ai_patterns(ai_text)
        tiers = result["tiers"]
        assert isinstance(tiers["sentence_score"], (int, float))
        assert isinstance(tiers["paragraph_score"], (int, float))
        assert isinstance(tiers["document_score"], (int, float))

    def test_detail_mode_returns_report(self, ai_text_multipar):
        from utils.detector import detect_ai_patterns_detailed
        result = detect_ai_patterns_detailed(ai_text_multipar)
        assert "report" in result
        report = result["report"]
        assert "tier_breakdown" in report
        assert "score_math" in report
        assert "escalation_traces" in report
        assert "document" in report["tier_breakdown"]
        assert "paragraph" in report["tier_breakdown"]
        assert "sentence" in report["tier_breakdown"]

    def test_escalation_traces_structure(self, ai_text_multipar):
        from utils.detector import detect_ai_patterns_detailed
        result = detect_ai_patterns_detailed(ai_text_multipar)
        traces = result["report"]["escalation_traces"]
        assert isinstance(traces, list)
        if traces:
            trace = traces[0]
            assert "signal" in trace
            assert "levels" in trace
            assert "compounded_severity" in trace

    def test_new_heuristic_patterns_appear(self, ai_text):
        result = detect_ai_patterns(ai_text)
        pattern_names = [p["pattern"] for p in result["detected_patterns"]]
        new_patterns = {"yules_k_very_high", "yules_k_high", "hapax_very_low",
                        "hapax_low", "function_word_high_deviation",
                        "function_word_moderate_deviation", "mattr_low",
                        "mattr_uniform", "zipf_high_deviation",
                        "zipf_moderate_deviation", "compression_very_high",
                        "compression_high", "sentence_opener_ai_heavy",
                        "sentence_opener_ai_moderate", "burrows_delta_high",
                        "burrows_delta_moderate", "burrows_delta_mild",
                        "word_length_uniform", "word_length_medium_cluster",
                        "char_ngram_low_entropy", "char_ngram_moderate_entropy"}
        found_new = set(pattern_names) & new_patterns
        assert len(found_new) >= 1, f"No Phase 2.3 patterns fired. Got: {pattern_names}"
