"""Shakespeare incremental training curve experiment.

Parses Shakespeare texts one at a time, then computes cumulative profiles
at increasing corpus sizes to measure how quickly the profile stabilizes.
Outputs: similarity-to-full-corpus at each step plus convergence data.
"""

import os
import sys
import json
import math
from copy import deepcopy

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
sys.path.insert(0, os.path.dirname(__file__))

from utils.voice_generator import generate_voice_profile
from voice_test_harness import (
    parse_file,
    profile_similarity,
    save_report,
    print_profile_summary,
    profile_to_json_for_ai,
)

SHAKESPEARE_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "local_data", "corpus", "shakespeare"
)


def _cumulative_average(profiles: list) -> dict:
    """Compute element-wise running average across multiple parse results.

    Mimics VoiceProfileService.apply_parse_results logic:
      - First profile sets values directly
      - Each subsequent: new_avg = (old_avg * count + new_value) / (count + 1)
      - Direction: majority vote across all profiles
      - Rounds weights to 4dp, target_values to 4dp
    """
    if not profiles:
        return {}

    # Start with a deep copy of the first profile
    avg = deepcopy(profiles[0])

    # Track direction votes for majority voting
    direction_votes: dict[str, list[str]] = {}
    for key, elem in avg.items():
        if elem.get("element_type") == "directional" and "direction" in elem:
            direction_votes[key] = [elem["direction"]]

    # Accumulate subsequent profiles
    for i, profile in enumerate(profiles[1:], start=1):
        count = i  # number of profiles already averaged

        all_keys = set(avg.keys()) | set(profile.keys())

        for key in all_keys:
            if key in avg and key in profile:
                old = avg[key]
                new = profile[key]

                # Average weight
                old_w = old.get("weight", 0.0)
                new_w = new.get("weight", 0.0)
                old["weight"] = round((old_w * count + new_w) / (count + 1), 4)

                # Average target_value for metrics
                if old.get("element_type") == "metric":
                    old_tv = old.get("target_value", 0.0)
                    new_tv = new.get("target_value", 0.0)
                    old["target_value"] = round(
                        (old_tv * count + new_tv) / (count + 1), 4
                    )

                # Track direction votes
                if old.get("element_type") == "directional" and "direction" in new:
                    if key not in direction_votes:
                        direction_votes[key] = []
                    direction_votes[key].append(new["direction"])

            elif key in profile:
                # New key not in avg yet — add it
                avg[key] = deepcopy(profile[key])
                if profile[key].get("element_type") == "directional" and "direction" in profile[key]:
                    direction_votes[key] = [profile[key]["direction"]]

    # Apply majority-vote directions
    for key, votes in direction_votes.items():
        if key in avg:
            from collections import Counter
            most_common = Counter(votes).most_common(1)[0][0]
            avg[key]["direction"] = most_common

    return avg


