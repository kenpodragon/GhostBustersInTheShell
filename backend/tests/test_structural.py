"""Tests for structural analysis heuristics."""
import pytest
from utils.heuristics.structural import (
    check_zipf_deviation,
    check_compression_ratio,
    check_sentence_opener_pos,
    check_word_length_distribution,
    check_char_ngram_profile,
)


class TestZipfDeviation:
    """Natural language follows Zipf's law. AI text deviates."""

    def test_returns_score_and_patterns(self, ai_text):
        score, patterns = check_zipf_deviation(ai_text)
        assert isinstance(score, (int, float))
        assert isinstance(patterns, list)

    def test_ai_text_scores_higher(self, ai_text, human_text):
        ai_score, _ = check_zipf_deviation(ai_text)
        human_score, _ = check_zipf_deviation(human_text)
        assert ai_score >= human_score

    def test_short_text_returns_zero(self, short_text):
        score, _ = check_zipf_deviation(short_text)
        assert score == 0


class TestCompressionRatio:
    """AI text compresses more uniformly (lower entropy)."""

    def test_returns_score_and_patterns(self, ai_text):
        score, patterns = check_compression_ratio(ai_text)
        assert isinstance(score, (int, float))
        assert isinstance(patterns, list)

    def test_ai_text_scores_higher(self, ai_text, human_text):
        ai_score, _ = check_compression_ratio(ai_text)
        human_score, _ = check_compression_ratio(human_text)
        assert ai_score >= human_score

    def test_short_text_returns_zero(self, short_text):
        score, _ = check_compression_ratio(short_text)
        assert score == 0


class TestSentenceOpenerPOS:
    """AI over-uses certain sentence starters."""

    def test_returns_score_and_patterns(self, ai_text):
        score, patterns = check_sentence_opener_pos(ai_text)
        assert isinstance(score, (int, float))
        assert isinstance(patterns, list)

    def test_ai_text_scores_higher(self, ai_text, human_text):
        ai_score, _ = check_sentence_opener_pos(ai_text)
        human_score, _ = check_sentence_opener_pos(human_text)
        assert ai_score >= human_score


class TestWordLengthDistribution:
    """AI text clusters word lengths around 5-8 chars."""

    def test_returns_score_and_patterns(self, ai_text):
        score, patterns = check_word_length_distribution(ai_text)
        assert isinstance(score, (int, float))
        assert isinstance(patterns, list)

    def test_ai_text_scores_higher(self, ai_text, human_text):
        ai_score, _ = check_word_length_distribution(ai_text)
        human_score, _ = check_word_length_distribution(human_text)
        assert ai_score >= human_score

    def test_short_text_returns_zero(self, short_text):
        score, _ = check_word_length_distribution(short_text)
        assert score == 0


class TestCharNgramProfile:
    """Character trigram entropy differs between AI and human text."""

    def test_returns_score_and_patterns(self, ai_text):
        score, patterns = check_char_ngram_profile(ai_text)
        assert isinstance(score, (int, float))
        assert isinstance(patterns, list)

    def test_ai_text_scores_higher(self, ai_text, human_text):
        ai_score, _ = check_char_ngram_profile(ai_text)
        human_score, _ = check_char_ngram_profile(human_text)
        assert ai_score >= human_score

    def test_short_text_returns_zero(self, short_text):
        score, _ = check_char_ngram_profile(short_text)
        assert score == 0
