#!/usr/bin/env python3
"""Synthesize 101 baseline voice prompts into 10-15 general human writing directives.

Reads the raw prompts from baseline_ai_prompts_20260404.json, sends them to AI
for synthesis, and outputs the general directives alongside the raw library.

Usage (inside Docker container):
    python /tools/baseline_synthesize_prompts.py
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend"))
if not os.path.isdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend")):
    sys.path.insert(0, "/app")

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "local_data"
if not DATA_DIR.is_dir():
    DATA_DIR = Path("/local_data")

SYNTHESIS_PROMPT = """You are analyzing 101 voice directives extracted from 20 diverse human-written articles
(news, tech blogs, opinion, memoir, wiki, economics, politics, culture, sports, lifestyle).

Your task: synthesize these into 10-15 GENERAL human writing directives that capture what makes
human writing sound human — patterns that appear across multiple authors and genres.

These directives will be used as the DEFAULT voice profile for an AI text humanization tool.
They should NOT describe any single author's voice. They should describe universal qualities
of natural human writing that distinguish it from AI-generated text.

Focus on:
- Structural patterns (sentence variety, paragraph rhythm, pacing)
- Voice qualities (directness, specificity, emotional texture)
- Rhetorical patterns (how humans build arguments, use evidence, create flow)
- What humans do that AI typically doesn't (imperfection, personality, surprise)

Do NOT include:
- Author-specific styles (e.g., "write like a cultural critic")
- Topic-specific advice (e.g., "anchor humanitarian crises in objects")
- Overly prescriptive rules (e.g., exact percentages or counts)

Here are the 101 prompts:

{prompts_text}

Return ONLY valid JSON:
{{
  "synthesized_directives": [
    {{"prompt": "the directive (2-3 sentences)", "confidence": 0.0-1.0, "source_count": N}}
  ]
}}"""


def main():
    # Load raw prompts
    prompts_file = DATA_DIR / "baseline_ai_prompts_20260404.json"
    with open(prompts_file) as f:
        data = json.load(f)

    all_clusters = data["all_clusters"]
    print(f"Loaded {len(all_clusters)} raw prompts")

    # Format prompts for AI
    prompts_text = "\n".join(
        f"{i}. [{c['avg_confidence']:.2f}] {c['representative']}"
        for i, c in enumerate(all_clusters, 1)
    )

    prompt = SYNTHESIS_PROMPT.format(prompts_text=prompts_text)

    # Get AI provider
    from ai_providers.router import _get_provider
    provider = _get_provider()
    if not provider:
        print("ERROR: No AI provider available")
        sys.exit(1)

    print("Sending to AI for synthesis...")
    result = provider._run_cli(prompt)

    directives = result.get("synthesized_directives", [])
    print(f"Got {len(directives)} synthesized directives")

    # Update the baseline export with both library and synthesized
    data["synthesized_directives"] = directives
    data["ai_extraction_summary"]["synthesized_count"] = len(directives)

    with open(prompts_file, "w") as f:
        json.dump(data, f, indent=2)
    print(f"Updated: {prompts_file}")

    # Also merge into the main baseline export
    baseline_files = sorted(DATA_DIR.glob("modern_human_baseline_export_*_65.json"))
    if baseline_files:
        baseline_path = baseline_files[-1]
        with open(baseline_path) as f:
            baseline = json.load(f)

        baseline["prompt_library"] = [c["representative"] for c in all_clusters]
        baseline["profile_prompts"] = [
            {"prompt": d["prompt"], "confidence": d.get("confidence", 0.8)}
            for d in directives
        ]
        baseline["ai_extraction"] = data["ai_extraction_summary"]

        with open(baseline_path, "w") as f:
            json.dump(baseline, f, indent=2)
        print(f"Merged into baseline: {baseline_path}")

    # Display
    print(f"\n--- Synthesized Directives ({len(directives)}) ---")
    for i, d in enumerate(directives, 1):
        sources = d.get("source_count", "?")
        conf = d.get("confidence", 0)
        print(f"\n{i}. [sources={sources}, conf={conf:.2f}]")
        print(f"   {d['prompt']}")


if __name__ == "__main__":
    main()
