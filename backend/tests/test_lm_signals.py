"""Tests for Phase 3.8 LM signal functions."""
import pytest
from utils.heuristics.lm_signals import (
    load_corpus, get_genre_baselines, preprocess_text,
    check_compression_ratio_sentence, check_compression_ratio_document,
    check_repetition_density,
    check_ngram_perplexity, check_ngram_burstiness,
    check_zipf_deviation_v2, check_mattr_v2, check_ttr_variance,
)

AI_SLOP = """In today's rapidly evolving digital landscape, artificial intelligence has emerged as a transformative force that is fundamentally reshaping how organizations approach innovation and strategic decision-making. By leveraging cutting-edge machine learning algorithms and sophisticated neural network architectures, businesses can unlock unprecedented opportunities for growth and operational excellence. The seamless integration of these technologies into existing workflows enables organizations to streamline processes, enhance productivity, and deliver exceptional value to stakeholders across the entire ecosystem. Furthermore, the convergence of cloud computing and artificial intelligence creates a paradigm shift that empowers enterprises to harness data-driven insights for competitive advantage. This holistic approach to digital transformation ensures sustainable growth while fostering a culture of continuous improvement and innovation across all organizational levels."""

HUMAN_TEXT = """I wrote my first poem when I was eleven. It was terrible — something about a dog we'd had that ran away. Mom found it under my mattress and didn't say anything, just left it there. Years later she told me she'd cried reading it. Not because it was good. Because I'd tried. That's the thing about writing nobody tells you. The first draft is always garbage. You sit there staring at the screen, or the page if you're old-school like me, and nothing comes out right. But you keep going. Sometimes at 2am with cold coffee. Sometimes in the car, pulled over because a sentence hit you. It's not romantic. It's work. Hard, lonely, occasionally beautiful work."""


# --- Corpus Loading ---

class TestCorpusLoading:
    def test_load_combined_corpus(self):
        corpus = load_corpus("combined")
        assert corpus is not None
        assert "trigrams" in corpus
        assert "floor_logprob" in corpus
        assert isinstance(corpus["trigrams"], dict)
        assert len(corpus["trigrams"]) > 10000
        assert corpus["floor_logprob"] < 0

    def test_load_corpus_caches(self):
        c1 = load_corpus("combined")
        c2 = load_corpus("combined")
        assert c1 is c2

    def test_load_missing_corpus_returns_none(self):
        result = load_corpus("nonexistent")
        assert result is None

    def test_genre_baselines(self):
        baselines = get_genre_baselines()
        assert isinstance(baselines, dict)
        assert len(baselines) > 0
        for genre, stats in baselines.items():
            assert "mattr_mean" in stats
            assert "mattr_std" in stats


# --- Preprocessing ---

class TestPreprocessing:
    def test_strips_urls(self):
        text = "Check out https://example.com/foo for more info"
        result = preprocess_text(text)
        assert "https://example.com" not in result
        assert "check out" in result

    def test_strips_code_blocks(self):
        text = "Here is code:\n```python\nprint('hello')\n```\nAnd more text."
        result = preprocess_text(text)
        assert "print" not in result
        assert "more text" in result

    def test_strips_emails(self):
        text = "Contact user@example.com for details"
        result = preprocess_text(text)
        assert "user@example.com" not in result

    def test_lowercases(self):
        text = "The Quick Brown Fox"
        result = preprocess_text(text)
        assert result == "the quick brown fox"

    def test_strips_non_latin(self):
        text = "This has non-latin chars inside"
        result = preprocess_text(text)
        assert "this has" in result

    def test_empty_text(self):
        assert preprocess_text("") == ""


# --- Category A: Internal Entropy ---

class TestCompressionRatioSentence:
    def test_returns_tuple(self):
        score, patterns = check_compression_ratio_sentence(
            "This is a test sentence with enough words to compress properly for analysis."
        )
        assert isinstance(score, float)
        assert isinstance(patterns, list)

    def test_short_text_returns_zero(self):
        score, patterns = check_compression_ratio_sentence("Too short")
        assert score == 0
        assert patterns == []

    def test_empty_returns_zero(self):
        score, patterns = check_compression_ratio_sentence("")
        assert score == 0

    def test_score_between_0_and_100(self):
        score, _ = check_compression_ratio_sentence(AI_SLOP)
        assert 0 <= score <= 100


class TestCompressionRatioDocument:
    def test_returns_tuple(self):
        score, patterns = check_compression_ratio_document(AI_SLOP)
        assert isinstance(score, float)
        assert isinstance(patterns, list)

    def test_few_sentences_returns_zero(self):
        score, patterns = check_compression_ratio_document("Just one sentence here.")
        assert score == 0

    def test_returns_patterns_when_scoring(self):
        score, patterns = check_compression_ratio_document(AI_SLOP)
        if score > 0:
            assert any("compression" in p.get("pattern", "") for p in patterns)


