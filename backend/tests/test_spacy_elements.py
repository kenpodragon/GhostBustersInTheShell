"""Tests for Tier 2 spaCy-based voice elements."""
import pytest
from unittest.mock import patch
from utils.voice_generator import generate_voice_profile


@pytest.fixture
def sample_text():
    """Text with known POS characteristics for testing spaCy elements.

    Contains:
    - Adjectives: best, clever, fancy, stupid, worst, good, hard, fast, clear, wrong
    - Adverbs: honestly, finally, straight, sheepishly, really, genuinely, happily
    - Past tense: been, tried, read, spent, switched, started
    - Present tense: is, isn't, are, tells, does, says, know, think
    - Named entities: Dave, Python, Java, TypeScript, Claude, Stack Overflow
    - Passive voice: "is underrated", "was designed", "were built"
    """
    return (
        "I've been writing code for years now, and honestly? The best part isn't the "
        "clever algorithms or the fancy frameworks. It's when you finally fix that one "
        "bug that's been haunting you for three days straight. You know the one — where "
        "you've tried everything, read every Stack Overflow answer, and you're about to "
        "give up. Then at 2am, you spot it. A missing semicolon. Or a variable spelled "
        "wrong. Something so stupid you want to cry.\n\n"
        "My coworker Dave — he's the worst about this. He'll spend six hours debugging "
        "something, refuse all help, then sheepishly admit he had a typo in a config "
        "file. Every. Single. Time. We've started a betting pool on how long it takes "
        "him to ask for a second pair of eyes. Current record is fourteen hours.\n\n"
        "But here's the thing about programming that nobody tells you when you're "
        "starting out: it's not really about the code. It's about communication. The "
        "code is just the medium. You're really trying to explain your thinking to "
        "whoever reads it next — which is usually future-you, six months later, "
        "wondering what the hell past-you was thinking.\n\n"
        "I switched to Python last year after a decade of Java, and the difference "
        "is night and day. Not because Python is 'better' — that's a loaded word in "
        "this industry — but because it lets me think faster. Less boilerplate, more "
        "actual problem-solving. Though I do miss static types sometimes. TypeScript "
        "has spoiled me on the frontend side.\n\n"
        "The whole AI thing is interesting too. I've been using Claude for pair "
        "programming and it's genuinely helpful for boilerplate and test generation. "
        "But I don't trust it for architecture decisions. It'll happily generate a "
        "perfectly structured, well-documented solution that completely misses the "
        "actual problem. You still need the human to say 'wait, that's solving the "
        "wrong thing entirely.'\n\n"
        "Anyway — coffee's getting cold and I've got a PR review to finish. The "
        "junior dev on my team wrote something really clever yesterday and I can't "
        "tell if it's genius or a time bomb. That's the fun part of code review: "
        "being wrong either way is educational.\n\n"
        "Documentation is underrated. It was designed to help future developers. "
        "The best systems were built with care. I know everyone says that. I also know "
        "that almost nobody actually writes good documentation, including me. But when "
        "you come back to a project after six months and there's a clear README, a "
        "sensible folder structure, and comments that explain the non-obvious bits — "
        "you feel a genuine sense of gratitude toward your past self.\n\n"
        "Testing is the same way. Writing tests feels like overhead when you're "
        "moving fast. Then you refactor something, run the test suite, and everything "
        "is green. That feeling is worth every minute you spent writing assertions. "
        "I've converted three skeptics on my team just by showing them that moment.\n\n"
        "The hardest skill in software isn't any particular language or framework. "
        "It's judgment. Knowing when to abstract and when to stay concrete. Knowing "
        "when to optimize and when readable code is fast enough. Knowing when to "
        "refactor and when you're just procrastinating on the hard problem.\n\n"
        "I don't think you can teach judgment directly. You develop it by making "
        "mistakes and being honest with yourself about what went wrong. The engineers "
        "I respect most aren't the ones who never mess up — they're the ones who "
        "can look at their own past decisions clearly and say 'that was the wrong "
        "call, here's what I'd do differently.' That kind of intellectual honesty "
        "is rare and genuinely valuable."
    )


class TestSpacyLazyLoading:
    def test_profile_has_spacy_elements_when_available(self, sample_text):
        result = generate_voice_profile(sample_text)
        assert "adjective_to_noun_ratio" in result
        assert "adverb_density" in result
        assert "verb_tense_past_ratio" in result
        assert "verb_tense_present_ratio" in result
        assert "clause_depth_avg" in result
        assert "named_entity_density" in result

    def test_spacy_elements_have_correct_tags(self, sample_text):
        result = generate_voice_profile(sample_text)
        spacy_elements = [
            "adjective_to_noun_ratio", "adverb_density",
            "verb_tense_past_ratio", "verb_tense_present_ratio",
            "clause_depth_avg", "named_entity_density",
        ]
        for name in spacy_elements:
            assert "spacy-extractable" in result[name]["tags"], f"{name} missing spacy-extractable tag"

    def test_fallback_without_spacy(self, sample_text):
        import utils.voice_generator as vg
        with patch.object(vg, "_spacy_available", False), \
             patch.object(vg, "_nlp", None):
            result = vg.generate_voice_profile(sample_text)
            assert "adjective_to_noun_ratio" not in result
            assert "contraction_rate" in result
            assert len(result) == 51

    def test_element_count_with_spacy(self, sample_text):
        result = generate_voice_profile(sample_text)
        assert len(result) == 57, f"Expected 57 elements, got {len(result)}: {sorted(result.keys())}"


