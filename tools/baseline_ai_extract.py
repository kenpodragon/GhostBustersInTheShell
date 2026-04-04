#!/usr/bin/env python3
"""Extract AI voice prompts from 20 representative baseline corpus files.

Parses each file with heuristics (65 elements), then runs AI extraction
to produce qualitative prompts. Results are consolidated and merged into
the baseline export JSON.

Usage (inside Docker container):
    python /tools/baseline_ai_extract.py

Requires: AI provider enabled (Claude CLI).
"""
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend"))
if not os.path.isdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend")):
    sys.path.insert(0, "/app")

from utils.voice_generator import generate_voice_profile
from utils.ai_voice_extractor import extract_voice_with_ai

CORPUS_DIR = Path(__file__).resolve().parent.parent.parent / "local_data" / "modern_human_td"
if not CORPUS_DIR.is_dir():
    CORPUS_DIR = Path("/local_data/modern_human_td")

EXPORT_DIR = Path(__file__).resolve().parent.parent.parent / "local_data"
if not EXPORT_DIR.is_dir():
    EXPORT_DIR = Path("/local_data")

COOLDOWN = 5  # seconds between AI calls

# 20 representative files selected by similarity to baseline + source diversity
SELECTED_FILES = [
    "salon_Taylor_Frankie_Pauls_dirty_laundry_is_our_reality_check_374e2dc2c6.txt",
    "wired_At_Gazas_Al-Shifa_Hospital_the_War_Isnt_Over_d14103ae00.txt",
    "theatlantic_Building_Tanks_While_the_Ukrainians_Master_Drones_2b5ddfdc0a.txt",
    "theatlantic_The_Surprising_Reason_for_the_New_Homophobia_53378c9bf8.txt",
    "wiki_History_of_cricket_04344ea341.txt",
    "theatlantic_Welcome_to_a_Multidimensional_Economic_Disaster_e0ccbe82e1.txt",
    "salon_ICE_at_the_airport_is_just_the_beginning_6358c07d88.txt",
    "salon_Melissa_Auf_der_Maurs_memoir_captures_the_beauty_and_brutality_of_90s_rock_24dc924fa6.txt",
    "pbs_Israel_launches_new_strikes_on_Iran_as_Rubio_says_war_could_end_in_a_matter_of_w_1f6f8c9150.txt",
    "bbc_Iran_war_splits_older_and_younger_conservatives_-_as_pressure_builds_for_Trump_t_5cdb590d14.txt",
    "devto_Gemini_25_Flash_vs_Claude_37_Sonnet_4_Production_Constraints_That_Made_the_Decis_3dd4482169.txt",
    "theverge_The_latest_in_data_centers_AI_and_energy_76fb7e2ba2.txt",
    "npr_How_long_will_the_war_last_No_one_knows_and_its_making_oil_prices_weird_45d38cf03d.txt",
    "bbc_The_gravest_crime_against_humanity_What_does_the_UN_vote_on_slavery_mean_3baabf073a.txt",
    "wired_10_Things_You_Can_Do_While_Waiting_in_the_TSA_Line_ef2705185f.txt",
    "ap_top_House_ethics_panel_finds_Florida_congresswoman_committed_numerous_violations_f7c388a1f4.txt",
    "wiki_Imperial_Japanese_Navy_ship_classifications_9f26eb5895.txt",
    "devto_Weve_Seen_This_Movie_Before_c68690ab99.txt",
    "salon_On_The_Comeback_AI_gets_the_last_laugh_43e82ca8e4.txt",
    "theatlantic_Airfare_Is_Just_the_Beginning_93e2d245d1.txt",
]

# State file for resume support
STATE_FILE = EXPORT_DIR / "baseline_ai_state.json"


