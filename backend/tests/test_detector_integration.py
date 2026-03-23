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
        assert (high - low) > 10

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
