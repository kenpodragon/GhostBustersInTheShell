# code/backend/tests/conftest.py
"""Shared test fixtures for AI detection heuristics."""
import pytest


@pytest.fixture
def ai_text():
    """Typical AI-generated text with known AI patterns."""
    return (
        "In today's rapidly evolving digital landscape, organizations must leverage "
        "innovative strategies to navigate the complexities of modern business. "
        "Furthermore, it is essential to streamline operations and harness the power "
        "of cutting-edge technology. Additionally, stakeholders should foster a culture "
        "of collaboration and transparency. Moreover, the implementation of robust "
        "frameworks can significantly enhance overall performance. It is worth noting "
        "that these approaches have proven to be highly effective in driving sustainable "
        "growth. Ultimately, by embracing these transformative solutions, businesses can "
        "position themselves for long-term success in an increasingly competitive marketplace. "
        "However, it is important to acknowledge that challenges remain. Nevertheless, "
        "the potential benefits far outweigh the associated risks. In conclusion, "
        "a comprehensive and strategic approach is paramount to achieving meaningful outcomes."
    )


@pytest.fixture
def human_text():
    """Typical human-written text with natural patterns."""
    return (
        "I've been thinking about this problem for weeks now and I'm not sure "
        "there's a clean answer. My coworker Dave suggested we just rewrite the "
        "whole auth module from scratch — which, honestly? Tempting. But the last "
        "time we did something like that was in 2019 and it took three months "
        "longer than anyone expected. The old code is ugly but it works. "
        "Maybe we could refactor the token validation piece first and see if "
        "that fixes the timeout issues people keep complaining about on Slack. "
        "I dunno. There's also the question of whether we even need JWTs anymore "
        "now that we're behind Cloudflare's zero-trust thing. Sarah in security "
        "had some strong opinions about that last Tuesday."
    )


@pytest.fixture
def short_text():
    """Text too short for reliable detection (<150 words)."""
    return "This is a short sentence. Not much to analyze here."


@pytest.fixture
def academic_text():
    """Formal human academic writing (should NOT false-positive)."""
    return (
        "The results of the longitudinal study indicate a statistically significant "
        "correlation between socioeconomic status and educational attainment (p < 0.01, "
        "n = 2,847). Participants in the lowest income quartile demonstrated markedly "
        "different outcomes compared to their peers, with a mean GPA of 2.31 versus 3.14 "
        "in the highest quartile. These findings are consistent with previous research "
        "by Reardon (2011) and Chetty et al. (2014), though our sample size permits "
        "more granular analysis of intervening variables. Notably, parental education "
        "level emerged as a stronger predictor than household income alone (β = 0.47, "
        "SE = 0.08), suggesting that cultural capital mechanisms may mediate the "
        "relationship more powerfully than pure economic resources."
    )
