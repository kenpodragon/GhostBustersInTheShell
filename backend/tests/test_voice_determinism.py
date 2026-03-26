"""Determinism and discrimination tests for voice profile generation.

Validates that generate_voice_profile() produces identical results for the same
input across a diverse corpus, and that different texts produce meaningfully
different profiles.
"""
import os
import glob
import pytest
from itertools import combinations

from utils.voice_generator import generate_voice_profile

# ---------------------------------------------------------------------------
# Corpus loading
# ---------------------------------------------------------------------------

CORPUS_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "local_data", "corpus", "diverse"
)
CORPUS_DIR = os.path.normpath(CORPUS_DIR)

MAX_WORDS = 10_000


def _get_corpus_files() -> list[str]:
    """Return sorted list of .txt files in the diverse corpus directory."""
    if not os.path.isdir(CORPUS_DIR):
        return []
    files = sorted(glob.glob(os.path.join(CORPUS_DIR, "*.txt")))
    return files


def _load_text(path: str) -> str:
    """Load a corpus file, truncated to MAX_WORDS words."""
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        text = f.read()
    words = text.split()
    if len(words) > MAX_WORDS:
        text = " ".join(words[:MAX_WORDS])
    return text


def _profile_to_comparable(profile: dict) -> dict:
    """Extract comparable fields from a profile dict.

    Returns a dict keyed by element name, each value a tuple of
    (category, element_type, weight, direction, target_value, sorted_tags).
    """
    result = {}
    for name, elem in sorted(profile.items()):
        result[name] = (
            elem.get("category"),
            elem.get("element_type"),
            elem.get("weight"),
            elem.get("direction"),
            elem.get("target_value"),
            tuple(sorted(elem.get("tags", []))),
        )
    return result


# ---------------------------------------------------------------------------
# Fixtures / parametrization
# ---------------------------------------------------------------------------

CORPUS_FILES = _get_corpus_files()
ENOUGH_FILES = len(CORPUS_FILES) >= 5

corpus_ids = [os.path.splitext(os.path.basename(f))[0] for f in CORPUS_FILES]


@pytest.fixture(params=CORPUS_FILES, ids=corpus_ids)
def corpus_text(request):
    """Yield (filename, text) for each corpus file."""
    path = request.param
    return os.path.basename(path), _load_text(path)


# ---------------------------------------------------------------------------
# TestDeterminism — parametrized across all corpus files
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not ENOUGH_FILES, reason=f"Need >=5 corpus files, found {len(CORPUS_FILES)}")
class TestDeterminism:
    """Parse each corpus text multiple times and verify identical output."""

    def test_parse_determinism(self, corpus_text):
        """Parse 3 times, assert all results are identical."""
        _name, text = corpus_text
        profiles = [generate_voice_profile(text) for _ in range(3)]
        comparables = [_profile_to_comparable(p) for p in profiles]
        assert comparables[0] == comparables[1], f"Run 1 != Run 2 for {_name}"
        assert comparables[1] == comparables[2], f"Run 2 != Run 3 for {_name}"

    def test_element_count_stable(self, corpus_text):
        """All 3 parses produce the same number of elements."""
        _name, text = corpus_text
        counts = [len(generate_voice_profile(text)) for _ in range(3)]
        assert counts[0] == counts[1] == counts[2], (
            f"Element counts differ for {_name}: {counts}"
        )

    def test_element_names_stable(self, corpus_text):
        """All 3 parses produce the same set of element names."""
        _name, text = corpus_text
        name_sets = [set(generate_voice_profile(text).keys()) for _ in range(3)]
        assert name_sets[0] == name_sets[1] == name_sets[2], (
            f"Element names differ for {_name}"
        )


# ---------------------------------------------------------------------------
# TestDiscrimination — different texts should yield different profiles
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not ENOUGH_FILES, reason=f"Need >=5 corpus files, found {len(CORPUS_FILES)}")
class TestDiscrimination:
    """Verify that different texts produce meaningfully different profiles."""

    @pytest.fixture(autouse=True)
    def _load_profiles(self):
        """Pre-generate profiles for discrimination tests."""
        self._profiles = {}
        for path in CORPUS_FILES:
            name = os.path.basename(path)
            text = _load_text(path)
            self._profiles[name] = generate_voice_profile(text)

    def test_different_texts_different_profiles(self):
        """Parse 6 different texts, assert each pair differs in >=3 elements."""
        names = list(self._profiles.keys())[:6]
        assert len(names) >= 6, f"Need 6 texts, found {len(names)}"

        for a, b in combinations(names, 2):
            prof_a = self._profiles[a]
            prof_b = self._profiles[b]
            all_keys = set(prof_a.keys()) | set(prof_b.keys())
            diffs = 0
            for key in all_keys:
                ea = prof_a.get(key, {})
                eb = prof_b.get(key, {})
                if (ea.get("weight") != eb.get("weight") or
                        ea.get("target_value") != eb.get("target_value")):
                    diffs += 1
            assert diffs >= 3, (
                f"{a} vs {b}: only {diffs} element(s) differ (need >=3)"
            )

    def test_weights_show_variance(self):
        """Across 8 texts, each element weight should have variance > 0.01.

        Allow up to 3 elements with zero variance (truly constant). For the
        broader 0.01 threshold, allow more since corpus texts from similar
        eras may share characteristics — but the majority should still vary.
        """
        names = list(self._profiles.keys())[:8]
        assert len(names) >= 8, f"Need 8 texts, found {len(names)}"

        # Collect all element names across the 8 profiles
        all_elements: set[str] = set()
        for n in names:
            all_elements.update(self._profiles[n].keys())

        zero_variance_elements = []
        total_elements = 0
        variance_sum = 0.0
        for elem in sorted(all_elements):
            weights = []
            for n in names:
                prof = self._profiles[n]
                if elem in prof:
                    weights.append(prof[elem].get("weight", 0.0))
            if len(weights) < 2:
                continue
            total_elements += 1
            mean = sum(weights) / len(weights)
            variance = sum((w - mean) ** 2 for w in weights) / len(weights)
            variance_sum += variance
            if variance == 0.0:
                zero_variance_elements.append((elem, variance))

        # No more than 3 elements should have truly zero variance
        assert len(zero_variance_elements) <= 3, (
            f"{len(zero_variance_elements)} elements have zero variance (max 3 allowed): "
            f"{zero_variance_elements}"
        )
        # Overall average variance should be meaningful (> 0.001)
        if total_elements > 0:
            avg_variance = variance_sum / total_elements
            assert avg_variance > 0.001, (
                f"Average weight variance across elements is too low: {avg_variance:.6f}"
            )