class TestRepetitionDensity:
    def test_returns_tuple(self):
        score, patterns = check_repetition_density(AI_SLOP)
        assert isinstance(score, float)
        assert isinstance(patterns, list)

    def test_short_text_returns_zero(self):
        score, patterns = check_repetition_density("Too few words here")
        assert score == 0

    def test_repetitive_text_scores_higher(self):
        repetitive = "The cat sat on the mat. The cat sat on the rug. The cat sat on the floor. The cat sat on the bed. The cat sat on the chair. The cat sat on the table."
        varied = "Jazz filled the smoky room. Outside rain hammered the awning. She ordered another whiskey neat. The bartender nodded slowly and reached for the good bottle."
        rep_score, _ = check_repetition_density(repetitive)
        var_score, _ = check_repetition_density(varied)
        assert rep_score >= var_score


# --- Category B: Corpus-Referenced ---

class TestNgramPerplexity:
    def test_returns_tuple(self):
        corpus = load_corpus("combined")
        if corpus is None:
            pytest.skip("Corpus not available")
        score, patterns = check_ngram_perplexity(AI_SLOP, corpus)
        assert isinstance(score, float)
        assert isinstance(patterns, list)

    def test_no_corpus_returns_zero(self):
        score, patterns = check_ngram_perplexity(AI_SLOP, None)
        assert score == 0
        assert patterns == []

    def test_short_text_returns_zero(self):
        corpus = load_corpus("combined")
        if corpus is None:
            pytest.skip("Corpus not available")
        score, patterns = check_ngram_perplexity("Hi", corpus)
        assert score == 0

    def test_scores_between_0_and_100(self):
        corpus = load_corpus("combined")
        if corpus is None:
            pytest.skip("Corpus not available")
        score, _ = check_ngram_perplexity(AI_SLOP, corpus)
        assert 0 <= score <= 100

    def test_coverage_guard_skips_jargon(self):
        corpus = load_corpus("combined")
        if corpus is None:
            pytest.skip("Corpus not available")
        jargon = "xyzzy plugh frobozz quux corge grault garply waldo thud"
        score, patterns = check_ngram_perplexity(jargon, corpus)
        assert score == 0


class TestNgramBurstiness:
    def test_returns_tuple(self):
        corpus = load_corpus("combined")
        if corpus is None:
            pytest.skip("Corpus not available")
        score, patterns = check_ngram_burstiness(AI_SLOP, corpus)
        assert isinstance(score, float)
        assert isinstance(patterns, list)

    def test_no_corpus_returns_zero(self):
        score, patterns = check_ngram_burstiness(AI_SLOP, None)
        assert score == 0

    def test_few_sentences_returns_zero(self):
        corpus = load_corpus("combined")
        if corpus is None:
            pytest.skip("Corpus not available")
        score, _ = check_ngram_burstiness("Just one short sentence.", corpus)
        assert score == 0


# --- Category C: Rehabilitated Stats ---

class TestZipfDeviationV2:
    def test_returns_tuple(self):
        score, patterns = check_zipf_deviation_v2(AI_SLOP)
        assert isinstance(score, float)
        assert isinstance(patterns, list)

    def test_short_text_returns_zero(self):
        score, _ = check_zipf_deviation_v2("Too few words")
        assert score == 0

    def test_scores_between_0_and_100(self):
        score, _ = check_zipf_deviation_v2(AI_SLOP)
        assert 0 <= score <= 100


class TestMattrV2:
    def test_returns_tuple(self):
        baselines = get_genre_baselines()
        score, patterns = check_mattr_v2(AI_SLOP, baselines, "general")
        assert isinstance(score, float)
        assert isinstance(patterns, list)

    def test_short_text_returns_zero(self):
        baselines = get_genre_baselines()
        score, _ = check_mattr_v2("Short text", baselines, "general")
        assert score == 0

    def test_unknown_genre_uses_fallback(self):
        baselines = get_genre_baselines()
        score, patterns = check_mattr_v2(AI_SLOP, baselines, "unknown_genre")
        assert isinstance(score, float)

    def test_empty_baselines_still_works(self):
        score, patterns = check_mattr_v2(AI_SLOP, {}, "general")
        assert isinstance(score, float)


class TestTtrVariance:
    def test_returns_tuple(self):
        score, patterns = check_ttr_variance(AI_SLOP)
        assert isinstance(score, float)
        assert isinstance(patterns, list)

    def test_short_text_returns_zero(self):
        score, _ = check_ttr_variance("Not enough words here for two chunks")
        assert score == 0

    def test_scores_between_0_and_100(self):
        score, _ = check_ttr_variance(AI_SLOP)
        assert 0 <= score <= 100
