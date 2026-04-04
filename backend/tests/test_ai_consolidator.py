"""Tests for AI observation consolidation engine."""
import pytest
import json
from unittest.mock import patch, MagicMock
from utils.ai_consolidator import (
    consolidate_observations,
    _aggregate_metric_descriptions,
    _aggregate_discovered_patterns,
    _fallback_from_clusters,
)


class TestAggregateMetricDescriptions:
    def test_single_observation(self):
        observations = [
            {"metric_descriptions": [
                {"element": "comma_rate", "value": 0.42, "description": "Heavy comma usage", "ai_assessment": "accurate"},
            ]}
        ]
        result = _aggregate_metric_descriptions(observations)
        assert len(result) == 1
        assert result[0]["element"] == "comma_rate"
        assert result[0]["agreement_count"] == 1
        assert result[0]["flagged_misleading"] is False

    def test_multiple_observations_same_element(self):
        observations = [
            {"metric_descriptions": [{"element": "comma_rate", "value": 0.42, "description": "Heavy commas", "ai_assessment": "accurate"}]},
            {"metric_descriptions": [{"element": "comma_rate", "value": 0.45, "description": "Lots of commas", "ai_assessment": "accurate"}]},
            {"metric_descriptions": [{"element": "comma_rate", "value": 0.40, "description": "Misleading comma count", "ai_assessment": "misleading"}]},
        ]
        result = _aggregate_metric_descriptions(observations)
        comma = [r for r in result if r["element"] == "comma_rate"][0]
        assert comma["agreement_count"] == 2
        assert comma["disagreement_count"] == 1
        assert comma["flagged_misleading"] is True

    def test_empty_observations(self):
        assert _aggregate_metric_descriptions([]) == []


class TestAggregateDiscoveredPatterns:
    def test_deduplicates_by_name(self):
        observations = [
            {"discovered_patterns": [{"pattern": "Uses tricolon", "suggested_element_name": "tricolon_usage", "description": "Three-part lists"}]},
            {"discovered_patterns": [{"pattern": "Tricolon structures", "suggested_element_name": "tricolon_usage", "description": "Three-part structures"}]},
        ]
        result = _aggregate_discovered_patterns(observations)
        assert len(result) == 1
        assert result[0]["occurrences"] == 2

    def test_single_occurrence(self):
        observations = [
            {"discovered_patterns": [{"pattern": "Rare pattern", "suggested_element_name": "rare_thing", "description": "Only once"}]},
        ]
        result = _aggregate_discovered_patterns(observations)
        assert result[0]["occurrences"] == 1


class TestFallbackFromClusters:
    def test_returns_significant_clusters(self):
        clusters = [{"representative": "dry humor", "frequency": 5, "avg_confidence": 0.8, "members": []}]
        result = _fallback_from_clusters(clusters)
        assert len(result) == 1
        assert result[0]["prompt"] == "dry humor"
        assert result[0]["frequency"] == 5
        assert result[0]["confidence"] == 0.8

    def test_filters_low_frequency(self):
        clusters = [{"representative": "rare thing", "frequency": 2, "avg_confidence": 0.9, "members": []}]
        result = _fallback_from_clusters(clusters)
        assert len(result) == 0


class TestConsolidateObservations:
    """Integration tests that need DB. Creates a temporary profile for isolation."""

    TEST_PROFILE_ID = None

    @pytest.fixture(autouse=True)
    def db_conn(self):
        """Set up test DB connection, create temp profile, clean up after."""
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
        from db import init_pool, execute, query_one
        try:
            init_pool()
        except Exception:
            pass
        # Create a temporary voice profile for test isolation
        row = query_one(
            "INSERT INTO voice_profiles (name, description) VALUES ('_test_consolidator', 'temp') RETURNING id"
        )
        self.__class__.TEST_PROFILE_ID = row["id"]
        yield
        # Clean up test data
        try:
            execute("DELETE FROM ai_parse_observations WHERE profile_id = %s", (self.TEST_PROFILE_ID,))
            execute("DELETE FROM profile_prompts WHERE voice_profile_id = %s", (self.TEST_PROFILE_ID,))
            execute("DELETE FROM profile_elements WHERE voice_profile_id = %s", (self.TEST_PROFILE_ID,))
            execute("DELETE FROM voice_profiles WHERE id = %s", (self.TEST_PROFILE_ID,))
        except Exception:
            pass

    def _insert_observations(self, count, prompt_text="dry humor", confidence=0.8):
        """Insert multiple observations with the same prompt to form a significant cluster."""
        from db import execute, query_one
        doc = query_one("SELECT id FROM documents LIMIT 1")
        if not doc:
            doc = query_one(
                "INSERT INTO documents (filename, file_type, original_text, purpose) VALUES ('test.txt', 'text', 'test', 'analysis') RETURNING id"
            )
        doc_id = doc["id"]
        for _ in range(count):
            execute(
                """INSERT INTO ai_parse_observations (profile_id, document_id, qualitative_prompts, metric_descriptions, discovered_patterns)
                   VALUES (%s, %s, %s::jsonb, %s::jsonb, %s::jsonb)""",
                (self.TEST_PROFILE_ID, doc_id,
                 json.dumps([{"prompt": prompt_text, "confidence": confidence}]),
                 json.dumps([{"element": "comma_rate", "value": 0.42, "description": "Heavy commas", "ai_assessment": "accurate"}]),
                 json.dumps([])),
            )

    @patch("utils.ai_consolidator._get_provider")
    def test_consolidation_with_ai(self, mock_get_provider):
        """Insert 5 observations (meets MIN_FREQUENCY_FOR_AI), verify AI merge is called."""
        mock_provider = MagicMock()
        mock_provider._run_cli.return_value = {
            "consolidated_prompts": [
                {"prompt": "Uses dry humor", "source_prompts": ["dry humor"] * 5, "frequency": 5, "confidence": 0.85},
            ]
        }
        mock_get_provider.return_value = mock_provider

        self._insert_observations(5)
        result = consolidate_observations(profile_id=self.TEST_PROFILE_ID)
        assert "consolidated_prompts" in result
        assert result["observation_count"] == 5
        mock_provider._run_cli.assert_called_once()

    @patch("utils.ai_consolidator._get_provider")
    def test_consolidation_without_ai_significant(self, mock_get_provider):
        """Without AI, significant clusters (freq >= 5) fall back to heuristic output."""
        mock_get_provider.return_value = None
        self._insert_observations(5)

        result = consolidate_observations(profile_id=self.TEST_PROFILE_ID)
        assert len(result["consolidated_prompts"]) == 1
        assert result["consolidated_prompts"][0]["prompt"] == "dry humor"
        assert result["consolidated_prompts"][0]["frequency"] == 5

    @patch("utils.ai_consolidator._get_provider")
    def test_consolidation_below_threshold(self, mock_get_provider):
        """Clusters below MIN_FREQUENCY_FOR_AI produce no consolidated prompts."""
        mock_get_provider.return_value = None
        self._insert_observations(2)

        result = consolidate_observations(profile_id=self.TEST_PROFILE_ID)
        assert result["observation_count"] == 2
        assert result["consolidated_prompts"] == []

    def test_empty_observations(self):
        result = consolidate_observations(profile_id=99999)
        assert result["observation_count"] == 0
        assert result["consolidated_prompts"] == []
