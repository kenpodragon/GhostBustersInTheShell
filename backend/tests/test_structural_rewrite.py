import pytest
from utils.style_brief import generate_style_brief


class TestStructuralRewritePriority:
    def test_always_on_structural_instruction(self):
        """Style brief should always include structural priority instruction."""
        brief = generate_style_brief(
            mode="voice"
        )
        assert "structural changes" in brief.lower() or "reorder sentences" in brief.lower()

    def test_low_divergence_triggers_stronger_directive(self):
        """When divergence is low, style brief should include aggressive restructuring."""
        brief = generate_style_brief(
            mode="detection_fix",
            divergence_label="low"
        )
        assert "restructure" in brief.lower()
        assert "aggressive" in brief.lower() or "sentence order" in brief.lower()

    def test_high_divergence_no_extra_directive(self):
        """When divergence is high, no extra restructuring directive needed."""
        brief = generate_style_brief(
            mode="detection_fix",
            divergence_label="high"
        )
        assert "structural changes" in brief.lower() or "reorder sentences" in brief.lower()
        assert "previous rewrite was too close" not in brief.lower()

    def test_no_divergence_label_no_crash(self):
        """When divergence_label is not provided, should not crash."""
        brief = generate_style_brief(
            mode="voice"
        )
        assert isinstance(brief, str)
        assert len(brief) > 0
