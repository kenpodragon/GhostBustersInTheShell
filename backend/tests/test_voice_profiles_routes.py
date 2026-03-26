"""Tests for voice profile API routes."""
import json
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


@pytest.fixture
def profile_id(client):
    """Create a test profile and yield its id; delete after test."""
    resp = client.post(
        "/api/voice-profiles",
        data=json.dumps({"name": "_test_profile_routes", "description": "route test", "profile_type": "baseline"}),
        content_type="application/json",
    )
    assert resp.status_code == 201
    pid = resp.get_json()["id"]
    yield pid
    client.delete(f"/api/voice-profiles/{pid}")


# ---------------------------------------------------------------------------
# Profile CRUD
# ---------------------------------------------------------------------------

class TestProfileCRUD:
    def test_list_profiles(self, client):
        resp = client.get("/api/voice-profiles")
        assert resp.status_code == 200
        assert isinstance(resp.get_json(), list)

    def test_create_profile(self, client):
        resp = client.post(
            "/api/voice-profiles",
            data=json.dumps({"name": "_test_create_tmp", "description": "tmp", "profile_type": "overlay"}),
            content_type="application/json",
        )
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["name"] == "_test_create_tmp"
        assert "id" in data
        # Cleanup
        client.delete(f"/api/voice-profiles/{data['id']}")

    def test_create_profile_no_name(self, client):
        resp = client.post(
            "/api/voice-profiles",
            data=json.dumps({"description": "missing name"}),
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_get_profile(self, client, profile_id):
        resp = client.get(f"/api/voice-profiles/{profile_id}")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["id"] == profile_id
        assert "elements" in data
        assert "prompts" in data

    def test_get_profile_not_found(self, client):
        resp = client.get("/api/voice-profiles/999999")
        assert resp.status_code == 404

    def test_update_profile(self, client, profile_id):
        resp = client.put(
            f"/api/voice-profiles/{profile_id}",
            data=json.dumps({"name": "_test_profile_renamed"}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        assert resp.get_json()["name"] == "_test_profile_renamed"

    def test_update_profile_not_found(self, client):
        resp = client.put(
            "/api/voice-profiles/999999",
            data=json.dumps({"name": "ghost"}),
            content_type="application/json",
        )
        assert resp.status_code == 404

    def test_delete_profile(self, client):
        # Create then delete
        resp = client.post(
            "/api/voice-profiles",
            data=json.dumps({"name": "_test_delete_tmp"}),
            content_type="application/json",
        )
        pid = resp.get_json()["id"]
        resp = client.delete(f"/api/voice-profiles/{pid}")
        assert resp.status_code == 200
        assert resp.get_json()["status"] == "deleted"

    def test_get_deleted_profile(self, client):
        resp = client.post(
            "/api/voice-profiles",
            data=json.dumps({"name": "_test_del_then_get"}),
            content_type="application/json",
        )
        pid = resp.get_json()["id"]
        client.delete(f"/api/voice-profiles/{pid}")
        resp = client.get(f"/api/voice-profiles/{pid}")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Elements
# ---------------------------------------------------------------------------

class TestElements:
    def test_get_elements(self, client, profile_id):
        resp = client.get(f"/api/voice-profiles/{profile_id}/elements")
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data, list)
        # Starter elements should be present
        assert len(data) > 0

    def test_update_element_weight(self, client, profile_id):
        # Get current elements
        resp = client.get(f"/api/voice-profiles/{profile_id}/elements")
        elements = resp.get_json()
        assert len(elements) > 0

        # Update the first element's weight
        elem = dict(elements[0])
        original_weight = elem["weight"]
        new_weight = round(1.0 - original_weight, 2)
        elem["weight"] = new_weight

        resp = client.put(
            f"/api/voice-profiles/{profile_id}/elements",
            data=json.dumps([elem]),
            content_type="application/json",
        )
        assert resp.status_code == 200
        updated = resp.get_json()
        names = {e["name"]: e for e in updated}
        assert abs(names[elem["name"]]["weight"] - new_weight) < 0.01

    def test_update_elements_bad_body(self, client, profile_id):
        resp = client.put(
            f"/api/voice-profiles/{profile_id}/elements",
            data=json.dumps({"not": "a list"}),
            content_type="application/json",
        )
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

class TestPrompts:
    def test_get_prompts(self, client, profile_id):
        resp = client.get(f"/api/voice-profiles/{profile_id}/prompts")
        assert resp.status_code == 200
        assert isinstance(resp.get_json(), list)

    def test_update_prompts(self, client, profile_id):
        prompts = [{"prompt_text": "Never use em dashes.", "sort_order": 0}]
        resp = client.put(
            f"/api/voice-profiles/{profile_id}/prompts",
            data=json.dumps(prompts),
            content_type="application/json",
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["prompt_text"] == "Never use em dashes."

    def test_update_prompts_bad_body(self, client, profile_id):
        resp = client.put(
            f"/api/voice-profiles/{profile_id}/prompts",
            data=json.dumps("not a list"),
            content_type="application/json",
        )
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Active Stack
# ---------------------------------------------------------------------------

class TestActiveStack:
    def test_get_active_stack(self, client):
        resp = client.get("/api/voice-profiles/active")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "baseline" in data
        assert "overlays" in data
        assert "resolved_elements" in data
        assert "prompts" in data

    def test_set_active_stack(self, client, profile_id):
        resp = client.put(
            "/api/voice-profiles/active",
            data=json.dumps({"baseline_id": profile_id, "overlay_ids": []}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["baseline"] is not None
        assert data["baseline"]["id"] == profile_id

    def test_set_active_stack_no_body(self, client):
        # Without content-type Flask may return 415; with empty JSON body it returns 400
        resp = client.put(
            "/api/voice-profiles/active",
            data=json.dumps(None),
            content_type="application/json",
        )
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Style Guide
# ---------------------------------------------------------------------------

class TestStyleGuide:
    def test_get_style_guide(self, client):
        resp = client.get("/api/style-guide")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "elements" in data
        assert "english_instructions" in data
        assert "prompts" in data

    def test_get_style_guide_full(self, client):
        resp = client.get("/api/style-guide/full")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "voice_profile" in data
        assert "rules" in data
        assert "english_instructions" in data["voice_profile"]
        assert "heuristic_weights" in data["rules"]


# ---------------------------------------------------------------------------
# Snapshots
# ---------------------------------------------------------------------------

class TestSnapshots:
    def test_save_snapshot(self, client, profile_id):
        resp = client.post(
            f"/api/voice-profiles/{profile_id}/snapshots",
            data=json.dumps({"name": "test snap"}),
            content_type="application/json",
        )
        assert resp.status_code == 201
        data = resp.get_json()
        assert "id" in data
        # service returns snapshot_name (not name)
        assert data.get("snapshot_name") == "test snap" or data.get("name") == "test snap"

    def test_list_snapshots(self, client, profile_id):
        # Save one first
        client.post(
            f"/api/voice-profiles/{profile_id}/snapshots",
            data=json.dumps({"name": "list test snap"}),
            content_type="application/json",
        )
        resp = client.get(f"/api/voice-profiles/{profile_id}/snapshots")
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data, list)
        # service returns snapshot_name field
        assert any(s.get("snapshot_name") == "list test snap" or s.get("name") == "list test snap" for s in data)

    def test_load_snapshot(self, client, profile_id):
        # Save
        resp = client.post(
            f"/api/voice-profiles/{profile_id}/snapshots",
            data=json.dumps({"name": "load test snap"}),
            content_type="application/json",
        )
        snap_id = resp.get_json()["id"]
        # Load
        resp = client.post(f"/api/voice-profiles/{profile_id}/snapshots/{snap_id}/load")
        assert resp.status_code == 200
        assert resp.get_json()["status"] == "loaded"

    def test_delete_snapshot(self, client, profile_id):
        # Save
        resp = client.post(
            f"/api/voice-profiles/{profile_id}/snapshots",
            data=json.dumps({"name": "delete test snap"}),
            content_type="application/json",
        )
        snap_id = resp.get_json()["id"]
        # Delete
        resp = client.delete(f"/api/voice-profiles/{profile_id}/snapshots/{snap_id}")
        assert resp.status_code == 200
        assert resp.get_json()["status"] == "deleted"
        # Verify gone
        resp = client.delete(f"/api/voice-profiles/{profile_id}/snapshots/{snap_id}")
        assert resp.status_code == 404

    def test_save_snapshot_no_name(self, client, profile_id):
        resp = client.post(
            f"/api/voice-profiles/{profile_id}/snapshots",
            data=json.dumps({}),
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_load_nonexistent_snapshot(self, client, profile_id):
        resp = client.post(f"/api/voice-profiles/{profile_id}/snapshots/999999/load")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Export / Import
# ---------------------------------------------------------------------------

class TestExportImport:
    def test_export_profile(self, client, profile_id):
        resp = client.get(f"/api/voice-profiles/{profile_id}/export")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "name" in data
        assert "elements" in data

    def test_export_not_found(self, client):
        resp = client.get("/api/voice-profiles/999999/export")
        assert resp.status_code == 404

    def test_import_profile(self, client, profile_id):
        # Export first
        export_resp = client.get(f"/api/voice-profiles/{profile_id}/export")
        export_data = export_resp.get_json()
        export_data["name"] = "_test_import_copy"

        resp = client.post(
            "/api/voice-profiles/import",
            data=json.dumps(export_data),
            content_type="application/json",
        )
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["name"] == "_test_import_copy"
        # Cleanup
        client.delete(f"/api/voice-profiles/{data['id']}")


# ---------------------------------------------------------------------------
# Parse & Reset
# ---------------------------------------------------------------------------

class TestParse:
    # generate_voice_profile requires >= 500 words; short text returns 400
    SHORT_TEXT = (
        "The project went well. We finished on time and the client loved it. "
        "I honestly didn't expect such a smooth delivery."
    )
    # 500+ word sample for happy path (10 words per sentence * 60 = 600 words)
    LONG_TEXT = " ".join(["The project went smoothly and the team delivered on time."] * 60)

    def test_parse_text_short_returns_400(self, client, profile_id):
        """Short text (<500 words) should return 400 with an error message."""
        resp = client.post(
            f"/api/voice-profiles/{profile_id}/parse",
            data=json.dumps({"text": self.SHORT_TEXT}),
            content_type="application/json",
        )
        assert resp.status_code == 400
        data = resp.get_json()
        assert "error" in data

    def test_parse_text_long(self, client, profile_id):
        """500+ word text should parse successfully."""
        resp = client.post(
            f"/api/voice-profiles/{profile_id}/parse",
            data=json.dumps({"text": self.LONG_TEXT}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert "elements" in data
        assert "parse_count" in data
        assert data["parse_count"] >= 1

    def test_parse_no_text(self, client, profile_id):
        resp = client.post(
            f"/api/voice-profiles/{profile_id}/parse",
            data=json.dumps({}),
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_reset_corpus(self, client, profile_id):
        resp = client.post(f"/api/voice-profiles/{profile_id}/reset")
        assert resp.status_code == 200
        assert resp.get_json()["status"] == "reset"
        # parse_count should be 0
        profile_resp = client.get(f"/api/voice-profiles/{profile_id}")
        assert profile_resp.get_json()["parse_count"] == 0
