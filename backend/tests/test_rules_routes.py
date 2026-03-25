"""Tests for rules configuration API routes."""
import json
import pytest


@pytest.fixture
def client():
    from db import init_pool
    from app import app
    init_pool()
    # Ensure rules config is seeded and loaded
    from utils.rules_config import rules_config
    rules_config.seed_db()
    rules_config.load()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


class TestConfigCRUD:
    """Config CRUD endpoints."""

    def test_get_all_config(self, client):
        resp = client.get("/api/rules/config")
        assert resp.status_code == 200
        data = resp.get_json()
        # Should contain at least some known sections
        assert isinstance(data, dict)
        assert "heuristic_weights" in data
        assert "buzzwords" in data

    def test_get_single_section(self, client):
        resp = client.get("/api/rules/config/heuristic_weights")
        assert resp.status_code == 200
        data = resp.get_json()
        # Returns config_data directly (not wrapped)
        assert isinstance(data, dict)
        assert "sentence_opener_pos" in data

    def test_get_invalid_section(self, client):
        resp = client.get("/api/rules/config/nonexistent_section")
        assert resp.status_code == 404

    def test_put_update_section(self, client):
        # Get current value first
        resp = client.get("/api/rules/config/thresholds")
        assert resp.status_code == 200
        original = resp.get_json()

        # Update with new data
        new_data = dict(original) if isinstance(original, dict) else {}
        new_data["_test_marker"] = True
        resp = client.put(
            "/api/rules/config/thresholds",
            data=json.dumps(new_data),
            content_type="application/json",
        )
        assert resp.status_code == 200
        assert resp.get_json()["status"] == "updated"

        # Verify persisted
        resp = client.get("/api/rules/config/thresholds")
        assert resp.get_json()["_test_marker"] is True

        # Restore original
        client.put(
            "/api/rules/config/thresholds",
            data=json.dumps(original),
            content_type="application/json",
        )

    def test_put_invalid_section(self, client):
        resp = client.put(
            "/api/rules/config/nonexistent",
            data=json.dumps({"config_data": {}}),
            content_type="application/json",
        )
        assert resp.status_code == 404

    def test_get_defaults(self, client):
        resp = client.get("/api/rules/defaults")
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data, dict)
        assert "heuristic_weights" in data

    def test_revert_to_defaults(self, client):
        # Modify a section
        client.put(
            "/api/rules/config/thresholds",
            data=json.dumps({"_revert_test": True}),
            content_type="application/json",
        )

        # Revert
        resp = client.post("/api/rules/revert")
        assert resp.status_code == 200
        assert resp.get_json()["status"] == "reverted"

        # Verify reverted — should no longer have the test marker
        resp = client.get("/api/rules/config/thresholds")
        assert "_revert_test" not in resp.get_json()


class TestSnapshots:
    """Snapshot save/list/load/delete cycle."""

    def test_snapshot_lifecycle(self, client):
        # 1. Save snapshot
        resp = client.post(
            "/api/rules/snapshots",
            data=json.dumps({"name": "test-snapshot"}),
            content_type="application/json",
        )
        assert resp.status_code == 201
        snapshot = resp.get_json()
        assert snapshot["name"] == "test-snapshot"
        snapshot_id = snapshot["id"]

        # 2. List snapshots
        resp = client.get("/api/rules/snapshots")
        assert resp.status_code == 200
        snapshots = resp.get_json()
        assert any(s["id"] == snapshot_id for s in snapshots)

        # 3. Load snapshot
        resp = client.post(f"/api/rules/snapshots/{snapshot_id}/load")
        assert resp.status_code == 200
        assert resp.get_json()["status"] == "loaded"

        # 4. Delete snapshot
        resp = client.delete(f"/api/rules/snapshots/{snapshot_id}")
        assert resp.status_code == 200
        assert resp.get_json()["status"] == "deleted"

        # 5. Verify deleted
        resp = client.delete(f"/api/rules/snapshots/{snapshot_id}")
        assert resp.status_code == 404

    def test_save_snapshot_no_name(self, client):
        resp = client.post(
            "/api/rules/snapshots",
            data=json.dumps({}),
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_load_nonexistent_snapshot(self, client):
        resp = client.post("/api/rules/snapshots/999999/load")
        assert resp.status_code == 404


class TestVersion:
    """Version endpoint."""

    def test_get_version(self, client):
        resp = client.get("/api/version")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "app_version" in data
        assert "rules_version" in data
        assert "rules_version_date" in data
