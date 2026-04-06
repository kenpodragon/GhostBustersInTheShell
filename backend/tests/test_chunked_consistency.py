import pytest
from unittest.mock import patch
from utils.heuristics.chunked_consistency import check_chunked_consistency


class TestChunkedConsistency:
    """Chunked consistency: low CV across chunk scores = AI signal."""

    def test_short_text_returns_zero(self):
        """Text under 900 words should return 0."""
        text = "Short text. " * 50
        score, patterns = check_chunked_consistency(text)
        assert score == 0
        assert patterns == []

    @patch('utils.heuristics.chunked_consistency.detect_ai_patterns')
    def test_uniform_chunks_score_high(self, mock_detect):
        """All chunks scoring similarly should flag as suspicious."""
        mock_detect.return_value = {"overall_score": 45}
        text = "Word " * 1000
        score, patterns = check_chunked_consistency(text)
        assert score > 0, f"Expected positive score for uniform chunks, got {score}"
        assert any(p["pattern"] == "chunked_consistency" for p in patterns)

    @patch('utils.heuristics.chunked_consistency.detect_ai_patterns')
    def test_varied_chunks_score_zero(self, mock_detect):
        """Chunks with highly varied scores should not flag."""
        mock_detect.side_effect = [
            {"overall_score": 10},
            {"overall_score": 60},
            {"overall_score": 25},
        ]
        text = "Word " * 1000
        score, patterns = check_chunked_consistency(text)
        assert score == 0, f"Expected 0 for varied chunks, got {score}"

    @patch('utils.heuristics.chunked_consistency.detect_ai_patterns')
    def test_exactly_three_chunks(self, mock_detect):
        """Minimum viable: exactly 3 chunks at 900 words."""
        mock_detect.return_value = {"overall_score": 40}
        text = "Word " * 900
        score, patterns = check_chunked_consistency(text)
        assert mock_detect.call_count == 3

    def test_returns_tuple_format(self):
        """Must return (float, list[dict])."""
        text = "Word " * 50
        score, patterns = check_chunked_consistency(text)
        assert isinstance(score, (int, float))
        assert isinstance(patterns, list)

    @patch('utils.heuristics.chunked_consistency.detect_ai_patterns')
    def test_does_not_recurse(self, mock_detect):
        """Sub-chunk detection calls must pass _skip_chunked=True."""
        mock_detect.return_value = {"overall_score": 45}
        text = "Word " * 1000
        check_chunked_consistency(text)
        for call in mock_detect.call_args_list:
            kwargs = call[1] if len(call) > 1 else call.kwargs
            assert kwargs.get('_skip_chunked') is True