class TestAdjectiveToNounRatio:
    def test_returns_metric_element(self, sample_text):
        result = generate_voice_profile(sample_text)
        el = result["adjective_to_noun_ratio"]
        assert el["element_type"] == "metric"
        assert el["category"] == "syntactic"
        assert 0.0 < el["target_value"] < 2.0

    def test_adjective_heavy_text(self):
        text = " ".join([
            "The beautiful gorgeous magnificent stunning incredible wonderful "
            "amazing fantastic brilliant spectacular house stood on the big tall "
            "wide narrow long hill near the old ancient historic crumbling wall."
        ] * 40)
        result = generate_voice_profile(text)
        assert result["adjective_to_noun_ratio"]["target_value"] > 0.5


class TestAdverbDensity:
    def test_returns_directional_element(self, sample_text):
        result = generate_voice_profile(sample_text)
        el = result["adverb_density"]
        assert el["element_type"] == "directional"
        assert el["category"] == "syntactic"
        assert 0.0 <= el["weight"] <= 1.0


class TestVerbTenseDistribution:
    def test_past_and_present_ratios_exist(self, sample_text):
        result = generate_voice_profile(sample_text)
        past = result["verb_tense_past_ratio"]
        present = result["verb_tense_present_ratio"]
        assert past["element_type"] == "metric"
        assert present["element_type"] == "metric"
        assert past["category"] == "syntactic"
        assert present["category"] == "syntactic"

    def test_ratios_sum_to_at_most_one(self, sample_text):
        result = generate_voice_profile(sample_text)
        total = (result["verb_tense_past_ratio"]["target_value"] +
                 result["verb_tense_present_ratio"]["target_value"])
        assert total <= 1.01, f"Past + present = {total}, expected <= 1.0"


class TestClauseDepth:
    def test_returns_metric_element(self, sample_text):
        result = generate_voice_profile(sample_text)
        el = result["clause_depth_avg"]
        assert el["element_type"] == "metric"
        assert el["category"] == "syntactic"
        assert el["target_value"] >= 1.0

    def test_simple_vs_complex_text(self):
        simple = " ".join(["I like dogs. Dogs are good. Cats are nice. "
                           "Birds fly high. Fish swim fast."] * 100)
        complex_text = " ".join([
            "Although the researchers who had been studying the phenomenon that "
            "was observed by the team which had been assembled by the professor "
            "who specialized in the field that was considered important believed "
            "that the results were significant, they acknowledged limitations."
        ] * 40)
        simple_result = generate_voice_profile(simple)
        complex_result = generate_voice_profile(complex_text)
        assert (complex_result["clause_depth_avg"]["target_value"] >
                simple_result["clause_depth_avg"]["target_value"])


class TestNamedEntityDensity:
    def test_returns_metric_element(self, sample_text):
        result = generate_voice_profile(sample_text)
        el = result["named_entity_density"]
        assert el["element_type"] == "metric"
        assert el["category"] == "lexical"
        assert el["target_value"] >= 0.0

    def test_entity_rich_text(self):
        text = " ".join([
            "Barack Obama met with Angela Merkel in Berlin on Tuesday. "
            "Microsoft and Google announced a partnership with the United Nations. "
            "The New York Times reported that Tesla moved its headquarters to Austin."
        ] * 60)
        result = generate_voice_profile(text)
        assert result["named_entity_density"]["target_value"] > 0.02


class TestPassiveVoiceUpgrade:
    def test_passive_voice_still_exists(self, sample_text):
        result = generate_voice_profile(sample_text)
        assert "passive_voice_rate" in result

    def test_passive_voice_uses_spacy_tag_when_available(self, sample_text):
        result = generate_voice_profile(sample_text)
        assert "spacy-extractable" in result["passive_voice_rate"]["tags"]

    def test_passive_heavy_text(self):
        text = " ".join([
            "The ball was thrown by the boy. The cake was eaten by the children. "
            "The book was written by a famous author. The song was sung beautifully. "
            "The house was built in the last century. The letter was delivered today."
        ] * 90)
        result = generate_voice_profile(text)
        assert result["passive_voice_rate"]["weight"] > 0.3
