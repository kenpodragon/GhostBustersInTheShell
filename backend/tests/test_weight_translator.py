"""Tests for weight-to-language translator."""
import pytest
from utils.weight_translator import translate_elements_to_english, translate_element


class TestTranslateElement:
    def test_directional_high_weight(self):
        el = {"name": "contraction_rate", "element_type": "directional", "direction": "more", "weight": 0.9}
        result = translate_element(el)
        assert isinstance(result, str)
        assert len(result) > 10
        assert any(word in result.lower() for word in ["heavily", "strongly", "frequently", "consistently"])

    def test_directional_low_weight(self):
        el = {"name": "contraction_rate", "element_type": "directional", "direction": "more", "weight": 0.2}
        result = translate_element(el)
        assert any(word in result.lower() for word in ["occasionally", "sometimes", "slightly", "sparingly"])

    def test_directional_less(self):
        el = {"name": "passive_voice_rate", "element_type": "directional", "direction": "less", "weight": 0.8}
        result = translate_element(el)
        assert any(word in result.lower() for word in ["avoid", "minimize", "rarely", "reduce", "never"])

    def test_metric_element(self):
        el = {"name": "flesch_kincaid_grade", "element_type": "metric", "target_value": 8.2, "weight": 0.8}
        result = translate_element(el)
        assert "8.2" in result

    def test_determinism(self):
        el = {"name": "em_dash_usage", "element_type": "directional", "direction": "more", "weight": 0.6}
        r1 = translate_element(el)
        r2 = translate_element(el)
        assert r1 == r2

    def test_unknown_element_name(self):
        el = {"name": "custom_weird_thing", "element_type": "directional", "direction": "more", "weight": 0.5}
        result = translate_element(el)
        assert "custom weird thing" in result.lower()


class TestTranslateBatch:
    def test_translate_multiple(self):
        elements = [
            {"name": "contraction_rate", "element_type": "directional", "direction": "more", "weight": 0.7, "category": "lexical"},
            {"name": "flesch_kincaid_grade", "element_type": "metric", "target_value": 8.0, "weight": 0.8, "category": "idiosyncratic"},
        ]
        result = translate_elements_to_english(elements)
        assert isinstance(result, str)
        assert "contraction" in result.lower()
        assert "8.0" in result

    def test_empty_list(self):
        result = translate_elements_to_english([])
        assert result == ""

    def test_grouped_by_category(self):
        elements = [
            {"name": "em_dash_usage", "element_type": "directional", "direction": "more", "weight": 0.5, "category": "idiosyncratic"},
            {"name": "contraction_rate", "element_type": "directional", "direction": "more", "weight": 0.5, "category": "lexical"},
        ]
        result = translate_elements_to_english(elements)
        lines = result.split("\n")
        assert len(lines) == 2
        # Idiosyncratic comes before lexical alphabetically (i < l)
        assert "em dash" in lines[0].lower()
        assert "contraction" in lines[1].lower()
