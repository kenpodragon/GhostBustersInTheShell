"""Voice format experiment harness.

Runs format experiments against Claude, scores output against
Stephen's voice profile, outputs comparison tables.

Usage:
  python tools/voice_format_harness.py assess     # E.1: AI self-assessment
  python tools/voice_format_harness.py test-json   # E.2: JSON-only generation test
  python tools/voice_format_harness.py test-all    # E.2+E.3: All format variants
  python tools/voice_format_harness.py compare     # Compare results across experiments
"""
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

from harness_config import PROFILE_ID, API_BASE, RESULTS_DIR, TEST_INPUTS_DIR, CLAUDE_TIMEOUT


def load_profile_elements(profile_id: int = PROFILE_ID) -> list[dict]:
    """Load voice profile elements from the API."""
    resp = requests.get(f"{API_BASE}/api/voice-profiles/{profile_id}")
    resp.raise_for_status()
    return resp.json()["elements"]


def format_elements_json(elements: list[dict]) -> str:
    """Format elements as a JSON array for prompts."""
    compact = [
        {
            "name": e["name"],
            "category": e.get("category", ""),
            "element_type": e.get("element_type", ""),
            "target_value": e.get("target_value") or e.get("weight", 0.5),
        }
        for e in elements
    ]
    return json.dumps(compact, indent=2)


def format_elements_english(elements: list[dict]) -> str:
    """Format elements as English instructions using weight_translator."""
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
    from utils.weight_translator import translate_element
    lines = []
    for e in elements:
        translated = translate_element(e)
        if translated:
            lines.append(f"- {translated}")
    return "\n".join(lines)


def call_claude(prompt: str, timeout: int = 300) -> dict:
    """Call Claude via CLI with configurable timeout.

    The Claude CLI with --output-format json wraps responses in:
      {"type": "result", "result": "<text>", ...}

    The "result" field is a TEXT string, NOT parsed JSON. Claude may also
    write files instead of returning data inline. We handle both cases.
    """
    import subprocess
    import re
    import glob

    # Snapshot existing JSON files in tools/ before the call
    tools_dir = Path(__file__).resolve().parent
    pre_files = set(tools_dir.glob("*.json"))

    cmd = ["claude", "-p", prompt, "--output-format", "json"]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)

    if result.returncode != 0:
        raise RuntimeError(f"Claude CLI error: {result.stderr.strip()[:300]}")

    output = result.stdout.strip()

    # Step 1: Unwrap the CLI wrapper to get the inner text
    inner_text = output
    try:
        parsed = json.loads(output)
        if isinstance(parsed, dict) and "result" in parsed:
            inner_text = parsed["result"]
            if not isinstance(inner_text, str):
                return inner_text  # Already a dict/list
    except json.JSONDecodeError:
        pass  # output wasn't JSON at all, use as-is

    # Step 2: Try to parse inner_text as JSON directly
    try:
        # Strip code fences if present
        fence_match = re.search(r'```(?:json)?\s*\n?(.*?)```', inner_text, re.DOTALL)
        if fence_match:
            return json.loads(fence_match.group(1).strip())
        return json.loads(inner_text)
    except (json.JSONDecodeError, ValueError):
        pass

    # Step 3: Claude may have written a file — check for new JSON files
    post_files = set(tools_dir.glob("*.json"))
    new_files = post_files - pre_files
    if new_files:
        # Read the newest file Claude wrote
        newest = max(new_files, key=lambda f: f.stat().st_mtime)
        print(f"  (Claude wrote file: {newest.name}, reading it)")
        with open(newest) as f:
            return json.load(f)

    # Step 4: Try to extract JSON from mixed text
    match = re.search(r'\{[\s\S]*\}', inner_text)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    raise RuntimeError(f"Claude returned no parseable JSON. Response: {inner_text[:500]}")


def score_output(generated_text: str, profile_elements: list[dict]) -> dict:
    """Score generated text against the voice profile."""
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
    from utils.voice_fidelity_scorer import score_fidelity
    return score_fidelity(
        generated_text=generated_text,
        profile_elements=profile_elements,
        mode="quantitative",
    )


def load_test_input(name: str) -> str:
    """Load a test input passage by name."""
    path = TEST_INPUTS_DIR / f"{name}.txt"
    return path.read_text(encoding="utf-8")


