import os
import time
import requests

DEFAULT_URL = "http://ghostbusters-roberta:5000"
TIMEOUT = 30
HEALTH_CACHE_TTL = 60


class RobertaClient:
    def __init__(self, base_url: str = None):
        self.base_url = base_url or os.environ.get("ROBERTA_SERVICE_URL", DEFAULT_URL)
        self._health_cache: bool | None = None
        self._health_cache_time: float = 0

    def classify(self, text: str) -> dict | None:
        if not text:
            return None
        try:
            resp = requests.post(
                f"{self.base_url}/classify",
                json={"text": text},
                timeout=TIMEOUT
            )
            resp.raise_for_status()
            return resp.json()
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


_client: RobertaClient | None = None


def get_roberta_client() -> RobertaClient:
    global _client
    if _client is None:
        _client = RobertaClient()
    return _client
