import os
import time
import requests

DEFAULT_URL = "http://ghostbusters-embeddings:5000"
TIMEOUT = 10
HEALTH_CACHE_TTL = 60


class EmbeddingClient:
    def __init__(self, base_url: str = None):
        self.base_url = base_url or os.environ.get("EMBEDDING_SERVICE_URL", DEFAULT_URL)
        self._health_cache: bool | None = None
        self._health_cache_time: float = 0

    def embed(self, texts: list[str]) -> list[list[float]] | None:
        if not texts:
            return []
        try:
            resp = requests.post(
                f"{self.base_url}/embed",
                json={"texts": texts},
                timeout=TIMEOUT
            )
            resp.raise_for_status()
            return resp.json()["embeddings"]
        except Exception:
            return None

    def similarity(self, text_a: str, text_b: str) -> float | None:
        try:
            resp = requests.post(
                f"{self.base_url}/similarity",
                json={"text_a": text_a, "text_b": text_b},
                timeout=TIMEOUT
            )
            resp.raise_for_status()
            return resp.json()["cosine_similarity"]
        except Exception:
            return None

    def is_available(self) -> bool:
        now = time.time()
        if self._health_cache is not None and (now - self._health_cache_time) < HEALTH_CACHE_TTL:
            return self._health_cache
        try:
            resp = requests.get(f"{self.base_url}/health", timeout=3)
            self._health_cache = resp.status_code == 200
        except Exception:
            self._health_cache = False
        self._health_cache_time = now
        return self._health_cache


_client: EmbeddingClient | None = None


def get_embedding_client() -> EmbeddingClient:
    global _client
    if _client is None:
        _client = EmbeddingClient()
    return _client
