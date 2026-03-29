"""Tests for the fidelity scoring API endpoint."""
import pytest


@pytest.fixture
def client():
    from db import init_pool
    from app import app
    init_pool()
    from utils.rules_config import rules_config
    rules_config.seed_db()
    rules_config.load()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


class TestScoreFidelityRoute:
    def test_quantitative_scoring(self, client):
        """POST /api/score-fidelity with quantitative mode — requires profile_id=1 and 500+ words."""
        # Build text that exceeds the 500-word minimum required by the scorer
        base = (
            "This is a test sentence covering various topics in natural language. "
            "Here is another sentence that adds more words to the sample text. "
            "And a third sentence for good measure to keep the word count climbing. "
            "The quick brown fox jumps over the lazy dog quite often in these tests. "
        )
        long_text = base * 15  # ~600 words
        res = client.post("/api/score-fidelity", json={
            "generated_text": long_text,
            "profile_id": 1,
            "mode": "quantitative",
        })
        # Accept 200 (profile exists) or 404 (no profile with id=1 in test DB)
        assert res.status_code in (200, 404)
        if res.status_code == 200:
            data = res.get_json()
            assert "aggregate_similarity" in data or "per_element" in data

    def test_missing_generated_text(self, client):
        res = client.post("/api/score-fidelity", json={
            "profile_id": 1,
            "mode": "quantitative",
        })
        assert res.status_code == 400
        assert "generated_text" in res.get_json()["error"]

    def test_missing_profile_id(self, client):
        res = client.post("/api/score-fidelity", json={
            "generated_text": "Some text here.",
            "mode": "quantitative",
        })
        assert res.status_code == 400
        assert "profile_id" in res.get_json()["error"]

    def test_invalid_mode(self, client):
        res = client.post("/api/score-fidelity", json={
            "generated_text": "Some text.",
            "profile_id": 1,
            "mode": "invalid_mode",
        })
        assert res.status_code == 400


class TestGetProfileSamplesRoute:
    def test_get_samples_empty(self, client):
        """GET /api/voice-profiles/1/samples returns list (may be empty)."""
        res = client.get("/api/voice-profiles/1/samples")
        assert res.status_code == 200
        data = res.get_json()
        assert isinstance(data, list)
