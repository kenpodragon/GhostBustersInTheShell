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


from utils.detector import _split_paragraphs, _score_paragraph


class TestSplitParagraphs:
    """Paragraph splitting."""

    def test_splits_on_double_newline(self):
        text = "First paragraph.\n\nSecond paragraph.\n\nThird."
        result = _split_paragraphs(text)
        assert len(result) == 3

    def test_single_paragraph(self):
        text = "Just one paragraph with no breaks."
        result = _split_paragraphs(text)
        assert len(result) == 1

    def test_strips_whitespace(self):
        text = "  First.  \n\n  Second.  "
        result = _split_paragraphs(text)
        assert result[0] == "First."
        assert result[1] == "Second."

    def test_ignores_empty_paragraphs(self):
        text = "First.\n\n\n\n\nSecond."
        result = _split_paragraphs(text)
        assert len(result) == 2


class TestScoreParagraph:
    """Per-paragraph scoring."""

    def test_returns_score_and_patterns(self):
        para = (
            "Furthermore, it is essential to leverage innovative strategies. "
            "Moreover, organizations must harness cutting-edge solutions. "
            "Additionally, stakeholders should foster robust collaboration."
        )
        score, patterns, signals = _score_paragraph(para, para_index=0, total_paragraphs=5)
        assert isinstance(score, (int, float))
        assert isinstance(patterns, list)
        assert isinstance(signals, dict)
        assert score > 0  # Should flag AI patterns

    def test_human_paragraph_scores_low(self):
        para = (
            "I went to the store yesterday and couldn't find the brand Dave recommended. "
            "Ended up buying whatever was on sale — it's fine, honestly. "
            "We'll see. "
            "The old stuff was better but hey, you can't always get what you want, "
            "and I'm not driving across town for mayonnaise."
        )
        score, patterns, signals = _score_paragraph(para, para_index=0, total_paragraphs=3)
        assert score < 25  # Human text with varied sentence lengths should score low
