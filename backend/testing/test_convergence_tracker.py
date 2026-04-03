"""Tests for convergence_tracker — Welford's algorithm + convergence detection."""
import pytest
from utils.convergence_tracker import ElementTracker, ConvergenceComputer, COMPLETENESS_TIERS


class TestElementTracker:
    """Test incremental stats via Welford's algorithm."""

    def test_single_value(self):
        t = ElementTracker("test_element")
        t.update(0.5)
        assert t.count == 1
        assert t.mean == pytest.approx(0.5)
        assert t.cv == 0.0
        assert t.converged is False

    def test_two_values_mean(self):
        t = ElementTracker("test_element")
        t.update(0.4)
        t.update(0.6)
        assert t.count == 2
        assert t.mean == pytest.approx(0.5)

    def test_stable_values_converge(self):
        """3+ consecutive values with <2% rolling delta should converge."""
        t = ElementTracker("test_element")
        for v in [0.50, 0.51, 0.49, 0.50]:
            t.update(v)
        t.update(0.501)
        t.update(0.500)
        t.update(0.499)
        assert t.converged is True

    def test_volatile_values_do_not_converge(self):
        t = ElementTracker("test_element")
        for v in [0.1, 0.9, 0.2, 0.8, 0.3, 0.7]:
            t.update(v)
        assert t.converged is False

    def test_near_zero_element_convergence(self):
        """Near-zero elements use absolute delta < 0.001."""
        t = ElementTracker("archaic_vocabulary_rate")
        for _ in range(5):
            t.update(0.001)
        t.update(0.0011)
        t.update(0.0009)
        t.update(0.001)
        assert t.converged is True

    def test_near_zero_does_not_converge_with_jumps(self):
        t = ElementTracker("test_element")
        t.update(0.0)
        t.update(0.0)
        t.update(0.05)
        assert t.converged is False

    def test_convergence_resets_on_instability(self):
        t = ElementTracker("test_element")
        for v in [0.50, 0.50, 0.50, 0.501, 0.500, 0.499]:
            t.update(v)
        assert t.converged is True
        t.update(0.80)
        assert t.converged is False
        assert t.consecutive_stable == 0

    def test_cv_calculation(self):
        t = ElementTracker("test_element")
        values = [10.0, 12.0, 11.0, 10.5, 11.5]
        for v in values:
            t.update(v)
        import statistics
        expected_mean = statistics.mean(values)
        expected_std = statistics.stdev(values)
        expected_cv = expected_std / expected_mean
        assert t.mean == pytest.approx(expected_mean)
        assert t.cv == pytest.approx(expected_cv, rel=0.01)


class TestConvergenceComputer:
    """Test aggregate completeness computation."""

    def test_empty_returns_zero(self):
        cc = ConvergenceComputer()
        result = cc.compute_completeness()
        assert result["pct"] == 0
        assert result["tier"] == "starter"

    def test_bronze_tier(self):
        cc = ConvergenceComputer()
        for i in range(33):
            t = ElementTracker(f"el_{i}")
            t._converged = True
            cc.add_tracker(t)
        for i in range(31):
            t = ElementTracker(f"el_nc_{i}")
            cc.add_tracker(t)
        result = cc.compute_completeness(total_words=100000)
        assert result["tier"] == "bronze"
        assert result["pct"] == 51

    def test_gold_tier(self):
        cc = ConvergenceComputer()
        for i in range(60):
            t = ElementTracker(f"el_{i}")
            t._converged = True
            cc.add_tracker(t)
        for i in range(4):
            t = ElementTracker(f"el_nc_{i}")
            cc.add_tracker(t)
        result = cc.compute_completeness(total_words=100000)
        assert result["tier"] == "gold"
        assert result["pct"] == 93

    def test_categories_breakdown(self):
        cc = ConvergenceComputer()
        t1 = ElementTracker("flesch_reading_ease")
        t1._converged = True
        t1._category = "readability"
        cc.add_tracker(t1)
        t2 = ElementTracker("em_dash_usage")
        t2._category = "idiosyncratic"
        cc.add_tracker(t2)
        result = cc.compute_completeness()
        cats = result["categories"]
        assert cats["readability"]["converged"] == 1
        assert cats["idiosyncratic"]["converged"] == 0


from utils.convergence_tracker import (
    STARTER_MILESTONES,
    STARTER_WORD_GATE,
    get_starter_milestone,
)


