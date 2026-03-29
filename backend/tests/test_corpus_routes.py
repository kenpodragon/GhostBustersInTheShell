"""Tests for corpus management endpoints."""
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


class TestGetCorpusInfo:
    def test_returns_corpus_structure(self, client):
        res = client.get("/api/voice-profiles/1/corpus")
        assert res.status_code == 200
        data = res.get_json()
        assert "documents" in data
        assert "stats" in data
        assert "total_documents" in data["stats"]
        assert "total_words" in data["stats"]
        assert "ai_observations_count" in data["stats"]


class TestDocumentManagement:
    def test_list_analysis_docs(self, client):
        res = client.get("/api/documents/management?purpose=analysis")
        assert res.status_code == 200
        data = res.get_json()
        assert "documents" in data
        assert "stats" in data
        assert "total_count" in data["stats"]

    def test_purge_refuses_voice_corpus(self, client):
        res = client.delete("/api/documents/purge", json={
            "purpose": "voice_corpus",
            "older_than_days": 30,
        })
        assert res.status_code == 400
        assert "Cannot bulk purge" in res.get_json()["error"]

    def test_purge_analysis_docs(self, client):
        res = client.delete("/api/documents/purge", json={
            "purpose": "analysis",
            "older_than_days": 9999,
        })
        assert res.status_code == 200
        data = res.get_json()
        assert "deleted_count" in data
