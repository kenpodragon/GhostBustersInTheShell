"""Tests for rewritten voice generator — outputs profile_elements format."""
import pytest
from utils.voice_generator import generate_voice_profile


@pytest.fixture
def sample_text():
    base = (
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
        "There's a broader point here about craftsmanship that I keep coming back to. "
        "Good code isn't just functional — it's maintainable, readable, and honest. "
        "It tells the next person exactly what it's doing and why. Bad code lies to "
        "you. It says one thing and does another. I've spent more hours unraveling "
        "other people's clever abstractions than I'd like to admit.\n\n"
        "Documentation is underrated. I know everyone says that. I also know that "
        "almost nobody actually writes good documentation, including me. But when you "
        "come back to a project after six months and there's a clear README, a "
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
    return base


class TestGenerateProfile:
    def test_returns_dict_of_elements(self, sample_text):
        result = generate_voice_profile(sample_text)
        assert isinstance(result, dict)
        assert "contraction_rate" in result
        assert "avg_sentence_length" in result
        assert "flesch_kincaid_grade" in result

    def test_element_structure(self, sample_text):
        result = generate_voice_profile(sample_text)
        el = result["contraction_rate"]
        assert "category" in el
        assert "element_type" in el
        assert "weight" in el
        assert "tags" in el
        assert el["element_type"] in ("directional", "metric")

    def test_readability_metrics_present(self, sample_text):
        result = generate_voice_profile(sample_text)
        for metric in ["flesch_kincaid_grade", "flesch_reading_ease", "gunning_fog_index",
                        "coleman_liau_index", "smog_index", "automated_readability_index"]:
            assert metric in result, f"Missing readability metric: {metric}"
            assert result[metric]["element_type"] == "metric"
            assert result[metric]["target_value"] is not None

    def test_determinism(self, sample_text):
        r1 = generate_voice_profile(sample_text)
        r2 = generate_voice_profile(sample_text)
        for key in r1:
            assert r1[key]["weight"] == r2[key]["weight"], f"Non-deterministic: {key}"
            if r1[key].get("target_value") is not None:
                assert r1[key]["target_value"] == r2[key]["target_value"]

    def test_minimum_word_count(self):
        with pytest.raises(ValueError, match="200"):
            generate_voice_profile("Too short to analyze.")

    def test_punctuation_elements(self, sample_text):
        result = generate_voice_profile(sample_text)
        assert "em_dash_usage" in result
        assert "exclamation_rate" in result
        # em dashes appear in sample text
        assert result["em_dash_usage"]["weight"] > 0

    def test_vocabulary_elements(self, sample_text):
        result = generate_voice_profile(sample_text)
        assert "vocabulary_richness" in result
        assert "avg_word_length" in result
        assert result["avg_word_length"]["element_type"] == "metric"

    def test_weights_in_range(self, sample_text):
        result = generate_voice_profile(sample_text)
        for name, el in result.items():
            assert 0.0 <= el["weight"] <= 1.0, f"{name} weight out of range: {el['weight']}"

    def test_all_have_tags(self, sample_text):
        result = generate_voice_profile(sample_text)
        for name, el in result.items():
            has_valid_tag = ("python-extractable" in el["tags"] or
                            "spacy-extractable" in el["tags"])
            assert has_valid_tag, f"{name} missing extractable tag"
