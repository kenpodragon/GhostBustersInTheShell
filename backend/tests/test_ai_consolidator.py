"""Tests for AI observation consolidation engine."""
import pytest
import json
from unittest.mock import patch, MagicMock
from utils.ai_consolidator import (
    consolidate_observations,
    _aggregate_metric_descriptions,
    _aggregate_discovered_patterns,
    _fallback_raw_prompts,
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


class TestFallbackRawPrompts:
    def test_wraps_prompts(self):
        prompts = [{"prompt": "dry humor", "confidence": 0.8}]
        result = _fallback_raw_prompts(prompts)
        assert len(result) == 1
        assert result[0]["prompt"] == "dry humor"
        assert result[0]["frequency"] == 1
        assert result[0]["source_prompts"] == ["dry humor"]
        assert result[0]["confidence"] == 0.8


class TestConsolidateObservations:
    """Integration tests that need DB. Use inline db_conn fixture."""

    @pytest.fixture(autouse=True)
    def db_conn(self):
        """Set up test DB connection and clean up after."""
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
        from db import init_pool, execute
        try:
            init_pool()
        except Exception:
            pass
        yield
        # Clean up test data
        try:
            execute("DELETE FROM ai_parse_observations WHERE profile_id = 1")
        except Exception:
            pass

    @patch("utils.ai_consolidator._get_provider")
    def test_consolidation_with_ai(self, mock_get_provider):
        from db import execute, query_one
        mock_provider = MagicMock()
        mock_provider._run_cli.return_value = {
            "consolidated_prompts": [
                {"prompt": "Uses dry humor", "source_prompts": ["dry humor", "deadpan comedy"], "frequency": 2, "confidence": 0.85},
            ]
        }
        mock_get_provider.return_value = mock_provider

        # Need a valid document_id — use an existing one or insert
        doc = query_one("SELECT id FROM documents LIMIT 1")
        if not doc:
            doc = query_one(
                "INSERT INTO documents (filename, file_type, original_text, purpose) VALUES ('test.txt', 'text', 'test', 'analysis') RETURNING id"
            )
        doc_id = doc["id"]

        execute(
            """INSERT INTO ai_parse_observations (profile_id, document_id, qualitative_prompts, metric_descriptions, discovered_patterns)
               VALUES (%s, %s, %s::jsonb, %s::jsonb, %s::jsonb)""",
            (1, doc_id,
             json.dumps([{"prompt": "dry humor", "confidence": 0.8}]),
             json.dumps([{"element": "comma_rate", "value": 0.42, "description": "Heavy commas", "ai_assessment": "accurate"}]),
             json.dumps([])),
        )

        result = consolidate_observations(profile_id=1)
        assert "consolidated_prompts" in result
        assert result["observation_count"] == 1

    @patch("utils.ai_consolidator._get_provider")
    def test_consolidation_without_ai(self, mock_get_provider):
        from db import execute, query_one
        mock_get_provider.return_value = None

        doc = query_one("SELECT id FROM documents LIMIT 1")
        if not doc:
            doc = query_one(
                "INSERT INTO documents (filename, file_type, original_text, purpose) VALUES ('test.txt', 'text', 'test', 'analysis') RETURNING id"
            )
        doc_id = doc["id"]

        execute(
            """INSERT INTO ai_parse_observations (profile_id, document_id, qualitative_prompts, metric_descriptions, discovered_patterns)
               VALUES (%s, %s, %s::jsonb, %s::jsonb, %s::jsonb)""",
            (1, doc_id,
             json.dumps([{"prompt": "dry humor", "confidence": 0.8}]),
             json.dumps([]),
             json.dumps([])),
        )

        result = consolidate_observations(profile_id=1)
        assert result["consolidated_prompts"][0]["prompt"] == "dry humor"
        assert result["consolidated_prompts"][0]["frequency"] == 1

    def test_empty_observations(self):
        result = consolidate_observations(profile_id=99999)
        assert result["observation_count"] == 0
        assert result["consolidated_prompts"] == []
