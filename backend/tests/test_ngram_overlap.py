import pytest
from utils.heuristics.ngram_overlap import compute_ngram_overlap


class TestNgramOverlap:
    def test_identical_texts_return_high_overlap(self):
        text = "The quick brown fox jumps over the lazy dog near the river bank."
        overlap, label, warning = compute_ngram_overlap(text, text)
        assert overlap > 0.9
        assert label == "high"

    def test_completely_different_texts_return_low(self):
        original = "The quick brown fox jumps over the lazy dog near the river bank."
        rewrite = "Quantum computing leverages superposition and entanglement for parallel processing."
        overlap, label, warning = compute_ngram_overlap(original, rewrite)
        assert overlap < 0.4
        assert label == "low"

    def test_synonym_swap_returns_moderate_to_high(self):
        original = "The technology is transforming how businesses operate in the modern workplace."
        rewrite = "The innovation is changing how companies function in the current workplace."
        overlap, label, warning = compute_ngram_overlap(original, rewrite)
        assert overlap >= 0.3

    def test_structural_rewrite_returns_low(self):
        original = "The company reported strong earnings. Revenue increased by twenty percent. Analysts were pleased."
        rewrite = "Pleased analysts noted the twenty percent revenue increase that drove strong earnings at the company."
        overlap, label, warning = compute_ngram_overlap(original, rewrite)
        assert overlap < 0.7

    def test_short_text_handled(self):
        overlap, label, warning = compute_ngram_overlap("Hello.", "Hi.")
        assert isinstance(overlap, float)
        assert label in ("low", "moderate", "high")

    def test_empty_text_returns_zero(self):
        overlap, label, warning = compute_ngram_overlap("", "")
        assert overlap == 0.0

    def test_returns_correct_format(self):
        overlap, label, warning = compute_ngram_overlap("Some text here.", "Other text here.")
        assert isinstance(overlap, float)
        assert isinstance(label, str)
        assert isinstance(warning, str)
        assert 0.0 <= overlap <= 1.0
