"""Personal writing voice profile experiment.

Parses personal writing corpus, builds a voice profile, generates text
using the profile, and scores how well the generated text matches
the author's writing style.

Mirrors the Shakespeare experiment but for personal writing.
"""

import argparse
import os
import sys
import json

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
from shakespeare_experiment import (
    _cumulative_average,
    _create_shakespeare_profile_via_api,
    _generate_text_with_voice,
    _score_similarity_with_ai,
    _call_claude,
    _parse_json_from_claude,
)

API_BASE = "http://localhost:8066"

PERSONAL_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "local_data", "corpus", "personal"
)


def parse_personal_corpus(max_files: int = 0):
    """Parse all personal writing files and build cumulative profile.

    Args:
        max_files: Limit number of files (0 = all).

    Returns:
        (full_profile, file_results, training_curve)
    """
    txt_files = sorted(
        f for f in os.listdir(PERSONAL_DIR) if f.endswith(".txt")
    )

    if not txt_files:
        print(f"ERROR: No .txt files found in {PERSONAL_DIR}")
        return None, None, None

    if max_files > 0:
        txt_files = txt_files[:max_files]

    print(f"Found {len(txt_files)} personal writing files\n")

    # Parse each file
    file_results = []
    for filename in txt_files:
        filepath = os.path.join(PERSONAL_DIR, filename)
        print(f"  Parsing {filename[:60]}...", end=" ", flush=True)
        try:
            result = parse_file(filepath, max_words=0)
            n_elements = len(result["profile"])
            print(f"{result['word_count']:,} words, {n_elements} elements")
            file_results.append({"filename": filename, **result})
        except Exception as e:
            print(f"ERROR: {e}")
            continue

    if not file_results:
        print("ERROR: No files parsed successfully")
        return None, None, None

    # Build cumulative profile
    all_profiles = [r["profile"] for r in file_results]
    full_profile = _cumulative_average(all_profiles)

    # Training curve at key steps
    n = len(file_results)
    step_sizes = sorted(set([1, 2, 5, 10, 20, 40, n]))
    step_sizes = [s for s in step_sizes if s <= n]

    print(f"\n{'='*60}")
    print("TRAINING CURVE")
    print(f"{'='*60}")
    print(f"{'Files':>6} | {'Words':>12} | {'Similarity to Full':>20} | {'Label':<20}")
    print(f"{'-'*6}-+-{'-'*12}-+-{'-'*20}-+-{'-'*20}")

    training_curve = []
    for step in step_sizes:
        step_profiles = all_profiles[:step]
        step_avg = _cumulative_average(step_profiles)
        sim = profile_similarity(step_avg, full_profile)
        total_words = sum(file_results[i]["word_count"] for i in range(step))

        entry = {
            "num_files": step,
            "total_words": total_words,
            "similarity_to_full": sim["overall_similarity"],
            "label": sim["label"],
        }
        training_curve.append(entry)
        print(
            f"{step:>6} | {total_words:>12,} | "
            f"{sim['overall_similarity']:>18.4f}% | {sim['label']:<20}"
        )

    return full_profile, file_results, training_curve


