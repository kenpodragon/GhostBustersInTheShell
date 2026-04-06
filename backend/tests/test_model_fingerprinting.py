import pytest
from utils.heuristics.model_signatures import check_model_fingerprint


class TestModelFingerprinting:
    """Cross-model phrase fingerprinting: detect model-specific AI tells."""

    def test_claude_signature_detected(self):
        sentence = "It's worth noting that this approach has both strengths and weaknesses."
        score, patterns = check_model_fingerprint(sentence)
        assert score > 0
        assert any(p.get("model") == "claude" for p in patterns)

    def test_gpt_signature_detected(self):
        sentence = "Certainly! Let me delve into this topic for you."
        score, patterns = check_model_fingerprint(sentence)
        assert score > 0
        assert any(p.get("model") == "gpt" for p in patterns)

    def test_gemini_signature_detected(self):
        sentence = "Here's a breakdown of the key takeaways from the report."
        score, patterns = check_model_fingerprint(sentence)
        assert score > 0
        assert any(p.get("model") == "gemini" for p in patterns)

    def test_human_sentence_no_match(self):
        sentence = "I grabbed a coffee and walked to the park yesterday."
        score, patterns = check_model_fingerprint(sentence)
        assert score == 0
        assert patterns == []

    def test_case_insensitive_matching(self):
        sentence = "IT'S WORTH NOTING that things are changing."
        score, patterns = check_model_fingerprint(sentence)
        assert score > 0

    def test_multiple_matches_compound(self):
        sentence = "Certainly! It's worth noting that we should delve deeper."
        score, patterns = check_model_fingerprint(sentence)
        assert score >= 30

    def test_returns_tuple_format(self):
        sentence = "Just a normal sentence."
        score, patterns = check_model_fingerprint(sentence)
        assert isinstance(score, (int, float))
        assert isinstance(patterns, list)

    def test_pattern_has_model_attribution(self):
        sentence = "Certainly! This is straightforward."
        score, patterns = check_model_fingerprint(sentence)
        for p in patterns:
            assert "model" in p
            assert p["model"] in ("claude", "gpt", "gemini")
            assert "matched" in p
