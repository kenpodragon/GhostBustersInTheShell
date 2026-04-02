"""Tests for style_guide_builder module."""
import json
import pytest
from unittest.mock import patch, MagicMock


@pytest.fixture
def sample_elements():
    """Minimal voice profile elements for testing."""
    return [
        {"name": "contraction_rate", "category": "idiosyncratic", "element_type": "directional",
         "direction": "more", "weight": 0.85, "target_value": 0.85},
        {"name": "ellipsis_usage", "category": "idiosyncratic", "element_type": "directional",
         "direction": "more", "weight": 0.058, "target_value": 0.058},
        {"name": "avg_sentence_length", "category": "structural", "element_type": "metric",
         "weight": 0.7, "target_value": 15.5},
        {"name": "em_dash_usage", "category": "idiosyncratic", "element_type": "directional",
         "direction": "more", "weight": 0.038, "target_value": 0.038},
        {"name": "comma_rate", "category": "structural", "element_type": "directional",
         "direction": "more", "weight": 0.6, "target_value": 0.6},
    ]


@pytest.fixture
def mock_routing():
    """Simulated routing dict (keyed by element_name) from _load_routing."""
    return {
        "contraction_rate": {
            "element_name": "contraction_rate", "strategy": "json",
            "best_score": 1.0, "detection_override": None, "enforcement_template": None,
        },
        "ellipsis_usage": {
            "element_name": "ellipsis_usage", "strategy": "targeted_enforcement",
            "best_score": 0.849, "detection_override": None,
            "enforcement_template": "Include {count} ellipses (...) for trailing thoughts or pauses",
        },
        "avg_sentence_length": {
            "element_name": "avg_sentence_length", "strategy": "english",
            "best_score": 0.967, "detection_override": None, "enforcement_template": None,
        },
        "em_dash_usage": {
            "element_name": "em_dash_usage", "strategy": "targeted_enforcement",
            "best_score": 0.0, "detection_override": "detection_wins", "enforcement_template": None,
        },
        "comma_rate": {
            "element_name": "comma_rate", "strategy": "hybrid",
            "best_score": 0.949, "detection_override": None, "enforcement_template": None,
        },
    }


# ---------------------------------------------------------------------------
# TestSectionRouting
# ---------------------------------------------------------------------------

class TestSectionRouting:
    def test_json_elements_in_hard_targets(self, sample_elements, mock_routing):
        from utils.style_guide_builder import build_style_guide
        with patch("utils.style_guide_builder._load_routing", return_value=mock_routing):
            result = build_style_guide(sample_elements)
        assert "Hard Targets" in result
        assert "contraction_rate" in result

    def test_english_elements_in_style_guidance(self, sample_elements, mock_routing):
        from utils.style_guide_builder import build_style_guide
        with patch("utils.style_guide_builder._load_routing", return_value=mock_routing):
            result = build_style_guide(sample_elements)
        assert "Style Guidance" in result
        # avg_sentence_length has strategy=english; translate_element produces "sentence length"
        assert "sentence length" in result.lower()

    def test_hybrid_elements_in_style_guidance(self, sample_elements, mock_routing):
        from utils.style_guide_builder import build_style_guide
        with patch("utils.style_guide_builder._load_routing", return_value=mock_routing):
            result = build_style_guide(sample_elements)
        # comma_rate has strategy=hybrid; should appear in Style Guidance
        assert "comma" in result.lower()

    def test_targeted_elements_in_mandatory_section(self, sample_elements, mock_routing):
        from utils.style_guide_builder import build_style_guide
        with patch("utils.style_guide_builder._load_routing", return_value=mock_routing):
            result = build_style_guide(sample_elements)
        assert "MANDATORY" in result
        # ellipsis_usage has strategy=targeted_enforcement and no detection_wins
        assert "ellips" in result.lower()


# ---------------------------------------------------------------------------
# TestDetectionOverride
# ---------------------------------------------------------------------------

class TestDetectionOverride:
    def test_detection_wins_element_excluded(self, sample_elements, mock_routing):
        from utils.style_guide_builder import build_style_guide
        with patch("utils.style_guide_builder._load_routing", return_value=mock_routing):
            result = build_style_guide(sample_elements)
        # em_dash_usage has detection_wins — must not appear anywhere
        assert "em_dash" not in result
        assert "em dash" not in result.lower()

    def test_voice_wins_element_included(self, sample_elements, mock_routing):
        from utils.style_guide_builder import build_style_guide
        routing_voice_wins = dict(mock_routing)
        routing_voice_wins["em_dash_usage"] = dict(mock_routing["em_dash_usage"])
        routing_voice_wins["em_dash_usage"]["detection_override"] = "voice_wins"
        routing_voice_wins["em_dash_usage"]["enforcement_template"] = "Use {count} em dashes"
        with patch("utils.style_guide_builder._load_routing", return_value=routing_voice_wins):
            result = build_style_guide(sample_elements)
        assert "em dash" in result.lower()


# ---------------------------------------------------------------------------
# TestCountComputation
# ---------------------------------------------------------------------------

