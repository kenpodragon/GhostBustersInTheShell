"""Tests for graduated severity system."""
import pytest
from utils.heuristics.severity import classify_severity, apply_severity, compound_across_levels


class TestClassifySeverity:
    """Map instance counts to severity tiers."""

    def test_zero_instances_returns_none(self):
        assert classify_severity(0) is None

    def test_one_instance_returns_caution(self):
        assert classify_severity(1) == "caution"

    def test_two_instances_returns_warning(self):
        assert classify_severity(2) == "warning"

    def test_three_instances_returns_warning(self):
        assert classify_severity(3) == "warning"

    def test_four_instances_returns_strong(self):
        assert classify_severity(4) == "strong"

    def test_ten_instances_returns_strong(self):
        assert classify_severity(10) == "strong"


class TestApplySeverity:
    """Scale a raw score by severity tier."""

    def test_caution_reduces_score(self):
        result = apply_severity(50, "caution")
        assert result == pytest.approx(12.5)  # 50 * 0.25

    def test_warning_moderate_score(self):
        result = apply_severity(50, "warning")
        assert result == pytest.approx(30.0)  # 50 * 0.6

    def test_strong_full_score(self):
        result = apply_severity(50, "strong")
        assert result == pytest.approx(50.0)  # 50 * 1.0

    def test_none_severity_returns_zero(self):
        result = apply_severity(50, None)
        assert result == 0


class TestCompoundAcrossLevels:
    """Cross-level compounding: same signal at multiple levels escalates."""

    def test_single_level_caution_stays_caution(self):
        result = compound_across_levels(["caution"])
        assert result == "caution"

    def test_two_cautions_escalate_to_warning(self):
        result = compound_across_levels(["caution", "caution"])
        assert result == "warning"

    def test_three_cautions_escalate_to_strong(self):
        result = compound_across_levels(["caution", "caution", "caution"])
        assert result == "strong"

    def test_warning_plus_caution_escalates_to_strong(self):
        result = compound_across_levels(["warning", "caution"])
        assert result == "strong"

    def test_any_strong_stays_strong(self):
        result = compound_across_levels(["strong"])
        assert result == "strong"

    def test_empty_returns_none(self):
        result = compound_across_levels([])
        assert result is None


class TestSeverityIntegration:
    """Severity affects actual detection scores."""

    def test_one_buzzword_scores_less_than_four(self):
        from utils.detector import detect_ai_patterns
        one_buzz = "We need to leverage our existing platform."
        four_buzz = (
            "We need to leverage our existing platform to streamline operations, "
            "harness cutting-edge solutions, and foster innovative growth."
        )
        r1 = detect_ai_patterns(one_buzz)
        r4 = detect_ai_patterns(four_buzz)
        assert r4["overall_score"] > r1["overall_score"]
