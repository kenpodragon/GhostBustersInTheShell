"""Tests for 3-category classification (Phase 3.7)."""
import pytest
from utils.heuristics.classification import (
    classify_category,
    CATEGORIES,
    _count_ai_signals,
    _count_human_absence,
    _has_human_tells,
    _compute_confidence,
)
from utils.detector import detect_ai_patterns


class TestClassifyCategory:
    def test_returns_required_keys(self):
        result = {"overall_score": 50, "detected_patterns": []}
        cat = classify_category(result)
        assert "category" in cat
        assert "label" in cat
        assert "subtitle" in cat
        assert "confidence" in cat

    def test_valid_category_values(self):
        result = {"overall_score": 50, "detected_patterns": []}
        cat = classify_category(result)
        assert cat["category"] in ("ghost_written", "ghost_touched", "clean")

    def test_zero_score_is_clean(self):
        result = {"overall_score": 0, "detected_patterns": []}
        cat = classify_category(result)
        assert cat["category"] == "clean"
        assert cat["label"] == "Clean"
        assert cat["subtitle"] == "Human Only"

    def test_low_score_is_clean(self):
        result = {"overall_score": 15, "detected_patterns": []}
        cat = classify_category(result)
        assert cat["category"] == "clean"

    def test_score_20_is_clean(self):
        result = {"overall_score": 20, "detected_patterns": []}
        cat = classify_category(result)
        assert cat["category"] == "clean"

    def test_score_25_with_human_tells_is_clean(self):
        """Score 21-30 should be Clean if 3+ human tells present (absence signals NOT fired)."""
        # No human-absence patterns fired = all human tells present
        result = {"overall_score": 25, "detected_patterns": [
            {"pattern": "buzzword", "detail": "some buzzword"},
        ]}
        cat = classify_category(result)
        assert cat["category"] == "clean"

    def test_score_25_without_human_tells_is_ghost_touched(self):
        """Score 21-30 without enough human tells → Ghost Touched."""
        # Many human-absence patterns = human tells missing
        result = {"overall_score": 25, "detected_patterns": [
            {"pattern": "no_contractions", "detail": ""},
            {"pattern": "no_first_person", "detail": ""},
            {"pattern": "no_specifics", "detail": ""},
            {"pattern": "no_digressions", "detail": ""},
            {"pattern": "buzzword", "detail": ""},
        ]}
        cat = classify_category(result)
        assert cat["category"] == "ghost_touched"

    def test_high_score_is_ghost_written(self):
        result = {"overall_score": 60, "detected_patterns": [
            {"pattern": "buzzword", "detail": ""},
            {"pattern": "ai_phrase", "detail": ""},
        ]}
        cat = classify_category(result)
        assert cat["category"] == "ghost_written"
        assert cat["label"] == "Ghost Written"
        assert cat["subtitle"] == "AI"

    def test_score_45_is_ghost_written(self):
        result = {"overall_score": 45, "detected_patterns": []}
        cat = classify_category(result)
        assert cat["category"] == "ghost_written"

    def test_score_35_weak_human_tells_many_ai_signals_is_ghost_written(self):
        """Score 35-44 with <2 human tells and 3+ AI signals → Ghost Written."""
        result = {"overall_score": 38, "detected_patterns": [
            {"pattern": "buzzword", "detail": ""},
            {"pattern": "ai_phrase", "detail": ""},
            {"pattern": "hedge_word", "detail": ""},
            {"pattern": "ai_transition", "detail": ""},
            {"pattern": "no_contractions", "detail": ""},
            {"pattern": "no_first_person", "detail": ""},
            {"pattern": "no_specifics", "detail": ""},
            {"pattern": "no_digressions", "detail": ""},
            {"pattern": "no_questions_exclamations", "detail": ""},
        ]}
        cat = classify_category(result)
        assert cat["category"] == "ghost_written"

    def test_score_38_with_human_tells_is_ghost_touched(self):
        """Score 35-44 WITH human tells → Ghost Touched (not Ghost Written)."""
        # Few human-absence signals = human tells ARE present
        result = {"overall_score": 38, "detected_patterns": [
            {"pattern": "buzzword", "detail": ""},
            {"pattern": "ai_phrase", "detail": ""},
            {"pattern": "hedge_word", "detail": ""},
        ]}
        cat = classify_category(result)
        assert cat["category"] == "ghost_touched"

    def test_middle_score_is_ghost_touched(self):
        result = {"overall_score": 33, "detected_patterns": [
            {"pattern": "buzzword", "detail": ""},
        ]}
        cat = classify_category(result)
        assert cat["category"] == "ghost_touched"
        assert cat["label"] == "Ghost Touched"
        assert cat["subtitle"] == "Assisted"


