"""Tests for RulesConfig singleton."""

import pytest
from utils.rules_config import RulesConfig, rules_config


@pytest.fixture(autouse=True)
def reset_singleton():
    """Reset singleton state before each test."""
    rules_config._reset_for_testing()
    yield
    rules_config._reset_for_testing()


# ---- File-based loading tests ----

class TestLoadFromFile:
    def test_load_from_gz_file(self):
        rules_config.load_from_file()
        assert rules_config.is_read_only is True
        assert len(rules_config.weights) > 30
        assert rules_config.weights["sentence_opener_pos"] == 1.0

    def test_load_buzzwords(self):
        rules_config.load_from_file()
        bw = rules_config.buzzwords
        assert "hard_ban_verbs" in bw
        assert "hard_ban_adj" in bw
        assert "hard_ban_filler" in bw
        assert "hard_ban_filler_phrases" in bw
        assert "delve" in bw["hard_ban_verbs"]

    def test_load_ai_phrases(self):
        rules_config.load_from_file()
        assert len(rules_config.ai_phrases) > 0

    def test_load_classification(self):
        rules_config.load_from_file()
        assert rules_config.classification["clean_upper"] == 20

    def test_load_pipeline(self):
        rules_config.load_from_file()
        assert rules_config.pipeline["ai_weight"] == 0.6
        assert rules_config.pipeline["heuristic_weight"] == 0.4

    def test_load_ai_prompt(self):
        rules_config.load_from_file()
        assert isinstance(rules_config.ai_prompt, str)
        assert len(rules_config.ai_prompt) > 100

    def test_load_severity(self):
        rules_config.load_from_file()
        assert "multipliers" in rules_config.severity

    def test_all_buzzwords_flat(self):
        rules_config.load_from_file()
        flat = rules_config.all_buzzwords
        assert isinstance(flat, set)
        assert "delve" in flat
        assert "robust" in flat
        assert len(flat) > 100


# ---- DB loading tests ----

class TestLoadFromDB:
    def test_load_from_db(self):
        """Try load_from_db; skip if DB not available or not seeded."""
        try:
            rules_config.load_from_db()
        except Exception:
            pytest.skip("DB not available or not seeded")
        assert rules_config.is_read_only is False
        assert len(rules_config.weights) > 0

    def test_load_fallback_chain(self):
        """load() succeeds via one path (DB or file)."""
        rules_config.load()
        assert len(rules_config.weights) > 0

    def test_reload(self):
        """reload preserves data."""
        rules_config.load()
        weights_before = dict(rules_config.weights)
        rules_config.reload()
        # After reload, weights should still be populated
        assert len(rules_config.weights) > 0
        # If read-only (file fallback), reload is no-op so data is same
        if rules_config.is_read_only:
            assert rules_config.weights == weights_before


# ---- Singleton tests ----

class TestSingleton:
    def test_singleton_identity(self):
        a = RulesConfig()
        b = RulesConfig()
        assert a is b

    def test_module_singleton_is_same(self):
        assert RulesConfig() is rules_config
