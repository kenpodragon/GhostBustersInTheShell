import pytest
from unittest.mock import patch, MagicMock
from utils.embedding_client import EmbeddingClient


class TestEmbeddingClient:
    def setup_method(self):
        self.client = EmbeddingClient(base_url="http://fake-embeddings:5000")

    @patch('utils.embedding_client.requests.post')
    def test_embed_returns_vectors(self, mock_post):
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {"embeddings": [[0.1, 0.2], [0.3, 0.4]]}
        )
        result = self.client.embed(["hello", "world"])
        assert result == [[0.1, 0.2], [0.3, 0.4]]
        mock_post.assert_called_once()

    @patch('utils.embedding_client.requests.post')
    def test_embed_returns_none_on_connection_error(self, mock_post):
        mock_post.side_effect = Exception("Connection refused")
        result = self.client.embed(["hello"])
        assert result is None

    @patch('utils.embedding_client.requests.post')
    def test_similarity_returns_float(self, mock_post):
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {"cosine_similarity": 0.87}
        )
        result = self.client.similarity("hello", "world")
        assert result == 0.87

    @patch('utils.embedding_client.requests.post')
    def test_similarity_returns_none_on_error(self, mock_post):
        mock_post.side_effect = Exception("Timeout")
        result = self.client.similarity("hello", "world")
        assert result is None

    @patch('utils.embedding_client.requests.get')
    def test_is_available_true_when_healthy(self, mock_get):
        mock_get.return_value = MagicMock(status_code=200)
        self.client._health_cache = None
        self.client._health_cache_time = 0
        assert self.client.is_available() is True

    @patch('utils.embedding_client.requests.get')
    def test_is_available_false_when_down(self, mock_get):
        mock_get.side_effect = Exception("Connection refused")
        self.client._health_cache = None
        self.client._health_cache_time = 0
        assert self.client.is_available() is False

    @patch('utils.embedding_client.requests.get')
    def test_is_available_caches_result(self, mock_get):
        mock_get.return_value = MagicMock(status_code=200)
        self.client._health_cache = None
        self.client._health_cache_time = 0
        self.client.is_available()
        self.client.is_available()
        assert mock_get.call_count == 1

    def test_embed_empty_list_returns_empty(self):
        result = self.client.embed([])
        assert result == []
