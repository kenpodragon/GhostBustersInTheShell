"""Tests for VoiceProfileService."""
import pytest
from utils.voice_profile_service import VoiceProfileService


@pytest.fixture
def svc():
    from db import init_pool, get_conn
    init_pool()
    with get_conn() as conn:
        yield VoiceProfileService(conn)


class TestProfileCRUD:
    def test_list_profiles(self, svc):
        profiles = svc.list_profiles()
        assert isinstance(profiles, list)
        assert len(profiles) >= 1
        assert profiles[0]["profile_type"] == "baseline"

    def test_create_profile(self, svc):
        profile = svc.create_profile("Test Overlay", "A test overlay", "overlay")
        assert profile["name"] == "Test Overlay"
        assert profile["profile_type"] == "overlay"
        assert profile["parse_count"] == 0
        svc.delete_profile(profile["id"])

    def test_get_profile(self, svc):
        profile = svc.create_profile("Get Test", "desc", "overlay")
        fetched = svc.get_profile(profile["id"])
        assert fetched["name"] == "Get Test"
        assert "elements" in fetched
        assert "prompts" in fetched
        assert len(fetched["elements"]) == 5  # starter elements
        svc.delete_profile(profile["id"])

    def test_update_profile(self, svc):
        profile = svc.create_profile("Update Test", "desc", "overlay")
        svc.update_profile(profile["id"], name="Updated Name")
        fetched = svc.get_profile(profile["id"])
        assert fetched["name"] == "Updated Name"
        svc.delete_profile(profile["id"])

    def test_delete_profile(self, svc):
        profile = svc.create_profile("Delete Test", "desc", "overlay")
        svc.delete_profile(profile["id"])
        assert svc.get_profile(profile["id"]) is None

    def test_get_nonexistent_profile(self, svc):
        assert svc.get_profile(99999) is None
