"""Shakespeare incremental training curve + generation experiment.

Parses Shakespeare texts one at a time, then computes cumulative profiles
at increasing corpus sizes to measure how quickly the profile stabilizes.
Optionally generates text using the Shakespeare voice profile via Flask API
and scores similarity using Claude.

Outputs: similarity-to-full-corpus at each step plus convergence data,
and (with --generate) generation + scoring results.
"""

import argparse
import os
import sys
import json
import math
import re
from copy import deepcopy

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
sys.path.insert(0, os.path.dirname(__file__))

import requests

from utils.voice_generator import generate_voice_profile
from utils.weight_translator import translate_elements_to_english
from voice_test_harness import (
    parse_file,
    profile_similarity,
    save_report,
    print_profile_summary,
    profile_to_json_for_ai,
)

import subprocess
import tempfile

API_BASE = "http://localhost:8066"

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


def _create_shakespeare_profile_via_api(profile: dict, name: str) -> int:
    """Create a voice profile in the DB via Flask API.

    Args:
        profile: Dict of element_key -> {category, element_type, weight, ...}
        name: Display name for the profile.

    Returns:
        profile_id from the API.
    """
    # Create the profile
    resp = requests.post(
        f"{API_BASE}/api/voice-profiles",
        json={
            "name": name,
            "description": f"Auto-generated {name} profile for experiment",
            "profile_type": "overlay",
        },
    )
    resp.raise_for_status()
    profile_id = resp.json()["id"]

    # Build elements array
    elements = []
    for key, elem in profile.items():
        el = {
            "name": key,
            "category": elem.get("category", "other"),
            "element_type": elem["element_type"],
            "weight": elem["weight"],
        }
        if elem.get("element_type") == "directional" and "direction" in elem:
            el["direction"] = elem["direction"]
        if elem.get("element_type") == "metric" and "target_value" in elem:
            el["target_value"] = elem["target_value"]
        elements.append(el)

    # Upsert elements (PUT, not POST)
    resp = requests.put(
        f"{API_BASE}/api/voice-profiles/{profile_id}/elements",
        json=elements,
    )
    resp.raise_for_status()

    return profile_id


def _generate_text_with_voice(profile_id: int, prompt: str) -> str:
    """Generate text using the rewrite endpoint with a voice profile.

    Args:
        profile_id: Voice profile ID in DB.
        prompt: Creative writing prompt.

    Returns:
        The generated/rewritten text.
    """
    resp = requests.post(
        f"{API_BASE}/api/rewrite",
        json={
            "text": "Generate new content.",
            "voice_profile_id": profile_id,
            "use_ai": True,
            "comment": f"GENERATE NEW CONTENT based on this prompt: {prompt}",
        },
    )
    resp.raise_for_status()
    data = resp.json()
    return data.get("rewritten_text", data.get("text", ""))


