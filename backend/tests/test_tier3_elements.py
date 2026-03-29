"""Tests for Tier 3 NLP-based voice elements."""
import pytest
from unittest.mock import patch
from utils.voice_generator import generate_voice_profile


@pytest.fixture
def positive_text():
    """Text with clearly positive sentiment throughout. ~600 words, 6 paragraphs."""
    return (
        "I absolutely love working on this project. Every morning I wake up excited "
        "to tackle the next challenge. The team is fantastic — everyone brings something "
        "unique to the table. We celebrate every small win together, and the energy in "
        "the room is infectious. Yesterday we hit a major milestone and the whole office "
        "erupted in cheers. It was one of those moments that reminds you why you do this.\n\n"
        "The best part about our approach is how clean the architecture turned out. "
        "Every component fits together beautifully. The API is elegant and intuitive. "
        "Our users have been sending in wonderful feedback — they genuinely enjoy using "
        "the product. One customer wrote us a heartfelt letter thanking us for making "
        "their daily workflow so much better. That kind of feedback is pure gold.\n\n"
        "Our latest feature release was a massive success. Downloads tripled in the "
        "first week. The reviews were overwhelmingly positive. People are recommending "
        "us to their friends and colleagues. The growth has been organic and genuine — "
        "no marketing tricks, just a great product that speaks for itself. We're thrilled "
        "with the trajectory and optimistic about the future.\n\n"
        "The technical improvements have been equally impressive. Performance is up 40% "
        "since last quarter. Bug reports are down to almost zero. The codebase is clean, "
        "well-tested, and a joy to work with. New developers onboard in days, not weeks. "
        "Everything just works, and that's a wonderful feeling after months of hard work.\n\n"
        "Looking ahead, I'm incredibly optimistic. We have a brilliant roadmap planned. "
        "Each upcoming feature builds on our strengths and addresses real user needs. "
        "The market opportunity is huge and we're perfectly positioned to capture it. "
        "Our investors are delighted with the progress. The board meeting last week was "
        "all smiles and congratulations. It's rare to feel this good about where things "
        "are heading, but everything is lining up perfectly.\n\n"
        "Even the small things bring joy. The office plants are thriving. The coffee "
        "machine works perfectly. Team lunches are fun and lively. Someone brought "
        "homemade cookies yesterday and they were absolutely delicious. It's the kind "
        "of positive environment where great work happens naturally. I feel genuinely "
        "lucky to be part of this team and this journey. Every day is better than the "
        "last, and I wouldn't trade it for anything in the world.\n\n"
        "The culture here is genuinely special and I notice it every single day. "
        "People support each other without hesitation and celebrate each other's wins "
        "with real enthusiasm. Collaboration is effortless because everyone trusts each "
        "other completely. New ideas get a fair hearing and the best ones actually get "
        "built. We have a shared sense of purpose that makes the work feel meaningful. "
        "I've never felt so energized and inspired at a job before. The future looks "
        "bright and I'm so grateful to be on this incredible journey with such "
        "wonderful, talented, and passionate people. Every challenge we face together "
        "makes us stronger and more capable as a cohesive and resilient team. "
        "Honestly this is the best job I have ever had in my entire professional life."
    )


