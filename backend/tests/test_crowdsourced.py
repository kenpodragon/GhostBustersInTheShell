"""Tests for crowdsourced AI tell heuristics."""
import pytest
from utils.heuristics.crowdsourced import (
    check_em_dash_overuse,
    check_ai_opening_phrases,
    check_closing_summary,
    check_question_exclamation_absence,
    check_oxford_comma_consistency,
    check_bullet_subheading_overuse,
    check_digression_absence,
    check_consensus_middle,
)


class TestEmDashOveruse:
    def test_returns_score_and_patterns(self, ai_text):
        score, patterns = check_em_dash_overuse(ai_text)
        assert isinstance(score, (int, float))
        assert isinstance(patterns, list)

    def test_em_dash_heavy_text_scores(self):
        text = (
            "The project — which had been delayed for several months — was finally complete. "
            "Our team — consisting of engineers and designers from multiple departments — delivered "
            "the solution — a robust platform for managing customer data — on time and under budget. "
            "The results — both quantitative and qualitative in their assessment — exceeded all "
            "expectations that the leadership team had originally set for the initiative."
        )
        score, _ = check_em_dash_overuse(text)
        assert score > 0

    def test_normal_text_no_flag(self, human_text):
        score, _ = check_em_dash_overuse(human_text)
        assert score == 0


class TestAIOpeningPhrases:
    def test_ai_text_scores(self):
        text = (
            "In today's rapidly evolving digital landscape, companies must adapt. "
            "In the world of modern technology, innovation drives success. "
            "When it comes to business strategy, agility is key."
        )
        score, _ = check_ai_opening_phrases(text)
        assert score > 0

    def test_human_text_low_score(self, human_text):
        score, _ = check_ai_opening_phrases(human_text)
        assert score == 0


class TestClosingSummary:
    def test_summary_detected(self):
        text = (
            "Some content here about the topic at hand. "
            "The analysis reveals several important findings. "
            "Multiple factors contribute to the overall outcome. "
            "In conclusion, by leveraging these strategies, organizations "
            "can position themselves for long-term success."
        )
        score, _ = check_closing_summary(text)
        assert score > 0

    def test_no_summary_no_flag(self, human_text):
        score, _ = check_closing_summary(human_text)
        assert score == 0


class TestQuestionExclamationAbsence:
    def test_no_questions_flags(self):
        text = (
            "The system provides excellent performance. It handles all cases efficiently. "
            "Users report high satisfaction levels. The implementation is straightforward. "
            "Results demonstrate clear improvements. The approach is well-validated. "
            "Documentation covers all scenarios. Testing confirms reliability."
        )
        score, _ = check_question_exclamation_absence(text)
        assert score > 0

    def test_questions_present_no_flag(self, human_text):
        score, _ = check_question_exclamation_absence(human_text)
        assert score == 0

    def test_short_text_returns_zero(self, short_text):
        score, _ = check_question_exclamation_absence(short_text)
        assert score == 0


class TestOxfordCommaConsistency:
    def test_returns_score_and_patterns(self, ai_text):
        score, patterns = check_oxford_comma_consistency(ai_text)
        assert isinstance(score, (int, float))
        assert isinstance(patterns, list)


class TestBulletSubheadingOveruse:
    def test_heavy_structure_scores(self):
        text = (
            "## Introduction\n\n"
            "Key points:\n"
            "- First item in the list\n"
            "- Second item in the list\n"
            "- Third item in the list\n\n"
            "## Details\n\n"
            "More points:\n"
            "- Another bullet point\n"
            "- Yet another bullet\n\n"
            "## Conclusion\n\n"
            "Final thoughts on the matter."
        )
        score, _ = check_bullet_subheading_overuse(text)
        assert score > 0

    def test_prose_no_flag(self, human_text):
        score, _ = check_bullet_subheading_overuse(human_text)
        assert score == 0


class TestDigressionAbsence:
    def test_returns_score_and_patterns(self, ai_text):
        score, patterns = check_digression_absence(ai_text)
        assert isinstance(score, (int, float))
        assert isinstance(patterns, list)

    def test_ai_text_scores_higher(self, ai_text, human_text):
        ai_score, _ = check_digression_absence(ai_text)
        human_score, _ = check_digression_absence(human_text)
        assert ai_score >= human_score


class TestConsensusMiddle:
    def test_returns_score_and_patterns(self, ai_text):
        score, patterns = check_consensus_middle(ai_text)
        assert isinstance(score, (int, float))
        assert isinstance(patterns, list)

    def test_ai_text_scores_higher(self, ai_text, human_text):
        ai_score, _ = check_consensus_middle(ai_text)
        human_score, _ = check_consensus_middle(human_text)
        assert ai_score >= human_score