def _score_similarity_with_ai(
    generated_text: str,
    reference_author: str,
    profile_json: str | None = None,
    english_instructions: str | None = None,
) -> dict:
    """Score how similar generated text is to a reference author's style.

    Args:
        generated_text: The text to evaluate.
        reference_author: Author name (e.g. "William Shakespeare").
        profile_json: Optional JSON profile to include in scoring prompt.
        english_instructions: Optional English style guide to include.

    Returns:
        Dict with similarity_score, style_matches, style_misses, reasoning, confidence.
    """
    # Build the scoring prompt
    context_parts = []
    if profile_json:
        context_parts.append(
            f"## Style Profile (JSON)\n```json\n{profile_json}\n```"
        )
    if english_instructions:
        context_parts.append(
            f"## Style Instructions (English)\n{english_instructions}"
        )

    context_block = ""
    if context_parts:
        context_block = (
            "\n\nUse the following style reference to inform your evaluation:\n\n"
            + "\n\n".join(context_parts)
        )

    scoring_prompt = f"""You are a literary style analyst. Evaluate how closely the following text matches the writing style of {reference_author}.
{context_block}

## Text to Evaluate
{generated_text}

Rate the similarity on a scale of 0-100 where:
- 0 = no resemblance at all
- 25 = occasional hints of the style
- 50 = moderate similarity with clear stylistic overlap
- 75 = strong resemblance, most elements present
- 100 = indistinguishable from the author's actual work

Respond with ONLY valid JSON (no markdown fences):
{{
  "similarity_score": <0-100>,
  "style_matches": ["<element that matches>", ...],
  "style_misses": ["<element that's missing or wrong>", ...],
  "reasoning": "<2-3 sentences explaining your rating>",
  "confidence": "<low|medium|high>"
}}"""

    # Use Claude CLI instead of Anthropic SDK
    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
            f.write(scoring_prompt)
            prompt_file = f.name

        result = subprocess.run(
            ["claude", "-p", scoring_prompt, "--output-format", "text"],
            capture_output=True, text=True, timeout=120,
        )
        os.unlink(prompt_file)

        if result.returncode != 0:
            return {"error": f"Claude CLI failed: {result.stderr.strip()}"}

        raw = result.stdout.strip()
    except FileNotFoundError:
        return {"error": "Claude CLI not found. Install with: npm install -g @anthropic-ai/claude-code"}
    except subprocess.TimeoutExpired:
        return {"error": "Claude CLI timed out after 120s"}

    # Try to extract JSON from response
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Try extracting from markdown fences
        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
        return {"error": "Failed to parse scoring response", "raw": raw[:500]}


