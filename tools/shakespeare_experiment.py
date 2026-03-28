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


def _call_claude(prompt: str) -> str:
    """Call Claude CLI and return raw text response."""
    result = subprocess.run(
        ["claude", "-p", prompt, "--output-format", "text"],
        capture_output=True, text=True, timeout=120,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Claude CLI failed: {result.stderr.strip()}")
    return result.stdout.strip()


def _parse_json_from_claude(raw: str) -> object:
    """Extract JSON from Claude response, handling markdown fences."""
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"```(?:json)?\s*(\[.*?\]|\{.*?\})\s*```", raw, re.DOTALL)
        if match:
            return json.loads(match.group(1))
        raise


def run_ai_enhanced_experiment(full_profile: dict):
    """Use AI to analyze gaps in Python-only profile and enhance with AI-crafted prompts.

    Steps:
    1. Send Shakespeare text samples + current profile to Claude
    2. Ask Claude to identify style patterns not captured by metrics
    3. Ask Claude to generate voice prompts that capture Shakespeare's essence
    4. Create enhanced profile with AI prompts in DB
    5. Generate text and score vs Python-only baseline
    """
    print(f"\n{'='*60}")
    print("AI-ENHANCED CORPUS EXPERIMENT")
    print(f"{'='*60}\n")

    profile_json_str = profile_to_json_for_ai(full_profile)

    # Build english instructions for comparison
    elements_list = [{"name": k, **v} for k, v in full_profile.items()]
    english_instructions = translate_elements_to_english(elements_list)

    # Load a Shakespeare sample for AI analysis
    sample_path = os.path.join(SHAKESPEARE_DIR, "hamlet.txt")
    with open(sample_path, "r", encoding="utf-8") as f:
        sample_text = f.read()
    # Truncate to ~3000 words
    sample_text = " ".join(sample_text.split()[:3000])

    # --- Step 1: Gap Analysis ---
    print("Step 1: Asking Claude to identify gaps in our metrics...")
    gap_prompt = f"""You are a literary style analyst specializing in Shakespeare.

Here is our current computational voice profile for Shakespeare (JSON metrics):
```json
{profile_json_str}
```

Here is a sample of Shakespeare's actual writing:
{sample_text[:2000]}

Identify 5-8 specific style elements that our computational metrics MISS but are crucial to Shakespeare's voice. Focus on patterns that would help an AI generate more authentic Shakespeare-style text.

For each gap, explain:
- What the element is
- Why it matters for Shakespeare specifically
- How it could be described in a writing instruction

Respond with ONLY valid JSON (no markdown fences):
[
  {{"name": "<element_name>", "description": "<what it is>", "importance": "<why it matters>", "instruction": "<how to tell AI to use it>"}}
]"""

    try:
        gap_raw = _call_claude(gap_prompt)
        gap_analysis = _parse_json_from_claude(gap_raw)
        print(f"  Found {len(gap_analysis)} style gaps:")
        for gap in gap_analysis:
            print(f"    - {gap.get('name', '?')}: {gap.get('description', '?')[:80]}")
    except Exception as e:
        print(f"  WARNING: Gap analysis failed: {e}")
        gap_analysis = []

    # --- Step 2: Generate AI Voice Prompts ---
    print("\nStep 2: Asking Claude to generate voice prompts...")
    prompt_prompt = f"""You are helping build a voice profile that guides AI text generation to sound like Shakespeare.

Current computational metrics:
```json
{profile_json_str}
```

Current English instructions (generated from metrics):
{english_instructions[:1500]}

Style gaps identified:
{json.dumps(gap_analysis[:5], indent=2) if gap_analysis else "None identified"}

Write 3-5 concise voice prompts (1-2 sentences each) that capture Shakespeare's writing style. These prompts will be prepended to AI generation requests. Focus on aspects NOT already covered by the English instructions above — especially the gaps.

Respond with ONLY valid JSON (no markdown fences):
["<prompt1>", "<prompt2>", ...]"""

    try:
        prompts_raw = _call_claude(prompt_prompt)
        ai_prompts = _parse_json_from_claude(prompts_raw)
        print(f"  Generated {len(ai_prompts)} voice prompts:")
        for p in ai_prompts:
            print(f"    - {p[:100]}...")
    except Exception as e:
        print(f"  WARNING: Prompt generation failed: {e}")
        ai_prompts = []

    # --- Step 3: Create Enhanced Profile ---
    print("\nStep 3: Creating AI-enhanced profile in DB...")
    try:
        profile_id = _create_shakespeare_profile_via_api(
            full_profile, "Shakespeare AI-Enhanced"
        )
        print(f"  Profile ID: {profile_id}")

        # Add AI-generated prompts
        for i, p in enumerate(ai_prompts):
            requests.post(
                f"{API_BASE}/api/voice-profiles/{profile_id}/prompts",
                json={"prompt_text": p, "sort_order": i},
            )
        print(f"  Added {len(ai_prompts)} AI prompts to profile")
    except Exception as e:
        print(f"  ERROR: Failed to create profile: {e}")
        return None

    # --- Step 4: Generate + Score ---
    print("\nStep 4: Generating text with AI-enhanced profile and scoring...")

    test_prompts = [
        "Write a short monologue about the nature of ambition and power.",
        "Write a dialogue between two characters debating the merits of love versus duty.",
        "Write a reflection on mortality and the passage of time.",
    ]

    # Build combined english instructions: original + AI prompts
    enhanced_english = english_instructions
    if ai_prompts:
        enhanced_english += "\n\n## Additional Style Directives\n"
        enhanced_english += "\n".join(f"- {p}" for p in ai_prompts)

    # Also build gap-informed instructions
    if gap_analysis:
        enhanced_english += "\n\n## Style Elements to Emphasize\n"
        for gap in gap_analysis:
            instr = gap.get("instruction", gap.get("description", ""))
            enhanced_english += f"- {gap.get('name', '?')}: {instr}\n"

    scoring_formats = {
        "english_only_python": {"english_instructions": english_instructions},
        "english_only_enhanced": {"english_instructions": enhanced_english},
        "both_enhanced": {"profile_json": profile_json_str, "english_instructions": enhanced_english},
    }

    generation_results = []

    for i, prompt in enumerate(test_prompts, 1):
        print(f"\n--- Prompt {i}: {prompt[:60]}... ---")

        # Generate with enhanced profile
        print("  Generating text...")
        try:
            generated = _generate_text_with_voice(profile_id, prompt)
        except requests.RequestException as e:
            print(f"  ERROR generating: {e}")
            generation_results.append({"prompt": prompt, "error": str(e)})
            continue

        if not generated or generated == "Generate new content.":
            print("  WARNING: Generation returned empty or unchanged text.")
            generation_results.append({"prompt": prompt, "error": "generation failed"})
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

    # --- Cleanup ---
    print("\nCleaning up: deleting AI-enhanced profile...")
    try:
        requests.delete(f"{API_BASE}/api/voice-profiles/{profile_id}")
        print("Profile deleted.")
    except requests.RequestException:
        print(f"WARNING: Could not delete profile {profile_id}")

    # --- Save Report ---
    report = {
        "experiment": "shakespeare_ai_enhanced",
        "gap_analysis": gap_analysis,
        "ai_prompts": ai_prompts,
        "enhanced_english_instructions": enhanced_english,
        "generation_results": generation_results,
    }
    report_path = save_report("shakespeare_ai_enhanced", report)
    print(f"\nReport saved: {report_path}")

    # --- Print Summary ---
    fmt_names = list(scoring_formats.keys())
    print(f"\n{'='*60}")
    print("AI-ENHANCED SCORING SUMMARY")
    print(f"{'='*60}")

    header = f"{'Prompt':<12}"
    for fmt in fmt_names:
        header += f" | {fmt:>22}"
    print(header)
    print("-" * len(header))

    fmt_totals = {fmt: [] for fmt in fmt_names}
    for i, result in enumerate(generation_results, 1):
        if "error" in result:
            row = f"Prompt {i:<5}"
            for fmt in fmt_names:
                row += f" | {'ERROR':>22}"
            print(row)
            continue
        row = f"Prompt {i:<5}"
        for fmt in fmt_names:
            s = result["scores"].get(fmt, {}).get("similarity_score", "?")
            row += f" | {s:>22}"
            if isinstance(s, (int, float)):
                fmt_totals[fmt].append(s)
        print(row)

    print("-" * len(header))
    row = f"{'Average':<12}"
    for fmt in fmt_names:
        vals = fmt_totals[fmt]
        avg = sum(vals) / len(vals) if vals else 0
        row += f" | {avg:>22.1f}"
    print(row)

    # Compare to baseline
    print(f"\n{'='*60}")
    print("COMPARISON TO PYTHON-ONLY BASELINE")
    print(f"{'='*60}")
    print("Baseline (Session 19):  english_only = 5.3, both = 40.7")
    print("Enhanced parser:        english_only = 55.7")
    enhanced_avg = sum(fmt_totals.get("english_only_enhanced", [])) / len(fmt_totals.get("english_only_enhanced", [1])) if fmt_totals.get("english_only_enhanced") else 0
    print(f"AI-enhanced:            english_only_enhanced = {enhanced_avg:.1f}")

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
    parser.add_argument(
        "--ai-enhance",
        action="store_true",
        help="Run AI-enhanced corpus experiment (gap analysis + AI prompts)",
    )
    args = parser.parse_args()

    # Determine what to run
    run_curve = not args.ai_enhance  # skip curve if only doing AI enhance
    run_gen = not args.curve_only and not args.ai_enhance
    run_ai = args.ai_enhance

    if args.generate:
        run_gen = True
        run_curve = True

    report = None
    full_profile = None

    def _build_full_profile():
        """Parse all Shakespeare texts and return cumulative profile."""
        txt_files = sorted(
            f for f in os.listdir(SHAKESPEARE_DIR) if f.endswith(".txt")
        )
        all_profiles = []
        for filename in txt_files:
            filepath = os.path.join(SHAKESPEARE_DIR, filename)
            result = parse_file(filepath, max_words=0)
            all_profiles.append(result["profile"])
        return _cumulative_average(all_profiles)

    if run_curve:
        result = run_training_curve()
        if result:
            report, full_profile = result
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
        if full_profile is None:
            full_profile = _build_full_profile()
        gen_report = run_generation_experiment(full_profile)

    if run_ai:
        if full_profile is None:
            print("Building full Shakespeare corpus profile...")
            full_profile = _build_full_profile()
        ai_report = run_ai_enhanced_experiment(full_profile)
