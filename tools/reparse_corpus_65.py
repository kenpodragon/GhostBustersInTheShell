#!/usr/bin/env python3
"""Re-parse Stephen's corpus with 65-element voice profile (includes Tier 3 NLP elements).

Usage: python tools/reparse_corpus_65.py
Requires: backend running on localhost:8066, DB on localhost:5566
"""
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

API_BASE = "http://localhost:8066"
PROFILE_ID = 363
CORPUS_DIR = Path(__file__).resolve().parent.parent.parent / "local_data" / "corpus" / "personal"
EXPORT_PATH = Path(__file__).resolve().parent.parent.parent / "docs" / "voice_profiles" / "stephen_voice_baseline_export_03292026_65.json"
MIN_WORDS = 500

TIER3_ELEMENTS = [
    "sentiment_mean",
    "sentiment_variance",
    "sentiment_shift_rate",
    "topic_drift_rate",
    "topic_coherence_score",
    "vocabulary_concentration",
    "paragraph_opening_pos_entropy",
    "narrative_vs_analytical_ratio",
]


def main():
    # 1. Reset profile
    print(f"Resetting profile {PROFILE_ID}...")
    r = requests.post(f"{API_BASE}/api/voice-profiles/{PROFILE_ID}/reset")
    if r.status_code != 200:
        print(f"FAILED to reset: {r.status_code} {r.text}")
        sys.exit(1)
    print("Profile reset OK.\n")

    # 2. Gather corpus files
    txt_files = sorted(CORPUS_DIR.glob("*.txt"))
    print(f"Found {len(txt_files)} .txt files in {CORPUS_DIR}\n")

    parsed = 0
    skipped = 0
    errors = 0

    for i, fpath in enumerate(txt_files, 1):
        text = fpath.read_text(encoding="utf-8", errors="replace")
        word_count = len(text.split())

        if word_count < MIN_WORDS:
            print(f"  [{i:2d}/{len(txt_files)}] SKIP {fpath.name} ({word_count} words < {MIN_WORDS})")
            skipped += 1
            continue

        print(f"  [{i:2d}/{len(txt_files)}] Parsing {fpath.name} ({word_count:,} words)...", end=" ", flush=True)
        t0 = time.time()
        try:
            r = requests.post(
                f"{API_BASE}/api/voice-profiles/{PROFILE_ID}/parse",
                json={"text": text},
                timeout=300,
            )
            elapsed = time.time() - t0
            if r.status_code == 200:
                parsed += 1
                print(f"OK ({elapsed:.1f}s)")
            else:
                errors += 1
                print(f"FAIL {r.status_code} ({elapsed:.1f}s): {r.text[:200]}")
        except Exception as e:
            errors += 1
            print(f"ERROR: {e}")

    print(f"\nParsing complete: {parsed} parsed, {skipped} skipped, {errors} errors")

    # 3. Fetch final profile
    print("\nFetching final profile...")
    r = requests.get(f"{API_BASE}/api/voice-profiles/{PROFILE_ID}")
    if r.status_code != 200:
        print(f"FAILED to fetch profile: {r.status_code}")
        sys.exit(1)

    profile_data = r.json()
    elements = profile_data.get("elements", [])
    print(f"Total elements: {len(elements)}")

    # 4. Export
    export = {
        "export_date": datetime.now(timezone.utc).isoformat(),
        "element_count": len(elements),
        "profile": {
            "name": profile_data.get("name", ""),
            "description": profile_data.get("description", ""),
            "profile_type": profile_data.get("profile_type", ""),
            "parse_count": profile_data.get("parse_count", 0),
            "is_active": profile_data.get("is_active", False),
            "stack_order": profile_data.get("stack_order", 0),
            "created_at": profile_data.get("created_at", ""),
            "updated_at": profile_data.get("updated_at", ""),
        },
        "elements": [
            {
                "name": e["name"],
                "category": e.get("category", ""),
                "element_type": e.get("element_type", ""),
                "direction": e.get("direction"),
                "weight": e.get("weight"),
                "target_value": e.get("target_value"),
                "tags": e.get("tags", []),
                "source": e.get("source", "parsed"),
            }
            for e in elements
        ],
    }

    EXPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(EXPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(export, f, indent=4)
    print(f"\nExported to {EXPORT_PATH}")

    # 5. Print Tier 3 element values
    print("\n--- Tier 3 Element Values ---")
    for el in elements:
        if el["name"] in TIER3_ELEMENTS:
            print(f"  {el['name']}: target_value={el.get('target_value', 'N/A')}, weight={el.get('weight', 'N/A')}")

    print(f"\nDone. {len(elements)} elements in profile.")


if __name__ == "__main__":
    main()
