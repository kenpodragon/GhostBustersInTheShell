import pytest
from unittest.mock import patch, MagicMock
from utils.heuristics.semantic_monotony import check_semantic_monotony


class TestSemanticMonotony:
    """Semantic monotony: high mean pairwise similarity = AI signal."""

    def test_uniform_ai_text_scores_high(self):
        """AI text with repetitive semantic content should score > 0."""
        text = (
            "AI technology is transforming the modern workplace. "
            "AI technology is reshaping how businesses operate. "
            "AI technology is revolutionizing the corporate landscape. "
            "AI technology is changing the way we work. "
            "AI technology is redefining professional environments."
        )
        score, patterns = check_semantic_monotony(text)
        assert score > 0, f"Expected positive score for uniform text, got {score}"
        assert any(p["pattern"] == "semantic_monotony" for p in patterns)

    def test_varied_human_text_scores_low(self):
        """Human text jumping between topics should score 0 or near 0."""
        text = (
            "The cat knocked over my coffee this morning. "
            "Interest rates are expected to rise next quarter. "
            "My grandmother's lasagna recipe uses three types of cheese. "
            "The Mars rover discovered unusual mineral formations. "
            "I need to replace the brake pads on my truck."
        )
        score, patterns = check_semantic_monotony(text)
        assert score == 0, f"Expected 0 for varied text, got {score}"

    def test_short_text_returns_zero(self):
        """Text with fewer than 4 sentences should return 0."""
        text = "First sentence. Second sentence. Third sentence."
        score, patterns = check_semantic_monotony(text)
        assert score == 0
        assert patterns == []

    def test_returns_tuple_format(self):
        """Must return (float, list[dict]) matching heuristic contract."""
        text = "Sentence one. Sentence two. Sentence three. Sentence four. Sentence five."
        score, patterns = check_semantic_monotony(text)
        assert isinstance(score, (int, float))
        assert isinstance(patterns, list)

    @patch('utils.heuristics.semantic_monotony.get_embedding_client')
    def test_uses_embeddings_when_available(self, mock_get_client):
        """When embeddings sidecar is available, use neural embeddings."""
        mock_client = MagicMock()
        mock_client.is_available.return_value = True
        mock_client.embed.return_value = [[0.5] * 384] * 5
        mock_get_client.return_value = mock_client

        text = "One thing. Another thing. More things. Yet more. Still more."
        score, patterns = check_semantic_monotony(text)
        assert score > 0
        mock_client.embed.assert_called_once()

    @patch('utils.heuristics.semantic_monotony.get_embedding_client')
    def test_falls_back_to_tfidf_when_sidecar_down(self, mock_get_client):
        """When sidecar unavailable, fall back to TF-IDF."""
        mock_client = MagicMock()
        mock_client.is_available.return_value = False
        mock_get_client.return_value = mock_client

        text = (
            "AI technology is transforming the modern workplace. "
            "AI technology is reshaping how businesses operate. "
            "AI technology is revolutionizing the corporate landscape. "
            "AI technology is changing the way we work. "
            "AI technology is redefining professional environments."
        )
        score, patterns = check_semantic_monotony(text)
        assert score >= 0
        mock_client.embed.assert_not_called()