@pytest.fixture
def negative_text():
    """Text with clearly negative sentiment throughout. ~600 words."""
    return (
        "This project has been a complete disaster from the start. Every deadline "
        "missed, every estimate wrong, every assumption flawed. The codebase is a "
        "tangled mess of spaghetti code that nobody wants to touch. Bug reports pile "
        "up faster than we can fix them. The team is burned out and morale is at an "
        "all-time low. Yesterday's deployment broke production for three hours.\n\n"
        "The architecture is fundamentally broken. Technical debt has accumulated to "
        "the point where simple changes take weeks. The API is inconsistent and poorly "
        "documented. Users are furious — our support inbox is overflowing with complaints. "
        "One customer publicly called our product 'the worst software they've ever used' "
        "and honestly, it's hard to disagree with that assessment.\n\n"
        "Our last release was catastrophic. We lost 30% of our user base in a single "
        "week. The reviews are brutal and getting worse. People are actively warning "
        "others to stay away. The negative press has been devastating — every tech blog "
        "is writing about our failures. We're hemorrhaging money and running out of "
        "options fast. The situation feels hopeless.\n\n"
        "The technical problems keep getting worse. Performance has degraded 60% since "
        "the last update. Memory leaks crash the server daily. The test suite is broken "
        "and nobody has time to fix it. New developers take months to understand the "
        "codebase, and most quit before they do. The whole thing is falling apart.\n\n"
        "Looking ahead, I see nothing but problems. The roadmap is unrealistic and "
        "nobody believes in it. Each proposed feature would require rewriting half the "
        "system. The market is shrinking and competitors are eating our lunch. Our "
        "investors are furious and threatening to pull funding. The board meeting was "
        "a nightmare of accusations and finger-pointing. Nobody has a plan to fix this.\n\n"
        "Even the small things are terrible. The office is depressing and poorly "
        "maintained. The coffee machine has been broken for weeks. Team meetings are "
        "tense and unproductive. Someone complained about the awful lunch options and "
        "started a heated argument. It's the kind of toxic environment where nothing "
        "good can happen. I dread coming to work every morning and I know I'm not "
        "the only one who feels that way. Everything about this situation is awful.\n\n"
        "The culture has become completely toxic and it shows in every interaction. "
        "People blame each other constantly and trust has completely broken down. "
        "Collaboration is impossible because everyone is defensive and territorial. "
        "New ideas get shot down immediately without any real consideration. "
        "There is no shared vision and nobody believes the mission statement anymore. "
        "I have never felt so demoralized and exhausted at any job in my entire life. "
        "The future looks bleak and I deeply regret joining this failing organization "
        "with such difficult, unmotivated, and disengaged people. Every setback "
        "tears the team further apart and leaves everyone feeling more bitter and deeply resentful. "
        "Honestly this is without question the absolute worst job I have ever suffered through in "
        "my entire long professional career and I would absolutely never recommend it to anyone under any circumstances whatsoever."
    )


@pytest.fixture
def mixed_sentiment_text():
    """Text alternating between positive and negative sentences. ~600 words."""
    return (
        "The project started beautifully with a clear vision. Then everything fell "
        "apart when the lead developer quit. We rallied together and rebuilt the core "
        "in record time. Unfortunately the new architecture had serious performance "
        "issues. The team worked overtime and fixed every single bottleneck. But the "
        "client changed requirements at the last minute and we had to start over.\n\n"
        "Our users love the new interface — it's intuitive and fast. The backend, "
        "however, is a nightmare of technical debt. Customer satisfaction scores are "
        "at an all-time high. Meanwhile, developer satisfaction is at an all-time low. "
        "Revenue is growing steadily every quarter. But costs are growing even faster "
        "and nobody seems concerned about the burn rate.\n\n"
        "The morning standup was productive and energizing. Then the afternoon was "
        "wasted in pointless meetings. We shipped a brilliant feature that users adore. "
        "It immediately caused a regression that broke the payment flow. The hotfix was "
        "deployed in under an hour — impressive response time. But it introduced a new "
        "bug that took three days to find.\n\n"
        "I'm proud of what we've accomplished this quarter. I'm also exhausted and "
        "questioning every decision we've made. The codebase is elegant in some areas. "
        "Other parts are horrifying spaghetti that nobody dares refactor. Our best "
        "engineer wrote something beautiful yesterday. Our worst engineer deleted it "
        "today by accident and there's no backup.\n\n"
        "The investor meeting went surprisingly well. Then the follow-up email was "
        "devastating — they want to cut our budget by half. The marketing campaign "
        "brought in record traffic. Unfortunately our servers couldn't handle the load "
        "and crashed for six hours. We won the industry award for innovation. The next "
        "day we got sued for patent infringement.\n\n"
        "On balance, this has been the most intense year of my career. Some days I "
        "feel like we're building something incredible and transformative. Other days "
        "I wonder if we're just rearranging deck chairs on a sinking ship. The highs "
        "are higher than anything I've experienced. The lows are absolutely crushing "
        "and make me question everything. But somehow we keep moving forward, one "
        "chaotic step at a time, hoping it all works out in the end.\n\n"
        "The culture is a paradox that confounds me every single day I show up. "
        "People are simultaneously brilliant and frustrating in equal measure. "
        "Some days the collaboration is seamless and produces genuinely great work. "
        "Other days the same team can barely agree on what day of the week it is. "
        "We had a beautiful team offsite last month that restored everyone's faith. "
        "Then the very next Monday someone sent a passive-aggressive email that "
        "undid all of it instantly. I cannot tell if we are succeeding or failing, "
        "thriving or collapsing, building something great or wasting everyone's time. "
        "The uncertainty is absolutely exhausting but somehow also remains strangely and persistently exciting. "
        "I genuinely do not know how this story ends but I keep showing up regardless every single morning. "
        "Perhaps that stubborn daily persistence is itself the only honest answer I can give right now."
    )


