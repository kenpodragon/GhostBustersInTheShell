"""Tests for AI phrase detection heuristic (Phase 3.6)."""
import pytest
from utils.heuristics.ai_phrases import (
    check_ai_phrases,
    check_ai_phrases_sentence,
    AI_PHRASES,
    _COMPILED_PATTERNS,
)


class TestAIPhrases:
    def test_returns_score_and_patterns(self, ai_text):
        score, patterns = check_ai_phrases(ai_text)
        assert isinstance(score, (int, float))
        assert isinstance(patterns, list)

    def test_ai_text_detects_phrases(self, ai_text):
        """The ai_text fixture contains several AI phrases — should score."""
        score, patterns = check_ai_phrases(ai_text)
        assert score > 0
        assert len(patterns) > 0

    def test_human_text_no_phrases(self, human_text):
        """Human text should have zero or very low AI phrase hits."""
        score, patterns = check_ai_phrases(human_text)
        assert score == 0

    def test_short_text_returns_zero(self, short_text):
        score, _ = check_ai_phrases(short_text)
        assert score == 0

    def test_vague_abstractions_detected(self):
        text = (
            "Understanding the intricacies of machine learning requires patience. "
            "The landscape of artificial intelligence is changing rapidly, and "
            "a wide range of applications have emerged in recent years. "
            "The cornerstone of modern AI is large-scale data processing, which "
            "continues to transform the fabric of society in fundamental ways. "
            "Researchers have published thousands of papers on this evolving topic."
        )
        score, patterns = check_ai_phrases(text)
        assert score > 0
        detail_text = " ".join(p["detail"] for p in patterns)
        assert "vague abstraction" in detail_text

    def test_false_depth_detected(self):
        text = (
            "It's worth noting that the situation has changed significantly. "
            "Given the fact that many organizations are struggling with this, "
            "it is essential to consider alternative approaches. "
            "This raises important questions about the future of work, "
            "though there's no one-size-fits-all answer to these challenges. "
            "It is important to understand that progress takes time and effort."
        )
        score, patterns = check_ai_phrases(text)
        assert score > 0
        detail_text = " ".join(p["detail"] for p in patterns)
        assert "false depth" in detail_text

    def test_metaphor_cliches_detected(self):
        text = (
            "This project serves as a testament to the team's dedication. "
            "Their work paves the way for future innovation and growth. "
            "AI plays a crucial role in shaping these outcomes for everyone. "
            "The initiative bridges the gap between theory and practice, and "
            "is widely considered to be at the forefront of the industry today."
        )
        score, patterns = check_ai_phrases(text)
        assert score > 0
        detail_text = " ".join(p["detail"] for p in patterns)
        assert "metaphor cliche" in detail_text

    def test_corporate_action_detected(self):
        text = (
            "We must unlock the potential of our workforce to succeed. "
            "By fostering a culture of innovation, we can push the boundaries "
            "of what is possible. Teams should embark on a journey to discover "
            "new opportunities. Leaders must navigate the complexities of the "
            "modern workplace while laying the groundwork for sustainable growth."
        )
        score, patterns = check_ai_phrases(text)
        assert score > 0
        detail_text = " ".join(p["detail"] for p in patterns)
        assert "corporate action" in detail_text

    def test_hedging_fillers_detected(self):
        text = (
            "One could argue that the approach is too conservative. "
            "That being said, it depends on various factors beyond our control. "
            "In light of this, we should reconsider our strategy. "
            "With that in mind, the team decided to pivot their approach. "
            "At the end of the day, results are what matter most to us all."
        )
        score, patterns = check_ai_phrases(text)
        assert score > 0
        detail_text = " ".join(p["detail"] for p in patterns)
        assert "hedging filler" in detail_text

    def test_no_overlap_double_counting(self):
        """Longer phrases should prevent shorter overlapping matches."""
        text = (
            "It's worth noting that progress requires consistent effort. "
            "A testament to the team's success can be seen in these results. "
            "Simply put, this approach works better than what we had before. "
            "We need a broader perspective to make informed decisions going forward. "
            "The long-term implications of these findings remain to be seen here."
        )
        score, patterns = check_ai_phrases(text)
        # Count total matched phrases across all pattern entries
        phrase_mentions = sum(
            p["detail"].count('"') // 2 for p in patterns
        )
        # Should not double-count "a testament to" inside "a testament to the"
        assert phrase_mentions >= 2

    def test_score_scales_with_count(self):
        """More phrases should give higher score."""
        one_phrase = (
            "The project serves as a testament to the team's hard work. "
            "Everyone contributed their unique skills to make it happen on time. "
            "The deadline was tight but we managed to ship the feature by Friday. "
            "Next quarter we plan to expand the product to international markets."
        )
        many_phrases = (
            "It's worth noting that the intricacies of machine learning require "
            "careful consideration. This serves as a testament to the field's "
            "complexity, and it plays a crucial role in shaping outcomes. "
            "One could argue that we must unlock the potential of AI. "
            "In light of this, fostering a culture of innovation paves the way "
            "for sustainable growth across the entire technology landscape."
        )
        score_one, _ = check_ai_phrases(one_phrase)
        score_many, _ = check_ai_phrases(many_phrases)
        assert score_many > score_one

    def test_case_insensitive(self):
        text = (
            "IT'S WORTH NOTING THAT this approach has been validated many times. "
            "THE INTRICACIES OF the system are well documented in our wiki. "
            "A TESTAMENT TO the engineering team's skill and determination here. "
            "Multiple stakeholders reviewed the proposal before final approval came. "
            "The quarterly report showed significant improvement across all metrics."
        )
        score, _ = check_ai_phrases(text)
        assert score > 0


class TestAIPhrasesSentence:
    def test_single_sentence_with_phrase(self):
        sentence = "It's worth noting that the results were impressive."
        score, patterns = check_ai_phrases_sentence(sentence)
        assert score > 0
        assert any("ai_phrase" == p["pattern"] for p in patterns)

    def test_single_sentence_no_phrase(self):
        sentence = "I grabbed coffee and fixed the bug before standup."
        score, patterns = check_ai_phrases_sentence(sentence)
        assert score == 0
        assert len(patterns) == 0

    def test_multiple_phrases_in_sentence(self):
        sentence = (
            "It's worth noting that this serves as a testament to the team's "
            "ability to navigate the complexities of modern software."
        )
        score, patterns = check_ai_phrases_sentence(sentence)
        assert score > 0
        assert len(patterns) >= 2

    def test_no_minimum_word_count(self):
        """Sentence-level check has no minimum word count."""
        sentence = "A testament to great work."
        score, patterns = check_ai_phrases_sentence(sentence)
        assert score > 0


class TestPhraseDictionary:
    def test_dictionary_not_empty(self):
        assert len(AI_PHRASES) > 100

    def test_all_categories_present(self):
        categories = {cat for _, cat in AI_PHRASES}
        assert "vague_abstraction" in categories
        assert "false_depth" in categories
        assert "metaphor_cliche" in categories
        assert "corporate_action" in categories
        assert "hedging_filler" in categories

    def test_patterns_compiled(self):
        assert len(_COMPILED_PATTERNS) == len(AI_PHRASES)

    def test_sorted_longest_first(self):
        """Phrases should be sorted longest first for greedy matching."""
        lengths = [len(phrase) for phrase, _ in AI_PHRASES]
        assert lengths == sorted(lengths, reverse=True)
