"""Tests for AI voice extraction alongside Python parsing."""
import pytest
from unittest.mock import patch, MagicMock
from utils.ai_voice_extractor import extract_voice_with_ai, AI_EXTRACTION_PROMPT, _format_elements


SAMPLE_TEXT = "The rain fell hard on the tin roof. I remember thinking it sounded like applause."

SAMPLE_ELEMENTS = {
    "avg_sentence_length": {"weight": 0.6, "target_value": 14.5, "category": "syntactic"},
    "comma_rate": {"weight": 0.8, "target_value": 0.42, "category": "character"},
    "sentiment_mean": {"weight": 0.5, "target_value": 0.138, "category": "content"},
}

MOCK_AI_RESPONSE = {
    "qualitative_prompts": [
        {"prompt": "Uses vivid sensory imagery grounded in everyday settings", "confidence": 0.85},
        {"prompt": "Employs dry, self-aware humor through unexpected metaphors", "confidence": 0.78},
    ],
    "metric_descriptions": [
        {"element": "avg_sentence_length", "value": 14.5, "description": "Moderate sentence length", "ai_assessment": "accurate"},
        {"element": "comma_rate", "value": 0.42, "description": "Heavy comma usage", "ai_assessment": "accurate"},
        {"element": "sentiment_mean", "value": 0.138, "description": "Slightly positive baseline", "ai_assessment": "misleading"},
    ],
    "discovered_patterns": [
        {"pattern": "Dash-interrupted asides for comedic timing", "suggested_element_name": "dash_aside_frequency", "description": "Em-dash parenthetical insertions"},
    ],
}


class TestExtractVoiceWithAI:
    @patch("utils.ai_voice_extractor._get_provider")
    def test_successful_extraction(self, mock_get_provider):
        mock_provider = MagicMock()
        mock_provider._run_cli.return_value = MOCK_AI_RESPONSE
        mock_get_provider.return_value = mock_provider

        result = extract_voice_with_ai(SAMPLE_TEXT, SAMPLE_ELEMENTS)

        assert result["status"] == "success"
        assert len(result["qualitative_prompts"]) == 2
        assert result["qualitative_prompts"][0]["confidence"] == 0.85
        assert len(result["metric_descriptions"]) == 3
        assert result["metric_descriptions"][2]["ai_assessment"] == "misleading"
        assert len(result["discovered_patterns"]) == 1
        assert result["raw_ai_response"] == MOCK_AI_RESPONSE

    @patch("utils.ai_voice_extractor._get_provider")
    def test_ai_unavailable_returns_skipped(self, mock_get_provider):
        mock_get_provider.return_value = None

        result = extract_voice_with_ai(SAMPLE_TEXT, SAMPLE_ELEMENTS)

        assert result["status"] == "skipped"
        assert result["qualitative_prompts"] == []
        assert result["metric_descriptions"] == []
        assert result["discovered_patterns"] == []

    @patch("utils.ai_voice_extractor._get_provider")
    def test_ai_error_returns_error_status(self, mock_get_provider):
        mock_provider = MagicMock()
        mock_provider._run_cli.side_effect = Exception("Rate limit exceeded")
        mock_get_provider.return_value = mock_provider

        result = extract_voice_with_ai(SAMPLE_TEXT, SAMPLE_ELEMENTS)

        assert result["status"] == "error"
        assert "Rate limit" in result["error"]

    @patch("utils.ai_voice_extractor._get_provider")
    def test_truncates_long_text(self, mock_get_provider):
        mock_provider = MagicMock()
        mock_provider._run_cli.return_value = MOCK_AI_RESPONSE
        mock_get_provider.return_value = mock_provider

        long_text = "word " * 10000  # ~50K chars
        extract_voice_with_ai(long_text, SAMPLE_ELEMENTS)

        call_args = mock_provider._run_cli.call_args[0][0]
        assert len(call_args) < 25000


class TestFormatElements:
    def test_formats_elements(self):
        result = _format_elements(SAMPLE_ELEMENTS)
        assert "avg_sentence_length: 14.5" in result
        assert "comma_rate: 0.42" in result

    def test_handles_numpy_types(self):
        import numpy as np
        elements = {"test_elem": {"weight": np.float64(0.5), "target_value": np.float64(1.23), "category": "test"}}
        result = _format_elements(elements)
        assert "test_elem: 1.23" in result


class TestPromptTemplate:
    def test_prompt_contains_elements(self):
        prompt = AI_EXTRACTION_PROMPT.format(
            document_text="Sample text",
            element_values="avg_sentence_length: 14.5\ncomma_rate: 0.42",
        )
        assert "avg_sentence_length: 14.5" in prompt
        assert "comma_rate: 0.42" in prompt
