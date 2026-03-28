"""Tests for voice fidelity scoring module."""
import pytest
from unittest.mock import patch, MagicMock
from utils.voice_fidelity_scorer import score_fidelity


class TestScoreFidelityQuantitative:
    """Quantitative mode: re-parse generated text, compare to profile."""

    def test_returns_quantitative_structure(self, long_human_text, sample_profile_elements):
        result = score_fidelity(
            generated_text=long_human_text,
            profile_elements=sample_profile_elements,
            mode="quantitative",
        )
        assert result["mode"] == "quantitative"
        assert "aggregate_similarity" in result
        assert "element_count" in result
        assert "elements_matched" in result
        assert "elements_missing" in result
        assert "per_element" in result
        assert isinstance(result["per_element"], list)

    def test_aggregate_similarity_is_0_to_1(self, long_human_text, sample_profile_elements):
        result = score_fidelity(
            generated_text=long_human_text,
            profile_elements=sample_profile_elements,
            mode="quantitative",
        )
        assert 0.0 <= result["aggregate_similarity"] <= 1.0

    def test_per_element_has_required_fields(self, long_human_text, sample_profile_elements):
        result = score_fidelity(
            generated_text=long_human_text,
            profile_elements=sample_profile_elements,
            mode="quantitative",
        )
        for elem in result["per_element"]:
            assert "name" in elem
            assert "category" in elem
            assert "element_type" in elem
            assert "profile_value" in elem
            assert "generated_value" in elem
            assert "similarity" in elem
            assert "weight" in elem

    def test_per_element_similarity_is_0_to_1(self, long_human_text, sample_profile_elements):
        result = score_fidelity(
            generated_text=long_human_text,
            profile_elements=sample_profile_elements,
            mode="quantitative",
        )
        for elem in result["per_element"]:
            assert 0.0 <= elem["similarity"] <= 1.0, (
                f"{elem['name']}: similarity {elem['similarity']} out of range"
            )

    def test_element_count_matches_profile(self, long_human_text, sample_profile_elements):
        result = score_fidelity(
            generated_text=long_human_text,
            profile_elements=sample_profile_elements,
            mode="quantitative",
        )
        assert result["element_count"] == len(sample_profile_elements)

    def test_identical_text_high_similarity(self, long_human_text):
        """Parsing the same text as both profile and generated should score high."""
        from utils.voice_generator import generate_voice_profile
        profile_dict = generate_voice_profile(long_human_text)
        # Convert to list[dict] format matching DB rows
        profile_elements = []
        for name, elem in profile_dict.items():
            profile_elements.append({
                "name": name,
                "category": elem["category"],
                "element_type": elem["element_type"],
                "direction": elem.get("direction"),
                "weight": elem["weight"],
                "target_value": elem.get("target_value"),
            })

        result = score_fidelity(
            generated_text=long_human_text,
            profile_elements=profile_elements,
            mode="quantitative",
        )
        assert result["aggregate_similarity"] > 0.95, (
            f"Same text should score >0.95, got {result['aggregate_similarity']}"
        )
        assert result["elements_missing"] == 0

    def test_missing_elements_counted(self, long_human_text):
        """Elements in profile but not in parsed output should be counted."""
        fake_elements = [
            {
                "name": "totally_fake_element_xyz",
                "category": "idiosyncratic",
                "element_type": "metric",
                "direction": None,
                "weight": 0.5,
                "target_value": 99.99,
            },
        ]
        result = score_fidelity(
            generated_text=long_human_text,
            profile_elements=fake_elements,
            mode="quantitative",
        )
        assert result["elements_missing"] == 1
        assert result["elements_matched"] == 0
        assert result["aggregate_similarity"] == 0.0, (
            "All-missing profile should have 0.0 aggregate similarity"
        )


