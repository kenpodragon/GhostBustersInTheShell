"""Tests for baseline_seeder.seed_baseline_profile()."""
import json
from unittest.mock import patch, MagicMock, mock_open
import pytest


def _make_version_json(version="1.0.0"):
    return json.dumps({"version": version, "date": "2026-04-04", "min_app_version": "1.0.0", "changelog": "test"})


def _make_profile_json():
    return json.dumps({
        "name": "Modern Human Baseline",
        "description": "Baseline voice profile",
        "profile_type": "baseline",
        "parse_count": 325,
        "elements": [{"name": "test_el", "category": "lexical", "element_type": "metric",
                       "weight": 0.5, "tags": [], "source": "heuristic"}],
        "prompts": [{"prompt_text": "Write naturally.", "sort_order": 0}],
    })


class TestSeedBaselineProfile:
    """Tests for seed_baseline_profile()."""

    @patch("utils.voice_profile_service.VoiceProfileService")
    @patch("utils.baseline_seeder.get_conn")
    @patch("utils.baseline_seeder.query_one")
    @patch("utils.baseline_seeder.execute")
    @patch("builtins.open", new_callable=mock_open)
    @patch("os.path.exists", return_value=True)
    def test_fresh_install_imports_baseline(self, mock_exists, mock_file, mock_execute, mock_query, mock_get_conn, mock_svc_cls):
        """On fresh install (no baseline_version in settings), imports baseline and sets version."""
        from utils.baseline_seeder import seed_baseline_profile

        # No baseline version set yet
        mock_query.return_value = {"baseline_version": None, "active_baseline_id": None}

        # Mock file reads: first call = version JSON, second call = profile JSON
        mock_file.side_effect = [
            mock_open(read_data=_make_version_json())(),
            mock_open(read_data=_make_profile_json())(),
        ]

        # Mock get_conn context manager
        mock_conn = MagicMock()
        mock_get_conn.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_get_conn.return_value.__exit__ = MagicMock(return_value=False)

        # Mock import_profile returning new profile
        mock_svc = MagicMock()
        mock_svc.import_profile.return_value = {"id": 42, "name": "Modern Human Baseline"}
        mock_svc_cls.return_value = mock_svc

        seed_baseline_profile()

        mock_svc.import_profile.assert_called_once()
        # Should update settings with version and baseline id
        assert mock_execute.call_count >= 1
        update_call = mock_execute.call_args_list[-1]
        sql = update_call[0][0]
        assert "baseline_version" in sql
        assert "active_baseline_id" in sql

    @patch("utils.voice_profile_service.VoiceProfileService")
    @patch("utils.baseline_seeder.query_one")
    @patch("builtins.open", new_callable=mock_open)
    @patch("os.path.exists", return_value=True)
    def test_version_match_skips_import(self, mock_exists, mock_file, mock_query, mock_svc_cls):
        """When seed version matches DB version, no import happens."""
        from utils.baseline_seeder import seed_baseline_profile

        mock_query.return_value = {"baseline_version": "1.0.0", "active_baseline_id": 1}
        mock_file.return_value = mock_open(read_data=_make_version_json("1.0.0"))()

        seed_baseline_profile()

        mock_svc_cls.assert_not_called()

    @patch("utils.voice_profile_service.VoiceProfileService")
    @patch("utils.baseline_seeder.get_conn")
    @patch("utils.baseline_seeder.query_one")
    @patch("utils.baseline_seeder.execute")
    @patch("builtins.open", new_callable=mock_open)
    @patch("os.path.exists", return_value=True)
    def test_version_upgrade_imports_new_baseline(self, mock_exists, mock_file, mock_execute, mock_query, mock_get_conn, mock_svc_cls):
        """When seed version > DB version, imports new baseline."""
        from utils.baseline_seeder import seed_baseline_profile

        mock_query.return_value = {"baseline_version": "1.0.0", "active_baseline_id": 10}
        mock_file.side_effect = [
            mock_open(read_data=_make_version_json("1.1.0"))(),
            mock_open(read_data=_make_profile_json())(),
        ]

        # Mock get_conn context manager
        mock_conn = MagicMock()
        mock_get_conn.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_get_conn.return_value.__exit__ = MagicMock(return_value=False)

        mock_svc = MagicMock()
        mock_svc.import_profile.return_value = {"id": 55, "name": "Modern Human Baseline"}
        mock_svc_cls.return_value = mock_svc

        seed_baseline_profile()

        mock_svc.import_profile.assert_called_once()

    @patch("utils.baseline_seeder.query_one")
    @patch("os.path.exists", return_value=False)
    def test_missing_files_no_crash(self, mock_exists, mock_query):
        """If data files don't exist, function returns silently."""
        from utils.baseline_seeder import seed_baseline_profile

        seed_baseline_profile()
        mock_query.assert_not_called()
