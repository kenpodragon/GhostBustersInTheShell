"""Tests for the voice format experiment harness."""
import pytest
import json


def test_load_profile_elements():
    """Harness can load Stephen's 65 elements from the API."""
    from tools.voice_format_harness import load_profile_elements
    elements = load_profile_elements(1295)
    assert len(elements) == 65
    assert all("name" in e for e in elements)
    assert all("target_value" in e or "weight" in e for e in elements)


def test_format_elements_json():
    """Elements can be formatted as JSON for prompts."""
    from tools.voice_format_harness import format_elements_json
    fake_elements = [
        {"name": "contraction_rate", "category": "lexical", "element_type": "metric",
         "target_value": 0.7, "weight": 0.7}
    ]
    result = format_elements_json(fake_elements)
    parsed = json.loads(result)
    assert len(parsed) == 1
    assert parsed[0]["name"] == "contraction_rate"
    assert parsed[0]["target_value"] == 0.7


def test_format_elements_english():
    """Elements can be formatted as English instructions."""
    from tools.voice_format_harness import format_elements_english
    fake_elements = [
        {"name": "contraction_rate", "category": "lexical", "element_type": "metric",
         "direction": "more", "weight": 0.7, "target_value": 0.7}
    ]
    result = format_elements_english(fake_elements)
    assert isinstance(result, str)
    assert len(result) > 0


def test_run_self_assessment_builds_prompt():
    """Self-assessment builds a valid prompt with all 65 elements."""
    from tools.voice_format_harness import load_profile_elements, format_elements_json
    from tools.format_experiments import build_self_assessment_prompt
    elements = load_profile_elements(1295)
    elements_json = format_elements_json(elements)
    prompt = build_self_assessment_prompt(elements_json)
    assert "65 quantitative style elements" in prompt
    assert "contraction_rate" in prompt
    assert "controllable" in prompt
