# code/backend/tests/conftest.py
"""Shared test fixtures for AI detection heuristics."""
import pytest


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "integration: marks tests that require a running database or external services")


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


@pytest.fixture
def ai_text_multipar():
    """Multi-paragraph AI text for testing paragraph-level analysis."""
    return (
        "In today's rapidly evolving digital landscape, organizations must leverage "
        "innovative strategies to navigate the complexities of modern business. "
        "Furthermore, it is essential to streamline operations and harness the power "
        "of cutting-edge technology.\n\n"
        "Additionally, stakeholders should foster a culture of collaboration and "
        "transparency. Moreover, the implementation of robust frameworks can "
        "significantly enhance overall performance. It is worth noting that these "
        "approaches have proven to be highly effective.\n\n"
        "In conclusion, a comprehensive and strategic approach is paramount to "
        "achieving meaningful outcomes. Ultimately, by embracing these transformative "
        "solutions, businesses can position themselves for long-term success."
    )


@pytest.fixture
def sample_profile_elements():
    """Minimal voice profile elements for fidelity scoring tests."""
    return [
        {
            "name": "flesch_reading_ease",
            "category": "idiosyncratic",
            "element_type": "metric",
            "direction": None,
            "weight": 0.6615,
            "target_value": 66.15,
        },
        {
            "name": "avg_sentence_length",
            "category": "structural",
            "element_type": "metric",
            "direction": None,
            "weight": 0.5,
            "target_value": 18.5,
        },
        {
            "name": "comma_rate",
            "category": "idiosyncratic",
            "element_type": "metric",
            "direction": None,
            "weight": 0.2332,
            "target_value": 0.93,
        },
        {
            "name": "first_person_usage",
            "category": "idiosyncratic",
            "element_type": "directional",
            "direction": "more",
            "weight": 0.39,
            "target_value": None,
        },
        {
            "name": "contraction_rate",
            "category": "lexical",
            "element_type": "directional",
            "direction": "more",
            "weight": 0.65,
            "target_value": None,
        },
    ]


@pytest.fixture
def long_human_text():
    """Human-written text, 600+ words, for voice generator parsing."""
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
        "had some strong opinions about that last Tuesday.\n\n"
        "The thing about working on legacy systems is that everyone has an opinion "
        "but nobody wants to actually own the migration. I've seen this pattern at "
        "every company I've worked at. Someone will say 'we should rewrite this in "
        "Rust' or 'let's move to microservices' and then six months later we're "
        "still running the same PHP monolith because, surprise, rewrites are hard "
        "and the business doesn't stop shipping features just because engineering "
        "wants to play with new toys. Don't get me wrong — I love new tech as much "
        "as the next person. But I've learned the hard way that the best refactor "
        "is the one that actually ships.\n\n"
        "Last week I was debugging a race condition in our payment processing "
        "pipeline and I found a comment from 2017 that said 'TODO: fix this race "
        "condition.' Classic. The original author had even left a note explaining "
        "exactly what the problem was and how to fix it. They just... never did. "
        "And now here I am, five years later, dealing with the exact scenario they "
        "predicted. There's a lesson in there somewhere about technical debt and "
        "procrastination, but I'm too tired to articulate it.\n\n"
        "Speaking of being tired, I've been pulling late nights all week trying to "
        "get our CI pipeline under 30 minutes. We were at 47 minutes last month, "
        "which is absurd for a codebase our size. The main culprits were the "
        "integration tests — turns out someone had added a sleep(5) in a loop that "
        "ran for every test case. When I found it I literally laughed out loud in "
        "my empty apartment at 11pm. That's the kind of thing that makes you "
        "question your life choices. But hey, we're down to 22 minutes now, so "
        "I'll take the win.\n\n"
        "My manager keeps asking me to write documentation for the systems I work "
        "on, and intellectually I know she's right. Future me will thank present "
        "me for writing good docs. But in the moment, when I've just spent four "
        "hours tracking down a bug, the last thing I want to do is write a "
        "confluence page about it. I usually compromise by leaving detailed commit "
        "messages and inline comments. It's not perfect but it's better than "
        "nothing, which is what existed before I joined this team.\n\n"
        "Anyway, I think the plan for next sprint is to tackle the auth module "
        "refactor in phases. Start with the token validation, then move to session "
        "management, then finally the OAuth integration. Each phase should be "
        "independently deployable so we don't have a big bang release. I've been "
        "burned by those before and I don't intend to repeat the experience. "
        "Small, incremental changes. That's the way."
    )