def run_generation_experiment(full_profile: dict):
    """Run generation + scoring experiment with Shakespeare voice profile.

    Creates a profile via API, generates text with 3 prompts, scores each
    with 4 different context formats (json_only, english_only, both, none).
    """
    print(f"\n{'='*60}")
    print("GENERATION + SCORING EXPERIMENT")
    print(f"{'='*60}\n")

    # Convert profile to formats
    profile_json_str = profile_to_json_for_ai(full_profile)

    # Build elements list for translate_elements_to_english
    elements_list = []
    for key, elem in full_profile.items():
        el = {"name": key, **elem}
        elements_list.append(el)
    english_instructions = translate_elements_to_english(elements_list)

    # Create profile in DB
    print("Creating Shakespeare voice profile via API...")
    try:
        profile_id = _create_shakespeare_profile_via_api(
            full_profile, "Shakespeare Experiment"
        )
    except requests.RequestException as e:
        print(f"ERROR: Failed to create profile via API: {e}")
        print("Is the Flask API running on port 8066?")
        return None
    print(f"Created profile ID: {profile_id}\n")

    prompts = [
        "Write a short monologue about the nature of ambition and power.",
        "Write a dialogue between two characters debating the merits of love versus duty.",
        "Write a reflection on mortality and the passage of time.",
    ]

    scoring_formats = {
        "json_only": {"profile_json": profile_json_str, "english_instructions": None},
        "english_only": {"profile_json": None, "english_instructions": english_instructions},
        "both": {"profile_json": profile_json_str, "english_instructions": english_instructions},
        "none": {"profile_json": None, "english_instructions": None},
    }

    generation_results = []

    for i, prompt in enumerate(prompts, 1):
        print(f"--- Prompt {i}: {prompt[:60]}... ---")

        # Generate text
        print("  Generating text with voice profile...")
        try:
            generated = _generate_text_with_voice(profile_id, prompt)
        except requests.RequestException as e:
            print(f"  ERROR generating: {e}")
            generation_results.append({"prompt": prompt, "error": str(e)})
            continue

        if not generated or generated == "Generate new content.":
            print("  WARNING: Generation returned empty or unchanged text.")
            print("  AI may not be enabled. Check app settings.")
            generation_results.append({
                "prompt": prompt,
                "error": "Generation returned unchanged text - AI may be disabled",
            })
            continue

        print(f"  Generated {len(generated)} chars")
        print(f"  Preview: {generated[:120]}...\n")

        # Score with each format
        scores = {}
        for fmt_name, fmt_kwargs in scoring_formats.items():
            print(f"  Scoring ({fmt_name})...", end=" ", flush=True)
            result = _score_similarity_with_ai(
                generated, "William Shakespeare", **fmt_kwargs
            )
            score = result.get("similarity_score", "?")
            confidence = result.get("confidence", "?")
            print(f"score={score}, confidence={confidence}")
            scores[fmt_name] = result

        generation_results.append({
            "prompt": prompt,
            "generated_text": generated,
            "generated_length": len(generated),
            "scores": scores,
        })
        print()

    # Cleanup: delete the test profile
    print("Cleaning up: deleting test profile...")
    try:
        requests.delete(f"{API_BASE}/api/voice-profiles/{profile_id}")
        print("Profile deleted.\n")
    except requests.RequestException:
        print(f"WARNING: Could not delete profile {profile_id}\n")

    # Save report
    report = {
        "experiment": "shakespeare_generation",
        "profile_id": profile_id,
        "profile_json": json.loads(profile_json_str),
        "english_instructions": english_instructions,
        "generation_results": generation_results,
    }
    report_path = save_report("shakespeare_generation", report)
    print(f"Report saved: {report_path}")

    # Print summary
    print(f"\n{'='*60}")
    print("GENERATION SCORING SUMMARY")
    print(f"{'='*60}")
    print(f"{'Prompt':<12} | {'json_only':>10} | {'english':>10} | {'both':>10} | {'none':>10}")
    print(f"{'-'*12}-+-{'-'*10}-+-{'-'*10}-+-{'-'*10}-+-{'-'*10}")

    for i, result in enumerate(generation_results, 1):
        if "error" in result:
            print(f"Prompt {i:<5} | {'ERROR':>10} | {'ERROR':>10} | {'ERROR':>10} | {'ERROR':>10}")
            continue
        scores = result["scores"]
        vals = []
        for fmt in ["json_only", "english_only", "both", "none"]:
            s = scores.get(fmt, {}).get("similarity_score", "?")
            vals.append(f"{s:>10}" if isinstance(s, (int, float)) else f"{s:>10}")
        print(f"Prompt {i:<5} | {' | '.join(vals)}")

    # Averages
    fmt_totals = {fmt: [] for fmt in scoring_formats}
    for result in generation_results:
        if "scores" not in result:
            continue
        for fmt in scoring_formats:
            s = result["scores"].get(fmt, {}).get("similarity_score")
            if isinstance(s, (int, float)):
                fmt_totals[fmt].append(s)

    print(f"{'-'*12}-+-{'-'*10}-+-{'-'*10}-+-{'-'*10}-+-{'-'*10}")
    avg_vals = []
    for fmt in ["json_only", "english_only", "both", "none"]:
        vals = fmt_totals[fmt]
        avg = sum(vals) / len(vals) if vals else 0
        avg_vals.append(f"{avg:>10.1f}")
    print(f"{'Average':<12} | {' | '.join(avg_vals)}")

    return report


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

    return report, full_profile


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Shakespeare voice profile experiments"
    )
    parser.add_argument(
        "--generate",
        action="store_true",
        help="Run training curve + generation/scoring experiment",
    )
    parser.add_argument(
        "--curve-only",
        action="store_true",
        help="Run training curve only (skip generation)",
    )
    args = parser.parse_args()

    # Default: run both if no flags specified
    run_curve = True
    run_gen = not args.curve_only  # generate unless --curve-only

    if args.generate:
        run_gen = True

    report = None
    full_profile = None

    if run_curve:
        result = run_training_curve()
        if result:
            report, full_profile = result
            # Extract full profile from training curve for generation
            # Re-derive it from the report's full_profile_json
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

    if run_gen:
        # We need the full profile. Re-derive from corpus.
        if full_profile is None:
            # Build it from scratch by re-parsing
            txt_files = sorted(
                f for f in os.listdir(SHAKESPEARE_DIR) if f.endswith(".txt")
            )
            all_profiles = []
            for filename in txt_files:
                filepath = os.path.join(SHAKESPEARE_DIR, filename)
                result = parse_file(filepath, max_words=0)
                all_profiles.append(result["profile"])
            full_profile = _cumulative_average(all_profiles)

        gen_report = run_generation_experiment(full_profile)