def save_result(experiment_name: str, result: dict):
    """Save experiment result to JSON file."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = RESULTS_DIR / f"{experiment_name}_{timestamp}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    print(f"Saved: {path}")
    return path


# ---------------------------------------------------------------------------
# E.1 Self-Assessment
# ---------------------------------------------------------------------------

def run_self_assessment():
    """E.1: Ask Claude which elements it can control."""
    print("=== E.1: AI Self-Assessment ===\n")

    elements = load_profile_elements()
    elements_json = format_elements_json(elements)

    from format_experiments import build_self_assessment_prompt
    prompt = build_self_assessment_prompt(elements_json)

    print(f"Sending {len(elements)} elements to Claude for self-assessment...")
    t0 = time.time()
    response = call_claude(prompt)
    elapsed = time.time() - t0
    print(f"Response received in {elapsed:.1f}s\n")

    # Debug: dump response shape
    print(f"Response type: {type(response).__name__}")
    print(f"Response keys: {list(response.keys()) if isinstance(response, dict) else 'N/A'}")
    # Save raw response for debugging
    debug_path = RESULTS_DIR / "e1_debug_raw_response.json"
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(debug_path, "w", encoding="utf-8") as f:
        json.dump(response, f, indent=2)
    print(f"Raw response saved to: {debug_path}\n")

    assessments = response.get("assessments", [])

    controllable = [a for a in assessments if a["controllable"] == "yes"]
    partial = [a for a in assessments if a["controllable"] == "partially"]
    opaque = [a for a in assessments if a["controllable"] == "no"]

    print(f"Results:")
    print(f"  Controllable (yes):   {len(controllable)}")
    print(f"  Partial:              {len(partial)}")
    print(f"  Opaque (no):          {len(opaque)}")

    print(f"\n--- Controllable ({len(controllable)}) ---")
    for a in controllable:
        print(f"  {a['element']}: {a['implementation'][:80]}")

    print(f"\n--- Partial ({len(partial)}) ---")
    for a in partial:
        print(f"  {a['element']}: {a['notes'][:80]}")

    print(f"\n--- Opaque ({len(opaque)}) ---")
    for a in opaque:
        print(f"  {a['element']}: {a['notes'][:80]}")

    result = {
        "experiment": "e1_self_assessment",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "element_count": len(elements),
        "assessments": assessments,
        "summary": {
            "controllable": len(controllable),
            "partial": len(partial),
            "opaque": len(opaque),
        },
    }
    save_result("e1_self_assessment", result)
    return result


# ---------------------------------------------------------------------------
# E.2 JSON Tests
# ---------------------------------------------------------------------------

def run_experiment(
    experiment_name: str,
    prompt_builder,
    input_name: str = "neutral_passage",
) -> dict:
    """Run a single format experiment: generate with Claude, score output."""
    elements = load_profile_elements()
    input_text = load_test_input(input_name)

    elements_json = format_elements_json(elements)
    prompt = prompt_builder(elements_json, input_text)

    print(f"  Calling Claude ({experiment_name}, input={input_name})...", end=" ", flush=True)
    t0 = time.time()
    response = call_claude(prompt)
    elapsed = time.time() - t0

    rewritten = response.get("rewritten_text", "")
    if not rewritten:
        print(f"FAIL ({elapsed:.1f}s) — no rewritten_text in response")
        return {"experiment": experiment_name, "input_name": input_name, "error": "no rewritten_text", "raw_response": response}

    print(f"OK ({elapsed:.1f}s, {len(rewritten.split())} words)")

    scores = score_output(rewritten, elements)

    result = {
        "experiment": experiment_name,
        "input_name": input_name,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "elapsed_seconds": elapsed,
        "aggregate_similarity": scores["aggregate_similarity"],
        "elements_matched": scores["elements_matched"],
        "elements_missing": scores["elements_missing"],
        "per_element": scores["per_element"],
        "rewritten_text": rewritten,
        "notes": response.get("notes") or response.get("verification", ""),
    }
    return result


def run_json_tests():
    """E.2: Test JSON-only and JSON-enforced generation."""
    print("=== E.2: JSON Generation Tests ===\n")

    from format_experiments import build_json_only_prompt, build_json_enforced_prompt

    all_results = []
    for input_name in ["neutral_passage", "ai_sounding_passage"]:
        print(f"\n--- Input: {input_name} ---")
        result_json = run_experiment("e2a_json_only", build_json_only_prompt, input_name)
        all_results.append(result_json)
        result_enforced = run_experiment("e2b_json_enforced", build_json_enforced_prompt, input_name)
        all_results.append(result_enforced)

    print(f"\n{'='*60}")
    print(f"{'Experiment':<25} {'Input':<22} {'Fidelity':>8}")
    print(f"{'-'*25} {'-'*22} {'-'*8}")
    for r in all_results:
        if "error" not in r:
            print(f"{r['experiment']:<25} {r['input_name']:<22} {r['aggregate_similarity']:>7.1%}")
        else:
            print(f"{r['experiment']:<25} {r['input_name']:<22} {'ERROR':>8}")
    print(f"{'='*60}")

    save_result("e2_json_tests", {"experiments": all_results})
    return all_results


# ---------------------------------------------------------------------------
# E.3 English + Hybrid
# ---------------------------------------------------------------------------

def run_english_test():
    """E.3a: Test English-only generation (current format baseline)."""
    print("=== E.3a: English-Only Generation Test (Baseline) ===\n")

    from format_experiments import build_english_only_prompt

    elements = load_profile_elements()
    english = format_elements_english(elements)

    def english_builder(_elements_json, input_text):
        return build_english_only_prompt(english, input_text)

    all_results = []
    for input_name in ["neutral_passage", "ai_sounding_passage"]:
        print(f"\n--- Input: {input_name} ---")
        result = run_experiment("e3a_english_only", english_builder, input_name)
        all_results.append(result)

    save_result("e3a_english_only", {"experiments": all_results})
    return all_results


def run_hybrid_test(assessment_path: str = None):
    """E.3b: Hybrid — JSON for controllable elements, English for the rest."""
    print("=== E.3b: Hybrid Format Test ===\n")

    if assessment_path:
        assess_file = Path(assessment_path)
    else:
        result_files = sorted(RESULTS_DIR.glob("e1_self_assessment_*.json"), reverse=True)
        if not result_files:
            print("ERROR: No E.1 assessment results found. Run 'assess' first.")
            sys.exit(1)
        assess_file = result_files[0]

    print(f"Using assessment: {assess_file.name}")
    with open(assess_file) as f:
        assessment = json.load(f)

    assessments_by_name = {a["element"]: a for a in assessment["assessments"]}

    elements = load_profile_elements()

    controllable_elements = []
    indirect_elements = []
    for e in elements:
        a = assessments_by_name.get(e["name"], {})
        if a.get("controllable") == "yes":
            controllable_elements.append(e)
        else:
            indirect_elements.append(e)

    print(f"  Controllable (JSON): {len(controllable_elements)} elements")
    print(f"  Indirect (English):  {len(indirect_elements)} elements")

    controllable_json = format_elements_json(controllable_elements)
    indirect_english = format_elements_english(indirect_elements)

    from format_experiments import build_categorized_prompt

    def hybrid_builder(_elements_json, input_text):
        return build_categorized_prompt(controllable_json, indirect_english, input_text)

    all_results = []
    for input_name in ["neutral_passage", "ai_sounding_passage"]:
        print(f"\n--- Input: {input_name} ---")
        result = run_experiment("e3b_hybrid", hybrid_builder, input_name)
        all_results.append(result)

    save_result("e3b_hybrid", {"experiments": all_results})
    return all_results


# ---------------------------------------------------------------------------
# Compare Command
# ---------------------------------------------------------------------------

def run_compare():
    """Compare results across all experiments."""
    print("=== Format Experiment Comparison ===\n")

    result_files = sorted(RESULTS_DIR.glob("e*.json"))
    if not result_files:
        print("No results found. Run experiments first.")
        sys.exit(1)

    all_experiments = []
    for f in result_files:
        with open(f) as fp:
            data = json.load(fp)
        if "experiments" in data:
            all_experiments.extend(data["experiments"])
        elif "experiment" in data:
            all_experiments.append(data)

    scored = [e for e in all_experiments if "aggregate_similarity" in e]

    if not scored:
        print("No scored experiments found.")
        return

    print(f"{'Experiment':<25} {'Input':<22} {'Fidelity':>8} {'Matched':>8}")
    print(f"{'-'*25} {'-'*22} {'-'*8} {'-'*8}")
    for r in sorted(scored, key=lambda x: (x["experiment"], x["input_name"])):
        print(f"{r['experiment']:<25} {r['input_name']:<22} {r['aggregate_similarity']:>7.1%} {r['elements_matched']:>7d}")

    print(f"\n\n=== Per-Element Best Format ===\n")
    element_best = {}
    for r in scored:
        for pe in r.get("per_element", []):
            name = pe["name"]
            sim = pe["similarity"]
            exp = r["experiment"]
            if name not in element_best or sim > element_best[name]["similarity"]:
                element_best[name] = {"format": exp, "similarity": sim}

    print(f"{'Element':<35} {'Best Format':<25} {'Fidelity':>8}")
    print(f"{'-'*35} {'-'*25} {'-'*8}")
    for name in sorted(element_best.keys()):
        b = element_best[name]
        print(f"{name:<35} {b['format']:<25} {b['similarity']:>7.1%}")

    routing_table = {
        name: {"format": b["format"], "similarity": b["similarity"]}
        for name, b in element_best.items()
    }
    save_result("routing_table", routing_table)
    print(f"\nRouting table saved.")


# ---------------------------------------------------------------------------
# CLI Dispatcher
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) < 2:
        print("Usage: python tools/voice_format_harness.py <command>")
        print("Commands: assess, test-json, test-english, test-hybrid, test-all, compare")
        sys.exit(1)

    command = sys.argv[1]
    if command == "assess":
        run_self_assessment()
    elif command == "test-json":
        run_json_tests()
    elif command == "test-english":
        run_english_test()
    elif command == "test-hybrid":
        run_hybrid_test(sys.argv[2] if len(sys.argv) > 2 else None)
    elif command == "test-all":
        run_json_tests()
        run_english_test()
        run_hybrid_test()
    elif command == "compare":
        run_compare()
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