class TestSentimentElements:
    """Tests for VADER-based sentiment elements."""

    def test_positive_text_sentiment_mean(self, positive_text):
        profile = generate_voice_profile(positive_text)
        assert "sentiment_mean" in profile
        assert profile["sentiment_mean"]["target_value"] > 0.2

    def test_negative_text_sentiment_mean(self, negative_text):
        profile = generate_voice_profile(negative_text)
        assert profile["sentiment_mean"]["target_value"] < -0.2

    def test_mixed_text_high_variance(self, mixed_sentiment_text):
        profile = generate_voice_profile(mixed_sentiment_text)
        assert "sentiment_variance" in profile
        assert profile["sentiment_variance"]["target_value"] > 0.05

    def test_positive_text_low_variance(self, positive_text):
        profile = generate_voice_profile(positive_text)
        mixed_profile = generate_voice_profile(
            "I love this. I hate this. It's wonderful. It's terrible. "
            "Everything is great. Everything is awful. What a joy. What a nightmare. "
            * 75
        )
        assert profile["sentiment_variance"]["target_value"] < mixed_profile["sentiment_variance"]["target_value"]

    def test_mixed_text_high_shift_rate(self, mixed_sentiment_text):
        profile = generate_voice_profile(mixed_sentiment_text)
        assert "sentiment_shift_rate" in profile
        assert profile["sentiment_shift_rate"]["target_value"] > 0.2

    def test_positive_text_low_shift_rate(self, positive_text):
        profile = generate_voice_profile(positive_text)
        assert profile["sentiment_shift_rate"]["target_value"] < 0.4

    def test_sentiment_element_structure(self, positive_text):
        profile = generate_voice_profile(positive_text)
        for key in ["sentiment_mean", "sentiment_variance", "sentiment_shift_rate"]:
            elem = profile[key]
            assert elem["category"] == "voice_tone"
            assert elem["element_type"] == "metric"
            assert "target_value" in elem
            assert "weight" in elem
            assert "tier3" in elem["tags"]


class TestSentimentFallback:
    """Tests for VADER unavailable fallback."""

    def test_vader_unavailable_skips_sentiment(self, positive_text):
        with patch("utils.voice_generator._vader_available", False), \
             patch("utils.voice_generator._vader_analyzer", None):
            profile = generate_voice_profile(positive_text)
            assert "sentiment_mean" not in profile
            assert "sentiment_variance" not in profile
            assert "sentiment_shift_rate" not in profile
            assert "avg_word_length" in profile

    def test_too_few_sentences_skips_sentiment(self):
        long_sentence = "word " * 260
        text = long_sentence.strip() + ". " + long_sentence.strip() + "."
        profile = generate_voice_profile(text)
        assert "sentiment_mean" not in profile
