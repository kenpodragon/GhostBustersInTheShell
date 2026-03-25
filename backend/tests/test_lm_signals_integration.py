"""Integration tests for Phase 3.8 LM signals in the detection pipeline."""
import pytest
from utils.detector import detect_ai_patterns, detect_ai_patterns_detailed

AI_SLOP = """In today's rapidly evolving digital landscape, artificial intelligence has emerged as a transformative force that is fundamentally reshaping how organizations approach innovation and strategic decision-making. By leveraging cutting-edge machine learning algorithms and sophisticated neural network architectures, businesses can unlock unprecedented opportunities for growth and operational excellence. The seamless integration of these technologies into existing workflows enables organizations to streamline processes, enhance productivity, and deliver exceptional value to stakeholders across the entire ecosystem. Furthermore, the convergence of cloud computing and artificial intelligence creates a paradigm shift that empowers enterprises to harness data-driven insights for competitive advantage. This holistic approach to digital transformation ensures sustainable growth while fostering a culture of continuous improvement and innovation across all organizational levels."""

HUMAN_TEXT = """I wrote my first poem when I was eleven. It was terrible — something about a dog we'd had that ran away. Mom found it under my mattress and didn't say anything, just left it there. Years later she told me she'd cried reading it. Not because it was good. Because I'd tried. That's the thing about writing nobody tells you. The first draft is always garbage. You sit there staring at the screen, or the page if you're old-school like me, and nothing comes out right. But you keep going. Sometimes at 2am with cold coffee. Sometimes in the car, pulled over because a sentence hit you. It's not romantic. It's work. Hard, lonely, occasionally beautiful work."""

LM_SIGNAL_PATTERNS = (
    "compression_ratio_sentence", "compression_ratio_document",
    "repetition_density", "ngram_perplexity", "ngram_burstiness",
    "zipf_deviation_v2", "mattr_v2", "ttr_variance",
)

OLD_SIGNAL_PATTERNS = ("compression_ratio", "zipf_deviation", "mattr", "mattr_low", "mattr_uniform")


class TestLmSignalsOff:
    def test_no_lm_patterns_by_default(self):
        result = detect_ai_patterns(AI_SLOP)
        lm_patterns = [p for p in result.get("patterns", [])
                       if p.get("pattern", "") in LM_SIGNAL_PATTERNS]
        assert len(lm_patterns) == 0

    def test_old_signals_still_work_when_off(self):
        result = detect_ai_patterns(AI_SLOP, use_lm_signals=False)
        assert "score" in result or "overall_score" in result
        score = result.get("score", result.get("overall_score"))
        assert isinstance(score, (int, float))


class TestLmSignalsOn:
    def test_produces_results(self):
        result = detect_ai_patterns(AI_SLOP, use_lm_signals=True)
        score = result.get("score", result.get("overall_score"))
        assert score is not None
        assert isinstance(score, (int, float))

    def test_detailed_works(self):
        result = detect_ai_patterns_detailed(AI_SLOP, use_lm_signals=True)
        score = result.get("score", result.get("overall_score"))
        assert score is not None

    def test_human_text_reasonable_score(self):
        result = detect_ai_patterns(HUMAN_TEXT, use_lm_signals=True)
        score = result.get("score", result.get("overall_score"))
        assert score is not None
        assert score < 80

    def test_empty_text(self):
        result = detect_ai_patterns("", use_lm_signals=True)
        score = result.get("score", result.get("overall_score"))
        assert score == 0

    def test_old_signals_skipped_when_on(self):
        result = detect_ai_patterns_detailed(AI_SLOP, use_lm_signals=True)
        all_patterns = result.get("patterns", [])
        old_found = [p for p in all_patterns if p.get("pattern", "") in OLD_SIGNAL_PATTERNS]
        assert len(old_found) == 0, f"Old signals found: {old_found}"