class TestCountComputation:
    def test_count_scales_with_word_count(self):
        from utils.style_guide_builder import _compute_count
        element = {"name": "ellipsis_usage", "weight": 0.5, "target_value": 0.5}
        result_short = _compute_count(element, 200)
        result_long = _compute_count(element, 800)
        # Extract numeric value from result strings; longer text should give higher count
        def first_int(s):
            import re
            nums = re.findall(r"\d+", s)
            return int(nums[0]) if nums else 0
        assert first_int(result_long) >= first_int(result_short)

    def test_minimum_count_is_one(self):
        from utils.style_guide_builder import _compute_count
        # Very low weight + very short text should still produce at least "1"
        element = {"name": "ellipsis_usage", "weight": 0.001, "target_value": 0.001}
        result = _compute_count(element, 50)
        import re
        nums = re.findall(r"\d+", result)
        assert nums, "Expected at least one digit in count result"
        assert int(nums[0]) >= 1


# ---------------------------------------------------------------------------
# TestFallback
# ---------------------------------------------------------------------------

class TestFallback:
    def test_empty_routing_falls_back_to_english(self, sample_elements):
        from utils.style_guide_builder import build_style_guide
        with patch("utils.style_guide_builder._load_routing", return_value={}):
            result = build_style_guide(sample_elements)
        assert "Style Guidance" in result
        assert result.strip() != ""

    def test_empty_elements_returns_empty(self):
        from utils.style_guide_builder import build_style_guide
        with patch("utils.style_guide_builder._load_routing", return_value={}):
            result = build_style_guide([])
        assert result == ""


# ---------------------------------------------------------------------------
# TestOutputStructure
# ---------------------------------------------------------------------------

class TestOutputStructure:
    def test_sections_in_correct_order(self, sample_elements, mock_routing):
        from utils.style_guide_builder import build_style_guide
        with patch("utils.style_guide_builder._load_routing", return_value=mock_routing):
            result = build_style_guide(sample_elements)
        hard_pos = result.find("Hard Targets")
        guidance_pos = result.find("Style Guidance")
        mandatory_pos = result.find("MANDATORY")
        assert hard_pos != -1, "Hard Targets section missing"
        assert guidance_pos != -1, "Style Guidance section missing"
        assert mandatory_pos != -1, "MANDATORY section missing"
        assert hard_pos < guidance_pos < mandatory_pos

    def test_enforcement_uses_numbered_list(self, sample_elements, mock_routing):
        from utils.style_guide_builder import build_style_guide
        with patch("utils.style_guide_builder._load_routing", return_value=mock_routing):
            result = build_style_guide(sample_elements)
        # Enforcement section should use numbered list
        assert "1. " in result

    def test_json_section_contains_valid_json(self, sample_elements, mock_routing):
        from utils.style_guide_builder import build_style_guide
        import re
        with patch("utils.style_guide_builder._load_routing", return_value=mock_routing):
            result = build_style_guide(sample_elements)
        # Extract ```json ... ``` block
        match = re.search(r"```json\s*(.*?)\s*```", result, re.DOTALL)
        assert match, "No ```json block found in output"
        parsed = json.loads(match.group(1))
        assert isinstance(parsed, list)
        names = [item["name"] for item in parsed]
        assert "contraction_rate" in names


# ---------------------------------------------------------------------------
# TestSeedRoutingTable
# ---------------------------------------------------------------------------

class TestSeedRoutingTable:
    @patch("utils.style_guide_builder.json.load")
    @patch("builtins.open", create=True)
    @patch("os.path.exists", return_value=True)
    def test_seeds_when_version_is_newer(self, mock_exists, mock_open, mock_json_load):
        from utils.style_guide_builder import seed_routing_table

        mock_json_load.return_value = {
            "version": "1.0.0",
            "routing": [
                {"element_name": "test_el", "strategy": "json", "best_score": 0.9,
                 "detection_override": None, "enforcement_template": None}
            ]
        }

        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value = mock_cur
        # routing_version query returns old version
        mock_cur.fetchone.return_value = ("0.0.0",)

        seed_routing_table(db_conn=mock_conn)

        # Should have called INSERT
        assert mock_cur.execute.call_count >= 2  # SELECT + INSERT + UPDATE
        mock_conn.commit.assert_called_once()

    @patch("utils.style_guide_builder.json.load")
    @patch("builtins.open", create=True)
    @patch("os.path.exists", return_value=True)
    def test_skips_when_version_is_current(self, mock_exists, mock_open, mock_json_load):
        from utils.style_guide_builder import seed_routing_table

        mock_json_load.return_value = {
            "version": "1.0.0",
            "routing": [{"element_name": "test_el", "strategy": "json"}]
        }

        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value = mock_cur
        # routing_version already at 1.0.0
        mock_cur.fetchone.return_value = ("1.0.0",)

        seed_routing_table(db_conn=mock_conn)

        # Should NOT have committed (skipped)
        mock_conn.commit.assert_not_called()
