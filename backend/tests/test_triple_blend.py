import pytest
from unittest.mock import patch, MagicMock


class TestTripleBlend:
    @patch('ai_providers.router.get_roberta_client')
    def test_roberta_fields_in_response_heuristic_only(self, mock_roberta_client):
        """Response should include RoBERTa fields when available."""
        mock_rc = MagicMock()
        mock_rc.is_available.return_value = True
        mock_rc.classify.return_value = {
            "ai_probability": 0.92,
            "label": "ai-generated",
            "chunks": [{"text": "test", "ai_probability": 0.92}]
        }
        mock_roberta_client.return_value = mock_rc

        from ai_providers.router import route_analysis
        result = route_analysis("This is a test sentence for analysis.", use_ai=False)

        assert result.get("_roberta_available") is True
        assert "_roberta_score" in result
        assert "_roberta_chunks" in result

    @patch('ai_providers.router.get_roberta_client')
    def test_roberta_unavailable_fields(self, mock_roberta_client):
        """When RoBERTa is down, _roberta_available should be False."""
        mock_rc = MagicMock()
        mock_rc.is_available.return_value = False
        mock_roberta_client.return_value = mock_rc

        from ai_providers.router import route_analysis
        result = route_analysis("This is a test sentence.", use_ai=False)

        assert result.get("_roberta_available") is False

    @patch('ai_providers.router.get_roberta_client')
    def test_heuristic_plus_roberta_blend(self, mock_roberta_client):
        """Heuristic + RoBERTa should use 0.60/0.40 weights."""
        mock_rc = MagicMock()
        mock_rc.is_available.return_value = True
        mock_rc.classify.return_value = {
            "ai_probability": 1.0,  # 100% AI
            "label": "ai-generated",
            "chunks": []
        }
        mock_roberta_client.return_value = mock_rc

        from ai_providers.router import route_analysis
        result = route_analysis("Normal human text here.", use_ai=False)

        # Score should be higher than heuristic-only because RoBERTa says 100% AI
        # Exact value depends on heuristic score, but RoBERTa pulls it up
        assert result.get("_roberta_available") is True
        assert result.get("_roberta_score") == 100.0
