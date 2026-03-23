"""Tests for heuristic level classification and paragraph scoring."""
import pytest
from utils.heuristics.levels import HEURISTIC_LEVELS, get_heuristics_for_level


class TestHeuristicLevels:
    """Verify level classification map."""

    def test_all_weighted_heuristics_have_levels(self):
        """Every heuristic with weight > 0 must be classified."""
        from utils.heuristics.reference_data import HEURISTIC_WEIGHTS
        active = {k for k, v in HEURISTIC_WEIGHTS.items() if v > 0}
        classified = set(HEURISTIC_LEVELS.keys())
        missing = active - classified
        assert not missing, f"Heuristics missing level: {missing}"

    def test_document_level_heuristics(self):
        doc = get_heuristics_for_level("document")
        assert "compression_ratio" in doc
        assert "yules_k" in doc
        assert "vocabulary_richness" in doc

    def test_paragraph_level_heuristics(self):
        para = get_heuristics_for_level("paragraph")
        assert "self_contained_paragraphs" in para
        assert "transition_stacks" in para
        assert "paragraph_uniformity" in para

    def test_sentence_level_heuristics(self):
        sent = get_heuristics_for_level("sentence")
        assert "buzzwords" in sent
        assert "hedge_words" in sent
        assert "trailing_participial" in sent

    def test_cross_level_heuristics(self):
        cross = get_heuristics_for_level("cross")
        assert "contractions" in cross
        assert "sentence_opener_pos" in cross

    def test_no_duplicate_assignments(self):
        """Each heuristic should be assigned to exactly one level."""
        seen = set()
        for name, level in HEURISTIC_LEVELS.items():
            assert name not in seen, f"Duplicate: {name}"
            seen.add(name)