def load_state():
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"completed": [], "results": []}


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def main():
    state = load_state()
    completed = set(state["completed"])
    results = state["results"]

    # Verify files exist
    missing = []
    for fname in SELECTED_FILES:
        fpath = CORPUS_DIR / fname
        if not fpath.exists():
            # Try fuzzy match (filenames may be truncated in the selection)
            matches = list(CORPUS_DIR.glob(fname[:60] + "*"))
            if matches:
                idx = SELECTED_FILES.index(fname)
                SELECTED_FILES[idx] = matches[0].name
            else:
                missing.append(fname)

    if missing:
        print(f"WARNING: {len(missing)} files not found:")
        for m in missing:
            print(f"  {m}")

    remaining = [f for f in SELECTED_FILES if f not in completed and f not in missing]
    print(f"Files: {len(SELECTED_FILES)} selected, {len(completed)} done, {len(remaining)} remaining")

    for i, fname in enumerate(remaining, 1):
        fpath = CORPUS_DIR / fname
        text = fpath.read_text(encoding="utf-8", errors="replace")
        word_count = len(text.split())
        print(f"\n[{i}/{len(remaining)}] {fname[:60]}... ({word_count} words)")

        # Step 1: Heuristic parse
        try:
            parsed = generate_voice_profile(text)
            print(f"  Parsed: {len(parsed)} elements")
        except Exception as e:
            print(f"  SKIP (parse error): {e}")
            continue

        # Step 2: AI extraction
        print(f"  Extracting with AI...")
        result = extract_voice_with_ai(text, parsed)
        print(f"  Status: {result['status']}, prompts: {len(result['qualitative_prompts'])}, "
              f"patterns: {len(result['discovered_patterns'])}")

        if result["status"] == "success":
            results.append({
                "filename": fname,
                "word_count": word_count,
                "qualitative_prompts": result["qualitative_prompts"],
                "metric_descriptions": result["metric_descriptions"],
                "discovered_patterns": result["discovered_patterns"],
            })

        completed.add(fname)
        state["completed"] = list(completed)
        state["results"] = results
        save_state(state)

        if i < len(remaining):
            print(f"  Cooling down {COOLDOWN}s...")
            time.sleep(COOLDOWN)

    # Consolidate prompts
    all_prompts = []
    all_patterns = []
    for r in results:
        all_prompts.extend(r.get("qualitative_prompts", []))
        all_patterns.extend(r.get("discovered_patterns", []))

    print(f"\n--- Consolidation ---")
    print(f"Total prompts: {len(all_prompts)}")
    print(f"Total patterns: {len(all_patterns)}")

    # Simple dedup by prompt text similarity
    from difflib import SequenceMatcher
    THRESHOLD = 0.3

    clusters = []
    for p in all_prompts:
        text = p.get("prompt", "")[:200]
        placed = False
        for c in clusters:
            ratio = SequenceMatcher(None, text, c["representative"][:200]).ratio()
            if ratio > (1 - THRESHOLD):
                c["members"].append(p)
                c["frequency"] += 1
                c["avg_confidence"] = (
                    sum(m.get("confidence", 0.5) for m in c["members"]) / len(c["members"])
                )
                placed = True
                break
        if not placed:
            clusters.append({
                "representative": text,
                "members": [p],
                "frequency": 1,
                "avg_confidence": p.get("confidence", 0.5),
            })

    clusters.sort(key=lambda c: c["frequency"], reverse=True)
    print(f"Clusters: {len(clusters)} (from {len(all_prompts)} prompts)")

    # Keep clusters with freq >= 2 for baseline (lower threshold than Stephen's 5)
    significant = [c for c in clusters if c["frequency"] >= 2]
    print(f"Significant (freq >= 2): {len(significant)}")

    consolidated_prompts = [
        {
            "prompt": c["representative"],
            "frequency": c["frequency"],
            "confidence": round(c["avg_confidence"], 3),
        }
        for c in significant
    ]

    # Export
    export = {
        "ai_extraction_summary": {
            "files_processed": len(results),
            "total_prompts": len(all_prompts),
            "total_patterns": len(all_patterns),
            "clusters": len(clusters),
            "significant_clusters": len(significant),
        },
        "consolidated_prompts": consolidated_prompts,
        "all_clusters": [
            {
                "representative": c["representative"],
                "frequency": c["frequency"],
                "avg_confidence": round(c["avg_confidence"], 3),
            }
            for c in clusters
        ],
        "discovered_patterns": all_patterns,
    }

    export_path = EXPORT_DIR / "baseline_ai_prompts_20260404.json"
    with open(export_path, "w") as f:
        json.dump(export, f, indent=2)
    print(f"\nExported to: {export_path}")

    # Show top prompts
    print(f"\n--- Top 15 consolidated prompts ---")
    for i, p in enumerate(consolidated_prompts[:15], 1):
        print(f"  {i}. [freq={p['frequency']}, conf={p['confidence']}] {p['prompt'][:80]}")


if __name__ == "__main__":
    main()
