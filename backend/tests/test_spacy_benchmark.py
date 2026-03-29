"""Benchmark: measure parsing overhead of spaCy Tier 2 elements.

Run with: pytest tests/test_spacy_benchmark.py -v -s
The -s flag is important to see the printed timing output.
"""
import time
import pytest
import utils.voice_generator as vg
from utils.voice_generator import generate_voice_profile


def _generate_text(word_count: int) -> str:
    """Generate repeating sample text of approximately word_count words."""
    block = (
        "I've been writing code for years now, and honestly? The best part isn't the "
        "clever algorithms or the fancy frameworks. It's when you finally fix that one "
        "bug that's been haunting you for three days straight. You know the one — where "
        "you've tried everything, read every Stack Overflow answer, and you're about to "
        "give up. Then at 2am, you spot it. A missing semicolon. Or a variable spelled "
        "wrong. Something so stupid you want to cry. "
        "My coworker Dave — he's the worst about this. He'll spend six hours debugging "
        "something, refuse all help, then sheepishly admit he had a typo in a config "
        "file. Every. Single. Time. We've started a betting pool. "
        "But here's the thing about programming that nobody tells you when you're "
        "starting out: it's not really about the code. It's about communication. The "
        "code is just the medium. You're really trying to explain your thinking to "
        "whoever reads it next — which is usually future-you, six months later. "
    )
    block_words = len(block.split())
    repeats = max(1, word_count // block_words)
    text = " ".join([block] * repeats)
    return text


class TestParsingOverhead:
    """Measure wall-clock time with and without spaCy across text sizes."""

    @pytest.mark.parametrize("word_count,label", [
        (700, "~650 words"),
        (5000, "5K words"),
        (50000, "50K words"),
    ])
    def test_benchmark_with_spacy(self, word_count, label):
        """Time generate_voice_profile WITH spaCy."""
        text = _generate_text(word_count)

        # Warm up spaCy model (first load is slower)
        vg._get_spacy_nlp()

        start = time.perf_counter()
        result = generate_voice_profile(text)
        elapsed = time.perf_counter() - start

        element_count = len(result)
        actual_words = len(text.split())
        print(f"\n  WITH spaCy | {label} ({actual_words} actual): "
              f"{elapsed:.3f}s | {element_count} elements")
        assert element_count == 60

    @pytest.mark.parametrize("word_count,label", [
        (700, "~650 words"),
        (5000, "5K words"),
        (50000, "50K words"),
    ])
    def test_benchmark_without_spacy(self, word_count, label):
        """Time generate_voice_profile WITHOUT spaCy (fallback mode)."""
        text = _generate_text(word_count)
        from unittest.mock import patch

        with patch.object(vg, "_spacy_available", False), \
             patch.object(vg, "_nlp", None):
            start = time.perf_counter()
            result = generate_voice_profile(text)
            elapsed = time.perf_counter() - start

        element_count = len(result)
        actual_words = len(text.split())
        print(f"\n  WITHOUT spaCy | {label} ({actual_words} actual): "
              f"{elapsed:.3f}s | {element_count} elements")
        assert element_count == 54
