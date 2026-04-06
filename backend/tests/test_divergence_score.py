import pytest
from unittest.mock import patch, MagicMock


class TestDivergenceScore:
    @patch('ai_providers.router.get_embedding_client')
    def test_identical_texts_zero_divergence(self, mock_get_client):
        mock_client = MagicMock()
        mock_client.is_available.return_value = True
        mock_client.similarity.return_value = 1.0
        mock_get_client.return_value = mock_client

        from ai_providers.router import _compute_divergence
        score, label, warning = _compute_divergence("hello world", "hello world")
        assert score == 0.0
        assert label == "low"

    @patch('ai_providers.router.get_embedding_client')
    def test_different_texts_high_divergence(self, mock_get_client):
        mock_client = MagicMock()
        mock_client.is_available.return_value = True
        mock_client.similarity.return_value = 0.3
        mock_get_client.return_value = mock_client

        from ai_providers.router import _compute_divergence
        score, label, warning = _compute_divergence("original text", "completely different")
        assert score == pytest.approx(0.7, abs=0.01)
        assert label == "high"

    @patch('ai_providers.router.get_embedding_client')
    def test_fallback_to_jaccard_when_sidecar_down(self, mock_get_client):
        mock_client = MagicMock()
        mock_client.is_available.return_value = False
        mock_get_client.return_value = mock_client

        from ai_providers.router import _compute_divergence
        score, label, warning = _compute_divergence("the cat sat on the mat today", "the cat sat on the mat today")
        assert score < 0.15
        assert label == "low"

    @patch('ai_providers.router.get_embedding_client')
    def test_moderate_divergence_label(self, mock_get_client):
        mock_client = MagicMock()
        mock_client.is_available.return_value = True
        mock_client.similarity.return_value = 0.75
        mock_get_client.return_value = mock_client

        from ai_providers.router import _compute_divergence
        score, label, warning = _compute_divergence("text a", "text b")
        assert label == "moderate"
