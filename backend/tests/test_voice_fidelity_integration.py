"""Integration test: score generated text against a real exported profile."""
import json
import os
import pytest
from utils.voice_fidelity_scorer import score_fidelity

PROFILE_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "docs", "voice_profiles"
)


def _load_profile_export(filename):
    """Load a voice profile export JSON and return profile_elements list.

    The export stores elements as a dict keyed by element name.  Convert to
    the list-of-dicts format that score_fidelity() expects, injecting the
    name from the key into each element dict.
    """
    path = os.path.join(PROFILE_DIR, filename)
    if not os.path.exists(path):
        pytest.skip(f"Profile export not found: {path}")
    with open(path) as f:
        data = json.load(f)
    raw = data.get("elements", {})
    if isinstance(raw, list):
        return raw
    # Dict form: {name: {category, element_type, weight, ...}, ...}
    return [{"name": name, **props} for name, props in raw.items()]


@pytest.mark.integration
class TestFidelityWithRealProfiles:

    def test_29_element_profile_scores(self, long_human_text):
        elements = _load_profile_export("stephen_voice_baseline_export_03272026_29.json")
        result = score_fidelity(
            generated_text=long_human_text,
            profile_elements=elements,
            mode="quantitative",
        )
        assert result["element_count"] == len(elements)
        assert result["aggregate_similarity"] > 0.0
        assert result["elements_matched"] > 0
        # Print for manual inspection during development
        print(f"\n29-element aggregate: {result['aggregate_similarity']:.2%}")
        for e in sorted(result["per_element"], key=lambda x: x["similarity"]):
            print(f"  {e['name']:30s} profile={e['profile_value']:.4f} "
                  f"gen={e['generated_value']!s:>10s} sim={e['similarity']:.2%}")

    def test_51_element_profile_scores(self, long_human_text):
        elements = _load_profile_export("stephen_voice_baseline_export_03282026_51.json")
        result = score_fidelity(
            generated_text=long_human_text,
            profile_elements=elements,
            mode="quantitative",
        )
        assert result["element_count"] == len(elements)
        assert result["aggregate_similarity"] > 0.0
        assert result["elements_matched"] > 0
        print(f"\n51-element aggregate: {result['aggregate_similarity']:.2%}")
        for e in sorted(result["per_element"], key=lambda x: x["similarity"]):
            print(f"  {e['name']:30s} profile={e['profile_value']:.4f} "
                  f"gen={e['generated_value']!s:>10s} sim={e['similarity']:.2%}")

    def test_29_vs_51_both_score(self, long_human_text):
        """Both profiles should produce valid scores against the same text."""
        elements_29 = _load_profile_export("stephen_voice_baseline_export_03272026_29.json")
        elements_51 = _load_profile_export("stephen_voice_baseline_export_03282026_51.json")

        result_29 = score_fidelity(
            generated_text=long_human_text,
            profile_elements=elements_29,
            mode="quantitative",
        )
        result_51 = score_fidelity(
            generated_text=long_human_text,
            profile_elements=elements_51,
            mode="quantitative",
        )

        print(f"\n29-element aggregate: {result_29['aggregate_similarity']:.2%}")
        print(f"51-element aggregate: {result_51['aggregate_similarity']:.2%}")
        print(f"51 has {result_51['element_count'] - result_29['element_count']} more elements")

        assert result_29["aggregate_similarity"] > 0.0
        assert result_51["aggregate_similarity"] > 0.0