class TestStarterMilestones:
    """Test Starter tier milestone logic."""

    def test_starter_milestones_defined(self):
        assert STARTER_MILESTONES == [2000, 5000, 10000, 20000]

    def test_starter_word_gate(self):
        assert STARTER_WORD_GATE == 20000

    def test_zero_words(self):
        result = get_starter_milestone(0)
        assert result["milestone"] == 0
        assert result["milestone_label"] is None
        assert result["words_next"] == 2000
        assert result["milestone_pct"] == 0

    def test_under_first_milestone(self):
        result = get_starter_milestone(1000)
        assert result["milestone"] == 0
        assert result["milestone_label"] is None
        assert result["words_current"] == 1000
        assert result["words_next"] == 2000
        assert result["milestone_pct"] == 50

    def test_at_first_milestone(self):
        result = get_starter_milestone(2000)
        assert result["milestone"] == 1
        assert result["milestone_label"] == "¼"
        assert result["words_current"] == 2000
        assert result["words_next"] == 5000

    def test_between_second_and_third(self):
        result = get_starter_milestone(7500)
        assert result["milestone"] == 2
        assert result["milestone_label"] == "½"
        assert result["words_current"] == 7500
        assert result["words_next"] == 10000
        assert result["milestone_pct"] == 50

    def test_at_third_milestone(self):
        result = get_starter_milestone(10000)
        assert result["milestone"] == 3
        assert result["milestone_label"] == "¾"
        assert result["words_current"] == 10000
        assert result["words_next"] == 20000

    def test_at_word_gate(self):
        result = get_starter_milestone(20000)
        assert result["milestone"] == 4
        assert result["milestone_label"] == "complete"
        assert result["words_current"] == 20000
        assert result["words_next"] == 20000
        assert result["milestone_pct"] == 100

    def test_above_word_gate(self):
        result = get_starter_milestone(50000)
        assert result["milestone"] == 4
        assert result["milestone_label"] == "complete"
        assert result["milestone_pct"] == 100


class TestConvergenceComputerWordGate:
    """Test that Bronze requires both convergence AND word gate."""

    def _make_computer(self, converged_count: int, total: int = 10) -> ConvergenceComputer:
        cc = ConvergenceComputer()
        for i in range(total):
            t = ElementTracker(f"el_{i}")
            t.count = 5
            t.mean = 0.5
            t.m2 = 0.01
            if i < converged_count:
                t._converged = True
            cc.add_tracker(t)
        return cc

    def test_high_convergence_low_words_stays_starter(self):
        """60% converged but only 15K words -> still starter."""
        cc = self._make_computer(6, 10)
        result = cc.compute_completeness(total_words=15000)
        assert result["tier"] == "starter"
        assert result["starter_progress"] is not None
        assert result["starter_progress"]["milestone"] == 3
        assert result["starter_progress"]["milestone_label"] == "¾"

    def test_high_convergence_high_words_gets_bronze(self):
        """60% converged AND 25K words -> Bronze."""
        cc = self._make_computer(6, 10)
        result = cc.compute_completeness(total_words=25000)
        assert result["tier"] == "bronze"
        assert result["tier_label"] == "Bronze"
        assert "starter_progress" not in result

    def test_low_convergence_high_words_stays_starter_complete(self):
        """30% converged, 25K words -> starter (complete), waiting on convergence."""
        cc = self._make_computer(3, 10)
        result = cc.compute_completeness(total_words=25000)
        assert result["tier"] == "starter"
        assert result["starter_progress"]["milestone"] == 4
        assert result["starter_progress"]["milestone_label"] == "complete"

    def test_silver_not_affected_by_word_gate(self):
        """80% converged, 25K words -> Silver (word gate only blocks Bronze)."""
        cc = self._make_computer(8, 10)
        result = cc.compute_completeness(total_words=25000)
        assert result["tier"] == "silver"
        assert "starter_progress" not in result

    def test_gold_not_affected_by_word_gate(self):
        """95% converged, 30K words -> Gold."""
        cc = self._make_computer(10, 10)
        result = cc.compute_completeness(total_words=30000)
        assert result["tier"] == "gold"

    def test_zero_words_starter(self):
        """0 words, no convergence -> starter milestone 0."""
        cc = self._make_computer(0, 10)
        result = cc.compute_completeness(total_words=0)
        assert result["tier"] == "starter"
        assert result["starter_progress"]["milestone"] == 0