class TestConfidence:
    def test_ghost_written_high_confidence(self):
        assert _compute_confidence(65, "ghost_written") == "high"

    def test_ghost_written_medium_confidence(self):
        assert _compute_confidence(52, "ghost_written") == "medium"

    def test_ghost_written_low_confidence(self):
        assert _compute_confidence(46, "ghost_written") == "low"

    def test_clean_high_confidence(self):
        assert _compute_confidence(5, "clean") == "high"

    def test_clean_medium_confidence(self):
        assert _compute_confidence(12, "clean") == "medium"

    def test_clean_low_confidence(self):
        assert _compute_confidence(18, "clean") == "low"

    def test_ghost_touched_medium_confidence(self):
        assert _compute_confidence(33, "ghost_touched") == "medium"

    def test_ghost_touched_low_confidence(self):
        assert _compute_confidence(22, "ghost_touched") == "low"


class TestHelpers:
    def test_count_ai_signals(self):
        patterns = [
            {"pattern": "buzzword", "detail": ""},
            {"pattern": "ai_phrase", "detail": ""},
            {"pattern": "buzzword", "detail": ""},  # duplicate
            {"pattern": "no_contractions", "detail": ""},  # not AI signal
        ]
        assert _count_ai_signals(patterns) == 2

    def test_count_human_absence(self):
        patterns = [
            {"pattern": "no_contractions", "detail": ""},
            {"pattern": "no_first_person", "detail": ""},
            {"pattern": "buzzword", "detail": ""},  # not absence signal
        ]
        assert _count_human_absence(patterns) == 2

    def test_has_human_tells_all_present(self):
        """No absence signals fired = all 6 human tells present."""
        patterns = [{"pattern": "buzzword", "detail": ""}]
        assert _has_human_tells(patterns) == 6

    def test_has_human_tells_none_present(self):
        """All absence signals fired = 0 human tells present."""
        patterns = [
            {"pattern": "no_contractions", "detail": ""},
            {"pattern": "no_first_person", "detail": ""},
            {"pattern": "no_specifics", "detail": ""},
            {"pattern": "no_digressions", "detail": ""},
            {"pattern": "no_questions_exclamations", "detail": ""},
            {"pattern": "low_first_person", "detail": ""},
        ]
        assert _has_human_tells(patterns) == 0


class TestCATEGORIES:
    def test_three_categories_defined(self):
        assert len(CATEGORIES) == 3

    def test_all_categories_have_required_keys(self):
        for key, cat in CATEGORIES.items():
            assert "category" in cat
            assert "label" in cat
            assert "subtitle" in cat
            assert cat["category"] == key


class TestIntegration:
    def test_ai_text_classified_ghost_written(self, ai_text):
        """Full AI text should classify as Ghost Written."""
        result = detect_ai_patterns(ai_text)
        assert "classification" in result
        assert result["classification"]["category"] == "ghost_written"

    def test_human_text_classified_clean(self, human_text):
        """Natural human text should classify as Clean."""
        result = detect_ai_patterns(human_text)
        assert "classification" in result
        assert result["classification"]["category"] == "clean"

    def test_classification_in_detailed_mode(self, ai_text):
        """Classification should also appear in detailed results."""
        from utils.detector import detect_ai_patterns_detailed
        result = detect_ai_patterns_detailed(ai_text)
        assert "classification" in result
        assert result["classification"]["category"] == "ghost_written"

    def test_empty_text_classified_clean(self):
        result = detect_ai_patterns("")
        assert "classification" not in result or result.get("classification", {}).get("category") == "clean"