def run_generation_experiment(full_profile: dict):
    """Generate text with personal voice profile and score similarity."""
    print(f"\n{'='*60}")
    print("PERSONAL WRITING GENERATION EXPERIMENT")
    print(f"{'='*60}\n")

    profile_json_str = profile_to_json_for_ai(full_profile)
    elements_list = [{"name": k, **v} for k, v in full_profile.items()]
    english_instructions = translate_elements_to_english(elements_list)

    # Create profile in DB
    print("Creating personal voice profile via API...")
    try:
        profile_id = _create_shakespeare_profile_via_api(
            full_profile, "Personal Writing Experiment"
        )
    except requests.RequestException as e:
        print(f"ERROR: Failed to create profile: {e}")
        return None
    print(f"Created profile ID: {profile_id}\n")

    # Prompts that match the author's writing domains
    prompts = [
        "Write a short article about the challenges of transitioning from a developer to a technical leader.",
        "Write a reflection on how AI is changing the landscape for software teams and what leaders should do about it.",
        "Write an opinion piece about why most corporate motivational advice fails and what actually works for tech teams.",
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

        print("  Generating text with voice profile...")
        try:
            generated = _generate_text_with_voice(profile_id, prompt)
        except requests.RequestException as e:
            print(f"  ERROR generating: {e}")
            generation_results.append({"prompt": prompt, "error": str(e)})
            continue

        if not generated or generated == "Generate new content.":
            print("  WARNING: Generation returned empty/unchanged. AI may be disabled.")
            generation_results.append({"prompt": prompt, "error": "generation failed"})
            continue

        print(f"  Generated {len(generated)} chars")
        print(f"  Preview: {generated[:120]}...\n")

        # Score with each format
        scores = {}
        for fmt_name, fmt_kwargs in scoring_formats.items():
            print(f"  Scoring ({fmt_name})...", end=" ", flush=True)
            result = _score_similarity_with_ai(
                generated, "Stephen Salaka", **fmt_kwargs
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

    # Cleanup
    print("Cleaning up: deleting test profile...")
    try:
        requests.delete(f"{API_BASE}/api/voice-profiles/{profile_id}")
        print("Profile deleted.\n")
    except requests.RequestException:
        print(f"WARNING: Could not delete profile {profile_id}\n")

    # Summary
    print(f"\n{'='*60}")
    print("PERSONAL WRITING SCORING SUMMARY")
    print(f"{'='*60}")
    print(f"{'Prompt':<12} | {'json_only':>10} | {'english':>10} | {'both':>10} | {'none':>10}")
    print(f"{'-'*12}-+-{'-'*10}-+-{'-'*10}-+-{'-'*10}-+-{'-'*10}")

    fmt_totals = {fmt: [] for fmt in scoring_formats}
    for i, result in enumerate(generation_results, 1):
        if "error" in result:
            print(f"Prompt {i:<5} | {'ERROR':>10} | {'ERROR':>10} | {'ERROR':>10} | {'ERROR':>10}")
            continue
        scores = result["scores"]
        vals = []
        for fmt in ["json_only", "english_only", "both", "none"]:
            s = scores.get(fmt, {}).get("similarity_score", "?")
            vals.append(f"{s:>10}" if isinstance(s, (int, float)) else f"{s:>10}")
            if isinstance(s, (int, float)):
                fmt_totals[fmt].append(s)
        print(f"Prompt {i:<5} | {' | '.join(vals)}")

    print(f"{'-'*12}-+-{'-'*10}-+-{'-'*10}-+-{'-'*10}-+-{'-'*10}")
    avg_vals = []
    for fmt in ["json_only", "english_only", "both", "none"]:
        vals = fmt_totals[fmt]
        avg = sum(vals) / len(vals) if vals else 0
        avg_vals.append(f"{avg:>10.1f}")
    print(f"{'Average':<12} | {' | '.join(avg_vals)}")

    report = {
        "experiment": "personal_writing_generation",
        "profile_json": json.loads(profile_json_str),
        "english_instructions": english_instructions,
        "generation_results": generation_results,
    }
    report_path = save_report("personal_writing_generation", report)
    print(f"\nReport saved: {report_path}")

    return report


def run_ai_enhanced_experiment(full_profile: dict):
    """Use AI to analyze gaps in Python-only profile and enhance with AI-crafted prompts.

    Same approach as Shakespeare AI-enhanced experiment but for personal writing.
    """
    print(f"\n{'='*60}")
    print("AI-ENHANCED PERSONAL WRITING EXPERIMENT")
    print(f"{'='*60}\n")

    profile_json_str = profile_to_json_for_ai(full_profile)
    elements_list = [{"name": k, **v} for k, v in full_profile.items()]
    english_instructions = translate_elements_to_english(elements_list)

    # Load a sample of personal writing for AI analysis
    txt_files = sorted(f for f in os.listdir(PERSONAL_DIR) if f.endswith(".txt"))
    # Pick a few LinkedIn articles (shorter, more representative of voice)
    sample_files = [f for f in txt_files if "salaka" in f.lower()][:3]
    if not sample_files:
        sample_files = txt_files[:3]

    sample_text = ""
    for sf in sample_files:
        with open(os.path.join(PERSONAL_DIR, sf), "r", encoding="utf-8", errors="replace") as fh:
            sample_text += fh.read()[:2000] + "\n\n---\n\n"
    sample_text = sample_text[:5000]  # Cap at ~5K chars

    # --- Step 1: Gap Analysis ---
    print("Step 1: Asking Claude to identify gaps in our metrics...")
    gap_prompt = f"""You are a writing style analyst.

Here is a computational voice profile for an author (JSON metrics extracted by Python):
```json
{profile_json_str}
```

Here are samples of the author's actual writing:
{sample_text}

Identify 5-8 specific style elements that our computational metrics MISS but are crucial to this author's voice. Focus on patterns that would help an AI generate more authentic text in this person's style.

For each gap, explain:
- What the element is
- Why it matters for this author specifically
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
    prompt_prompt = f"""You are helping build a voice profile that guides AI text generation to sound like a specific author.

Current computational metrics:
```json
{profile_json_str}
```

Current English instructions (generated from metrics):
{english_instructions[:1500]}

Style gaps identified:
{json.dumps(gap_analysis[:5], indent=2) if gap_analysis else "None identified"}

Author samples:
{sample_text[:2000]}

Write 3-5 concise voice prompts (1-2 sentences each) that capture this author's writing style. These prompts will be prepended to AI generation requests. Focus on aspects NOT already covered by the English instructions above — especially the gaps. Be specific to this author's voice, not generic writing advice.

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
            full_profile, "Personal AI-Enhanced"
        )
        print(f"  Profile ID: {profile_id}")

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
        "Write a short article about the challenges of transitioning from a developer to a technical leader.",
        "Write a reflection on how AI is changing the landscape for software teams and what leaders should do about it.",
        "Write an opinion piece about why most corporate motivational advice fails and what actually works for tech teams.",
    ]

    # Build enhanced english instructions
    enhanced_english = english_instructions
    if ai_prompts:
        enhanced_english += "\n\n## Additional Style Directives\n"
        enhanced_english += "\n".join(f"- {p}" for p in ai_prompts)
    if gap_analysis:
        enhanced_english += "\n\n## Style Elements to Emphasize\n"
        for gap in gap_analysis:
            instr = gap.get("instruction", gap.get("description", ""))
            enhanced_english += f"- {gap.get('name', '?')}: {instr}\n"

    scoring_formats = {
        "english_only_python": {"english_instructions": english_instructions},
        "english_only_enhanced": {"english_instructions": enhanced_english},
        "json_only": {"profile_json": profile_json_str, "english_instructions": None},
        "both_enhanced": {"profile_json": profile_json_str, "english_instructions": enhanced_english},
    }

    generation_results = []

    for i, prompt in enumerate(test_prompts, 1):
        print(f"\n--- Prompt {i}: {prompt[:60]}... ---")

        print("  Generating text...")
        try:
            generated = _generate_text_with_voice(profile_id, prompt)
        except requests.RequestException as e:
            print(f"  ERROR generating: {e}")
            generation_results.append({"prompt": prompt, "error": str(e)})
            continue

        if not generated or generated == "Generate new content.":
            print("  WARNING: Generation returned empty/unchanged.")
            generation_results.append({"prompt": prompt, "error": "generation failed"})
            continue

        print(f"  Generated {len(generated)} chars")
        print(f"  Preview: {generated[:120]}...\n")

        scores = {}
        for fmt_name, fmt_kwargs in scoring_formats.items():
            print(f"  Scoring ({fmt_name})...", end=" ", flush=True)
            result = _score_similarity_with_ai(
                generated, "Stephen Salaka", **fmt_kwargs
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
        "experiment": "personal_writing_ai_enhanced",
        "gap_analysis": gap_analysis,
        "ai_prompts": ai_prompts,
        "enhanced_english_instructions": enhanced_english,
        "generation_results": generation_results,
    }
    report_path = save_report("personal_writing_ai_enhanced", report)
    print(f"\nReport saved: {report_path}")

    # --- Print Summary ---
    fmt_names = list(scoring_formats.keys())
    print(f"\n{'='*60}")
    print("AI-ENHANCED PERSONAL WRITING SCORING SUMMARY")
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

    # Compare
    print(f"\n{'='*60}")
    print("COMPARISON: PYTHON-ONLY vs AI-ENHANCED")
    print(f"{'='*60}")
    py_avg = sum(fmt_totals.get("english_only_python", [])) / len(fmt_totals.get("english_only_python", [1])) if fmt_totals.get("english_only_python") else 0
    ai_avg = sum(fmt_totals.get("english_only_enhanced", [])) / len(fmt_totals.get("english_only_enhanced", [1])) if fmt_totals.get("english_only_enhanced") else 0
    json_avg = sum(fmt_totals.get("json_only", [])) / len(fmt_totals.get("json_only", [1])) if fmt_totals.get("json_only") else 0
    both_avg = sum(fmt_totals.get("both_enhanced", [])) / len(fmt_totals.get("both_enhanced", [1])) if fmt_totals.get("both_enhanced") else 0
    print(f"  english_only (Python):    {py_avg:.1f}")
    print(f"  english_only (Enhanced):  {ai_avg:.1f}")
    print(f"  json_only:                {json_avg:.1f}")
    print(f"  both_enhanced:            {both_avg:.1f}")

    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Personal writing voice profile experiment"
    )
    parser.add_argument(
        "--generate",
        action="store_true",
        help="Run generation + scoring experiment after parsing",
    )
    parser.add_argument(
        "--parse-only",
        action="store_true",
        help="Only parse corpus and show training curve",
    )
    parser.add_argument(
        "--max-files",
        type=int,
        default=0,
        help="Limit number of files to parse (0 = all)",
    )
    parser.add_argument(
        "--ai-enhance",
        action="store_true",
        help="Run AI-enhanced experiment (gap analysis + AI prompts)",
    )
    args = parser.parse_args()

    # Parse corpus
    full_profile, file_results, training_curve = parse_personal_corpus(
        max_files=args.max_files
    )

    if full_profile is None:
        sys.exit(1)

    # Print profile summary
    print_profile_summary(full_profile, "Full Personal Writing Profile")

    # Save parse report
    total_words = sum(r["word_count"] for r in file_results)
    parse_report = {
        "experiment": "personal_writing_parse",
        "num_files": len(file_results),
        "total_words": total_words,
        "training_curve": training_curve,
        "full_profile_json": json.loads(profile_to_json_for_ai(full_profile)),
        "individual_file_word_counts": {
            r["filename"]: r["word_count"] for r in file_results
        },
    }
    report_path = save_report("personal_writing_parse", parse_report)
    print(f"\nParse report saved: {report_path}")

    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    print(f"Files parsed: {len(file_results)}")
    print(f"Total words:  {total_words:,}")
    print("\nTraining curve:")
    for entry in training_curve:
        print(
            f"  {entry['num_files']} files ({entry['total_words']:,} words): "
            f"{entry['similarity_to_full']:.4f} similarity"
        )

    # Generation experiments
    if not args.parse_only and not args.ai_enhance:
        gen_report = run_generation_experiment(full_profile)

    if args.ai_enhance:
        ai_report = run_ai_enhanced_experiment(full_profile)
