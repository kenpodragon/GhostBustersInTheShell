"""Integration tests for convergence tracking in the parse flow."""
import pytest
from utils.convergence_tracker import ElementTracker, ConvergenceComputer


class TestConvergenceDBIntegration:
    """Test convergence tracker persistence to/from DB rows."""

    def test_tracker_round_trip(self):
        """Serialize to dict and restore — state should be identical."""
        t = ElementTracker("comma_rate")
        t.update(0.05, 1000)
        t.update(0.06, 2000)
        t.update(0.055, 3000)

        data = t.to_dict()
        t2 = ElementTracker.from_dict(data)

        assert t2.name == "comma_rate"
        assert t2.count == 3
        assert t2.mean == pytest.approx(t.mean)
        assert t2.m2 == pytest.approx(t.m2)
        assert t2.rolling_delta == pytest.approx(t.rolling_delta)
        assert t2.consecutive_stable == t.consecutive_stable
        assert t2.converged == t.converged

    def test_tracker_incremental_persistence(self):
        """Simulate save-restore-update cycle (as DB would do)."""
        t = ElementTracker("exclamation_rate")
        t.update(0.02, 500)
        state = t.to_dict()

        t2 = ElementTracker.from_dict(state)
        t2.update(0.021, 1000)
        assert t2.count == 2
        assert t2.mean == pytest.approx(0.0205)


class TestCompletenessFromDB:
    """Test building completeness response from tracker states."""

    def test_build_completeness_response(self):
        cc = ConvergenceComputer()
        for name in ["flesch_reading_ease", "flesch_kincaid_grade",
                      "gunning_fog_index", "smog_index", "automated_readability_index"]:
            t = ElementTracker(name)
            t._converged = True
            cc.add_tracker(t)
        for name in ["em_dash_usage", "ellipsis_usage"]:
            t = ElementTracker(name)
            cc.add_tracker(t)

        result = cc.compute_completeness()
        assert result["pct"] == 71
        assert result["tier"] == "bronze"
        assert result["categories"]["readability"]["status"] == "complete"
        assert result["categories"]["idiosyncratic"]["status"] == "needs_more"
