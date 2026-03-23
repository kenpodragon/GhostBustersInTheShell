"""Tests for the scoring engine."""
import pytest
from utils.heuristics.scoring import (
    combine_signals,
    estimate_confidence,
    detect_genre,
)


class TestCombineSignals:
    """Weighted Bayesian signal combination."""

    def test_empty_signals_returns_zero(self):
        assert combine_signals({}) == 0

    def test_single_signal(self):
        result = combine_signals({"buzzwords": 50})
        assert 0 < result <= 100

    def test_high_weight_signal_dominates(self):
        high = combine_signals({"compression_ratio": 40})  # weight 0.8
        low = combine_signals({"emoji_density": 40})  # weight 0.3
        assert high > low

    def test_multiple_signals_boost_score(self):
        one = combine_signals({"buzzwords": 30})
        three = combine_signals({"buzzwords": 30, "hedge_words": 30, "transitions": 30})
        assert three > one

    def test_score_capped_at_100(self):
        signals = {name: 80 for name in [
            "buzzwords", "compression_ratio", "burrows_delta",
            "yules_k", "zipf_deviation", "hedge_words"
        ]}
        assert combine_signals(signals) <= 100

    def test_zero_signals_ignored(self):
        with_zeros = combine_signals({"buzzwords": 40, "hedge_words": 0, "transitions": 0})
        without_zeros = combine_signals({"buzzwords": 40})
        assert with_zeros == without_zeros


class TestEstimateConfidence:
    """Confidence interval estimation."""

    def test_returns_tuple(self):
        low, high = estimate_confidence(50, signal_count=5, word_count=200)
        assert isinstance(low, (int, float))
        assert isinstance(high, (int, float))

    def test_more_signals_narrows_interval(self):
        low_few, high_few = estimate_confidence(50, signal_count=2, word_count=200)
        low_many, high_many = estimate_confidence(50, signal_count=8, word_count=200)
        assert (high_few - low_few) > (high_many - low_many)

    def test_more_words_narrows_interval(self):
        low_short, high_short = estimate_confidence(50, signal_count=5, word_count=100)
        low_long, high_long = estimate_confidence(50, signal_count=5, word_count=500)
        assert (high_short - low_short) > (high_long - low_long)

    def test_bounds_within_0_100(self):
        low, high = estimate_confidence(95, signal_count=3, word_count=200)
        assert low >= 0
        assert high <= 100


class TestDetectGenre:
    """Automatic genre detection for baseline selection."""

    def test_returns_string(self, ai_text):
        genre = detect_genre(ai_text)
        assert isinstance(genre, str)
        assert genre in ("general", "academic", "casual", "business", "creative", "resume")

    def test_casual_text_detected(self, human_text):
        genre = detect_genre(human_text)
        assert genre == "casual"

    def test_academic_text_detected(self, academic_text):
        genre = detect_genre(academic_text)
        assert genre == "academic"