class TestScoreFidelityValidation:
    """Input validation tests."""

    def test_quantitative_requires_profile_elements(self, long_human_text):
        with pytest.raises(ValueError, match="profile_elements"):
            score_fidelity(
                generated_text=long_human_text,
                profile_elements=None,
                mode="quantitative",
            )

    def test_quantitative_requires_generated_text(self, sample_profile_elements):
        with pytest.raises(ValueError, match="generated_text"):
            score_fidelity(
                generated_text=None,
                profile_elements=sample_profile_elements,
                mode="quantitative",
            )

    def test_invalid_mode_raises(self, long_human_text, sample_profile_elements):
        with pytest.raises(ValueError, match="mode"):
            score_fidelity(
                generated_text=long_human_text,
                profile_elements=sample_profile_elements,
                mode="invalid",
            )

    def test_qualitative_requires_sample_text(self, long_human_text):
        with pytest.raises(ValueError, match="sample_text"):
            score_fidelity(
                generated_text=long_human_text,
                mode="qualitative",
            )

    def test_both_requires_all_inputs(self, long_human_text):
        with pytest.raises(ValueError, match="profile_elements"):
            score_fidelity(
                generated_text=long_human_text,
                sample_text="some text",
                mode="both",
            )


class TestScoreFidelityQualitative:
    """Qualitative mode: AI comparison of generated vs original text."""

    def test_returns_qualitative_structure(self, long_human_text):
        mock_response = {
            "matches": ["Tone matches well"],
            "gaps": ["Missing rhetorical questions"],
            "overall_assessment": "Good but not great.",
        }
        with patch(
            "utils.voice_fidelity_scorer._call_ai_qualitative",
            return_value=mock_response,
        ):
            result = score_fidelity(
                generated_text=long_human_text,
                sample_text="Original author sample text here.",
                mode="qualitative",
            )
        assert result["mode"] == "qualitative"
        assert isinstance(result["matches"], list)
        assert isinstance(result["gaps"], list)
        assert "overall_assessment" in result

    def test_qualitative_passes_texts_to_ai(self, long_human_text):
        mock_response = {
            "matches": [],
            "gaps": [],
            "overall_assessment": "N/A",
        }
        with patch(
            "utils.voice_fidelity_scorer._call_ai_qualitative",
            return_value=mock_response,
        ) as mock_ai:
            score_fidelity(
                generated_text=long_human_text,
                sample_text="Original text.",
                mode="qualitative",
            )
        mock_ai.assert_called_once()
        call_args = mock_ai.call_args
        assert call_args[0][0] == long_human_text  # generated_text
        assert call_args[0][1] == "Original text."  # sample_text


class TestScoreFidelityBoth:
    """Combined mode: quantitative + qualitative."""

    def test_returns_both_structure(self, long_human_text, sample_profile_elements):
        mock_response = {
            "matches": ["Good tone"],
            "gaps": ["Missing humor"],
            "overall_assessment": "Decent match.",
        }
        with patch(
            "utils.voice_fidelity_scorer._call_ai_qualitative",
            return_value=mock_response,
        ):
            result = score_fidelity(
                generated_text=long_human_text,
                profile_elements=sample_profile_elements,
                sample_text="Original text.",
                mode="both",
            )
        assert result["mode"] == "both"
        assert "quantitative" in result
        assert "qualitative" in result
        assert result["quantitative"]["mode"] == "quantitative"
        assert result["qualitative"]["mode"] == "qualitative"

    def test_both_passes_quant_scores_to_qualitative(self, long_human_text, sample_profile_elements):
        mock_response = {
            "matches": [],
            "gaps": [],
            "overall_assessment": "N/A",
        }
        with patch(
            "utils.voice_fidelity_scorer._call_ai_qualitative",
            return_value=mock_response,
        ) as mock_ai:
            score_fidelity(
                generated_text=long_human_text,
                profile_elements=sample_profile_elements,
                sample_text="Original text.",
                mode="both",
            )
        call_args = mock_ai.call_args
        # Third positional arg should be quant_scores dict
        assert call_args[0][2] is not None
        assert call_args[0][2]["mode"] == "quantitative"
