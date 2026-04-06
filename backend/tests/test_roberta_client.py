import pytest
from unittest.mock import patch, MagicMock
from utils.roberta_client import RobertaClient


class TestRobertaClient:
    def setup_method(self):
        self.client = RobertaClient(base_url="http://fake-roberta:5000")

    @patch('utils.roberta_client.requests.post')
    def test_classify_returns_result(self, mock_post):
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                "ai_probability": 0.92,
                "label": "ai-generated",
                "chunks": [{"text": "test...", "ai_probability": 0.92}]
            }
        )
        result = self.client.classify("Some text to classify")
        assert result["ai_probability"] == 0.92
        assert result["label"] == "ai-generated"
        assert len(result["chunks"]) == 1

    @patch('utils.roberta_client.requests.post')
    def test_classify_returns_none_on_error(self, mock_post):
        mock_post.side_effect = Exception("Connection refused")
        result = self.client.classify("Some text")
        assert result is None

    @patch('utils.roberta_client.requests.post')
    def test_classify_returns_none_on_empty_text(self, mock_post):
        result = self.client.classify("")
        assert result is None
        mock_post.assert_not_called()

    @patch('utils.roberta_client.requests.get')
    def test_is_available_true_when_healthy(self, mock_get):
        mock_get.return_value = MagicMock(status_code=200)
        self.client._health_cache = None
        self.client._health_cache_time = 0
        assert self.client.is_available() is True

    @patch('utils.roberta_client.requests.get')
    def test_is_available_false_when_down(self, mock_get):
        mock_get.side_effect = Exception("Connection refused")
        self.client._health_cache = None
        self.client._health_cache_time = 0
        assert self.client.is_available() is False

    @patch('utils.roberta_client.requests.get')
    def test_is_available_caches_result(self, mock_get):
        mock_get.return_value = MagicMock(status_code=200)
        self.client._health_cache = None
        self.client._health_cache_time = 0
        self.client.is_available()
        self.client.is_available()
        assert mock_get.call_count == 1
