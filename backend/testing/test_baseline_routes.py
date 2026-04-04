"""Tests for baseline update check and apply endpoints."""
import json
from unittest.mock import patch, MagicMock
import pytest
from app import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


class TestBaselineUpdateCheck:
    """GET /api/baseline/updates/check"""

    @patch("routes.baseline._fetch_github_json")
    @patch("routes.baseline.query_one")
    def test_up_to_date(self, mock_query, mock_fetch, client):
        mock_query.return_value = {"baseline_version": "1.0.0"}
        mock_fetch.return_value = {
            "version": "1.0.0",
            "date": "2026-04-04",
            "min_app_version": "1.0.0",
            "changelog": "Initial",
        }

        resp = client.get("/api/baseline/updates/check")
        data = resp.get_json()

        assert data["status"] == "up_to_date"
        assert data["current_version"] == "1.0.0"

    @patch("routes.baseline._fetch_github_json")
    @patch("routes.baseline.query_one")
    def test_update_available(self, mock_query, mock_fetch, client):
        mock_query.return_value = {"baseline_version": "1.0.0"}
        mock_fetch.return_value = {
            "version": "1.1.0",
            "date": "2026-05-01",
            "min_app_version": "1.0.0",
            "changelog": "Updated baseline with more articles",
        }

        resp = client.get("/api/baseline/updates/check")
        data = resp.get_json()

        assert data["status"] == "update_available"
        assert data["remote_version"] == "1.1.0"
        assert data["changelog"] == "Updated baseline with more articles"

    @patch("routes.baseline._fetch_github_json", side_effect=Exception("Network error"))
    @patch("routes.baseline.query_one")
    def test_github_fetch_failure(self, mock_query, mock_fetch, client):
        mock_query.return_value = {"baseline_version": "1.0.0"}

        resp = client.get("/api/baseline/updates/check")
        data = resp.get_json()

        assert resp.status_code == 502
        assert "error" in data


class TestBaselineUpdateApply:
    """POST /api/baseline/updates/apply"""

    @patch("routes.baseline.VoiceProfileService")
    @patch("routes.baseline.execute")
    @patch("routes.baseline._fetch_github_json")
    def test_successful_apply(self, mock_fetch, mock_execute, mock_svc_cls, client):
        mock_fetch.side_effect = [
            # First call: version manifest
            {"version": "1.1.0", "date": "2026-05-01", "min_app_version": "1.0.0", "changelog": "Update"},
            # Second call: profile data
            {
                "profile_name": "Modern Human Baseline",
                "parse_count": 400,
                "elements": [{"name": "test", "category": "lexical", "element_type": "metric",
                              "weight": 0.5, "tags": [], "source": "heuristic"}],
                "prompts": [{"prompt_text": "Write naturally.", "sort_order": 0}],
            },
        ]
        mock_svc = MagicMock()
        mock_svc.import_profile.return_value = {"id": 99, "name": "Modern Human Baseline"}
        mock_svc_cls.return_value = mock_svc

        resp = client.post("/api/baseline/updates/apply")
        data = resp.get_json()

        assert data["success"] is True
        assert data["version"] == "1.1.0"
        assert data["baseline_id"] == 99
        mock_svc.import_profile.assert_called_once()


class TestVersionEndpointIncludesBaseline:
    """GET /api/version should include baseline_version."""

    @patch("routes.rules.query_one")
    def test_version_includes_baseline(self, mock_query, client):
        mock_query.return_value = {
            "rules_version": "1.0.0",
            "rules_version_date": "2026-03-25",
            "baseline_version": "1.0.0",
            "baseline_version_date": "2026-04-04",
        }

        resp = client.get("/api/version")
        data = resp.get_json()

        assert "baseline_version" in data
        assert data["baseline_version"] == "1.0.0"
