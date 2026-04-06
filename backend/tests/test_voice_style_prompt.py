import pytest
from unittest.mock import patch, MagicMock
from utils.voice_profile_service import VoiceProfileService


class TestGetVoiceStylePrompt:
    def setup_method(self):
        self.svc = VoiceProfileService.__new__(VoiceProfileService)

    @patch.object(VoiceProfileService, 'get_active_stack')
    @patch('utils.voice_profile_service.generate_style_brief')
    def test_returns_prompt_from_active_stack(self, mock_brief, mock_stack):
        mock_stack.return_value = {
            "baseline": {"id": 1295, "name": "Stephen"},
            "overlays": [],
            "resolved_elements": [{"name": "contraction_rate", "target_value": 0.72}],
            "prompts": [{"prompt_text": "Use personal asides"}]
        }
        mock_brief.return_value = "Write conversationally. Use contractions. {text}"

        result = self.svc.get_voice_style_prompt()

        assert result["prompt"] == "Write conversationally. Use contractions."
        assert "{text}" not in result["prompt"]
        assert result["profile_name"] == "Stephen"
        assert result["element_count"] == 1
        assert result["prompt_count"] == 1
        mock_brief.assert_called_once()
        call_kwargs = mock_brief.call_args[1]
        assert call_kwargs["mode"] == "voice"

    @patch.object(VoiceProfileService, 'get_profile_summary')
    @patch.object(VoiceProfileService, '_get_elements')
    @patch.object(VoiceProfileService, '_get_prompts')
    @patch('utils.voice_profile_service.generate_style_brief')
    def test_uses_specified_baseline_id(self, mock_brief, mock_prompts, mock_elements, mock_summary):
        mock_summary.return_value = {"id": 999, "name": "Custom"}
        mock_elements.return_value = [{"name": "el1"}, {"name": "el2"}]
        mock_prompts.return_value = [{"prompt_text": "Be formal"}]
        mock_brief.return_value = "Be formal and precise. {text}"

        result = self.svc.get_voice_style_prompt(baseline_id=999)

        assert result["profile_name"] == "Custom"
        assert result["element_count"] == 2
        assert "{text}" not in result["prompt"]

    @patch.object(VoiceProfileService, 'get_active_stack')
    def test_error_when_no_active_profile(self, mock_stack):
        mock_stack.return_value = {"baseline": None, "overlays": [], "resolved_elements": [], "prompts": []}

        with pytest.raises(ValueError, match="No active voice profile"):
            self.svc.get_voice_style_prompt()

    @patch.object(VoiceProfileService, 'get_active_stack')
    @patch('utils.voice_profile_service.generate_style_brief')
    def test_strips_text_placeholder(self, mock_brief, mock_stack):
        mock_stack.return_value = {
            "baseline": {"id": 1, "name": "Test"},
            "overlays": [],
            "resolved_elements": [],
            "prompts": []
        }
        mock_brief.return_value = "Some instructions.\n\nHere is the text to rewrite:\n{text}\n\nEnd."

        result = self.svc.get_voice_style_prompt()

        assert "{text}" not in result["prompt"]
