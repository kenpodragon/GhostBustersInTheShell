"""Voice test harness — reusable functions for voice profile experiments.

Provides: parse_file, profile_similarity, save_report,
          profile_to_json_for_ai, print_profile_summary.
"""
import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime

# Add backend to path so we can import voice_generator
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from utils.voice_generator import generate_voice_profile

RESULTS_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "local_data", "voice_testing"
)


def parse_file(filepath: str, max_words: int = 0) -> dict:
    """Parse a text file into a voice profile dict.

    Args:
        filepath: Path to a UTF-8 text file.
        max_words: If > 0, truncate text to this many words before analysis.

    Returns:
        dict with keys: profile, word_count, filepath.
    """
    with open(filepath, "r", encoding="utf-8") as f:
        text = f.read()

    if max_words > 0:
        words = text.split()
        if len(words) > max_words:
            text = " ".join(words[:max_words])

    word_count = len(text.split())
    profile = generate_voice_profile(text)
    return {"profile": profile, "word_count": word_count, "filepath": filepath}


def profile_similarity(profile_a: dict, profile_b: dict) -> dict:
    """Compare two voice profiles element-by-element.

    Returns dict with: overall_similarity, label, element_count,
    element_similarities.
    """
    all_keys = set(profile_a.keys()) | set(profile_b.keys())
    element_sims = {}

    for key in all_keys:
        a = profile_a.get(key)
        b = profile_b.get(key)

        if a is None or b is None:
            element_sims[key] = 0.0
            continue

        a_weight = a.get("weight", 0.0)
        b_weight = b.get("weight", 0.0)
        weight_sim = 1.0 - abs(a_weight - b_weight)

        elem_type = a.get("element_type", b.get("element_type", "directional"))

        if elem_type == "metric":
            ta = a.get("target_value", 0.0)
            tb = b.get("target_value", 0.0)
            denom = max(abs(ta), abs(tb), 1.0)
            target_sim = 1.0 - min(1.0, abs(ta - tb) / denom)
            combined = weight_sim * 0.3 + target_sim * 0.7
        else:
            # directional
            dir_a = a.get("direction", "")
            dir_b = b.get("direction", "")
            direction_match = 1.0 if dir_a == dir_b else 0.5
            combined = weight_sim * 0.7 + direction_match * 0.3

        element_sims[key] = round(combined, 4)

    element_count = len(all_keys)
    overall = sum(element_sims.values()) / element_count if element_count else 0.0
    overall = round(overall, 4)

    if overall >= 0.9:
        label = "very similar"
    elif overall >= 0.75:
        label = "similar"
    elif overall >= 0.5:
        label = "moderately similar"
    elif overall >= 0.3:
        label = "different"
    else:
        label = "very different"

    return {
        "overall_similarity": overall,
        "label": label,
        "element_count": element_count,
        "element_similarities": element_sims,
    }


def save_report(name: str, data: dict) -> str:
    """Save experiment results as timestamped JSON.

    Args:
        name: Descriptive name for the report file.
        data: Dict to serialize.

    Returns:
        Absolute path to the saved file.
    """
    os.makedirs(RESULTS_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{name}.json"
    filepath = os.path.join(RESULTS_DIR, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)

    print(filepath)
    return filepath


def profile_to_json_for_ai(profile: dict) -> str:
    """Convert a voice profile to a compact JSON string for AI scoring.

    Each element becomes: {weight, type, direction (if present),
    target (if present, rounded to 2dp)}.
    """
    compact = {}
    for name, elem in profile.items():
        entry = {
            "weight": elem.get("weight", 0.0),
            "type": elem.get("element_type", "unknown"),
        }
        if "direction" in elem:
            entry["direction"] = elem["direction"]
        if "target_value" in elem:
            entry["target"] = round(elem["target_value"], 2)
        compact[name] = entry

    return json.dumps(compact, indent=None)


def print_profile_summary(profile: dict, label: str = "Profile") -> None:
    """Print a human-readable profile summary grouped by category."""
    print(f"\n=== {label} ({len(profile)} elements) ===")

    by_category = defaultdict(list)
    for name, elem in profile.items():
        cat = elem.get("category", "unknown")
        by_category[cat].append((name, elem))

    for cat in sorted(by_category.keys()):
        print(f"\n  [{cat}]")
        for name, elem in sorted(by_category[cat]):
            etype = elem.get("element_type", "unknown")
            weight = elem.get("weight", 0.0)
            if etype == "metric":
                tv = elem.get("target_value", 0.0)
                print(f"    {name}: target={tv:.2f}, weight={weight:.4f}")
            else:
                direction = elem.get("direction", "?")
                print(f"    {name}: {direction} (weight={weight:.4f})")