def run_training_curve():
    """Main experiment: incremental training curve for Shakespeare corpus."""
    # Discover text files
    txt_files = sorted(
        f
        for f in os.listdir(SHAKESPEARE_DIR)
        if f.endswith(".txt")
    )

    if not txt_files:
        print(f"ERROR: No .txt files found in {SHAKESPEARE_DIR}")
        return

    print(f"Found {len(txt_files)} Shakespeare texts\n")

    # --- Parse each file individually ---
    file_results = []
    for filename in txt_files:
        filepath = os.path.join(SHAKESPEARE_DIR, filename)
        print(f"Parsing {filename}...", end=" ", flush=True)
        result = parse_file(filepath, max_words=0)
        n_elements = len(result["profile"])
        print(f"{result['word_count']:,} words, {n_elements} elements")
        file_results.append({"filename": filename, **result})

    # --- Define incremental steps ---
    n = len(file_results)
    step_sizes = sorted(set([1, 2, 4, n]))  # deduplicate if n <= 4
    step_sizes = [s for s in step_sizes if s <= n]

    # Extract just the profiles list
    all_profiles = [r["profile"] for r in file_results]

    # Full corpus profile (all texts)
    full_profile = _cumulative_average(all_profiles)

    # --- Compute training curve ---
    print(f"\n{'='*60}")
    print("TRAINING CURVE")
    print(f"{'='*60}")
    print(f"{'Texts':>6} | {'Similarity to Full':>20} | {'Label':<20}")
    print(f"{'-'*6}-+-{'-'*20}-+-{'-'*20}")

    training_curve = []
    prev_profile = None

    for step in step_sizes:
        step_profiles = all_profiles[:step]
        step_avg = _cumulative_average(step_profiles)

        sim = profile_similarity(step_avg, full_profile)

        # Convergence: compare to previous step
        convergence_sim = None
        if prev_profile is not None:
            conv = profile_similarity(step_avg, prev_profile)
            convergence_sim = conv["overall_similarity"]

        filenames_used = [file_results[i]["filename"] for i in range(step)]
        total_words = sum(file_results[i]["word_count"] for i in range(step))

        entry = {
            "num_texts": step,
            "filenames": filenames_used,
            "total_words": total_words,
            "similarity_to_full": sim["overall_similarity"],
            "similarity_label": sim["label"],
            "convergence_from_prev": convergence_sim,
        }
        training_curve.append(entry)

        print(
            f"{step:>6} | {sim['overall_similarity']:>18.4f}% | {sim['label']:<20}"
        )

        prev_profile = step_avg

    # --- Convergence summary ---
    print(f"\n{'='*60}")
    print("CONVERGENCE (step-to-step similarity)")
    print(f"{'='*60}")
    print(f"{'Step':>10} | {'Prev->Cur Similarity':>22} | {'Total Words':>12}")
    print(f"{'-'*10}-+-{'-'*22}-+-{'-'*12}")

    convergence = []
    for entry in training_curve:
        conv_str = (
            f"{entry['convergence_from_prev']:.4f}"
            if entry["convergence_from_prev"] is not None
            else "N/A"
        )
        print(
            f"{entry['num_texts']:>10} | {conv_str:>22} | {entry['total_words']:>12,}"
        )
        convergence.append(
            {
                "num_texts": entry["num_texts"],
                "convergence_from_prev": entry["convergence_from_prev"],
                "total_words": entry["total_words"],
            }
        )

    # --- Print full corpus profile ---
    print_profile_summary(full_profile, "Full Shakespeare Corpus Profile")

    # --- Individual file word counts ---
    individual_word_counts = {
        r["filename"]: r["word_count"] for r in file_results
    }

    # --- Save report ---
    report = {
        "experiment": "shakespeare_training_curve",
        "num_files": len(file_results),
        "training_curve": training_curve,
        "convergence": convergence,
        "full_profile_json": json.loads(profile_to_json_for_ai(full_profile)),
        "individual_file_word_counts": individual_word_counts,
    }

    report_path = save_report("shakespeare_training_curve", report)
    print(f"\nReport saved: {report_path}")

    return report


if __name__ == "__main__":
    report = run_training_curve()

    if report:
        print(f"\n{'='*60}")
        print("SUMMARY")
        print(f"{'='*60}")
        print(f"Files parsed: {report['num_files']}")
        print(f"Total words: {sum(report['individual_file_word_counts'].values()):,}")
        print("\nTraining curve:")
        for entry in report["training_curve"]:
            print(
                f"  {entry['num_texts']} texts ({entry['total_words']:,} words): "
                f"{entry['similarity_to_full']:.4f} similarity"
            )
        print("\nConvergence:")
        for entry in report["convergence"]:
            conv = entry["convergence_from_prev"]
            conv_str = f"{conv:.4f}" if conv is not None else "N/A"
            print(
                f"  {entry['num_texts']} texts ({entry['total_words']:,} words): "
                f"step similarity = {conv_str}"
            )
