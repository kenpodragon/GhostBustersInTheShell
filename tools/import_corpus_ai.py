#!/usr/bin/env python3
"""Import Stephen's corpus with AI extraction enabled.

Reads .txt files from local_data/corpus/personal/, calls the parse API
with use_ai=true and filename for each file. Skips files <500 words.

Usage: python tools/import_corpus_ai.py
Requires: backend running on localhost:8066 with AI enabled
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
EXPORT_PATH = Path(__file__).resolve().parent.parent.parent / "docs" / "voice_profiles" / f"stephen_voice_baseline_export_{datetime.now().strftime('%m%d%Y')}_65_ai.json"
MIN_WORDS = 500
MAX_WORDS = 15000  # AI extraction context limit — truncate longer files


def main():
    # 1. Verify AI is available
    print("Checking AI status...")
    try:
        r = requests.get(f"{API_BASE}/api/ai-status", timeout=10)
        if r.status_code == 200:
            status = r.json()
            print(f"  AI enabled: {status.get('enabled')}, provider: {status.get('provider')}")
            if not status.get("enabled"):
                print("  WARNING: AI is not enabled. Observations will not be generated.")
                resp = input("  Continue anyway? (y/n): ")
                if resp.lower() != "y":
                    sys.exit(0)
    except Exception as e:
        print(f"  Could not check AI status: {e}")

    # 2. Gather corpus files
    txt_files = sorted(CORPUS_DIR.glob("*.txt"))
    print(f"\nFound {len(txt_files)} .txt files in {CORPUS_DIR}")

    # Pre-filter by word count, truncate oversized files
    eligible = []
    for fpath in txt_files:
        text = fpath.read_text(encoding="utf-8", errors="replace")
        wc = len(text.split())
        if wc < MIN_WORDS:
            print(f"  SKIP {fpath.name} ({wc} words < {MIN_WORDS})")
            continue
        if wc > MAX_WORDS:
            words = text.split()
            text = " ".join(words[:MAX_WORDS])
            print(f"  TRUNCATE {fpath.name} ({wc:,} -> {MAX_WORDS:,} words)")
            wc = MAX_WORDS
        eligible.append((fpath, text, wc))

    print(f"\n{len(eligible)} files eligible for import ({len(txt_files) - len(eligible)} skipped)\n")

    parsed = 0
    ai_success = 0
    errors = 0
    total_words = 0

    for i, (fpath, text, wc) in enumerate(eligible, 1):
        fname = fpath.stem  # filename without extension
        print(f"  [{i:2d}/{len(eligible)}] {fname} ({wc:,} words)...", end=" ", flush=True)
        t0 = time.time()
        try:
            r = requests.post(
                f"{API_BASE}/api/voice-profiles/{PROFILE_ID}/parse",
                json={
                    "text": text,
                    "filename": fname,
                    "use_ai": True,
                },
                timeout=300,
            )
            elapsed = time.time() - t0
            if r.status_code == 200:
                data = r.json()
                ai_status = data.get("ai_extraction", {}).get("status", "unknown")
                parsed += 1
                total_words += wc
                if ai_status == "success":
                    ai_success += 1
                    prompts = len(data.get("ai_extraction", {}).get("qualitative_prompts", []))
                    print(f"OK ({elapsed:.1f}s) AI:{ai_status} ({prompts} prompts)")
                else:
                    print(f"OK ({elapsed:.1f}s) AI:{ai_status}")
            elif r.status_code == 409:
                data = r.json()
                print(f"DUP ({elapsed:.1f}s): {data.get('error', '')[:80]}")
            else:
                errors += 1
                print(f"FAIL {r.status_code} ({elapsed:.1f}s): {r.text[:200]}")
        except Exception as e:
            errors += 1
            elapsed = time.time() - t0
            print(f"ERROR ({elapsed:.1f}s): {e}")

    print(f"\n{'='*60}")
    print(f"Import complete:")
    print(f"  Parsed: {parsed}/{len(eligible)}")
    print(f"  AI extractions: {ai_success}/{parsed}")
    print(f"  Errors: {errors}")
    print(f"  Total words: {total_words:,}")
    print(f"{'='*60}")

    # 3. Fetch final profile and export
    print("\nFetching final profile...")
    r = requests.get(f"{API_BASE}/api/voice-profiles/{PROFILE_ID}")
    if r.status_code != 200:
        print(f"FAILED to fetch profile: {r.status_code}")
        sys.exit(1)

    profile_data = r.json()
    elements = profile_data.get("elements", [])
    print(f"Total elements: {len(elements)}, parse_count: {profile_data.get('parse_count')}")

    export = {
        "export_date": datetime.now(timezone.utc).isoformat(),
        "element_count": len(elements),
        "ai_observations": ai_success,
        "total_words": total_words,
        "profile": {
            "name": profile_data.get("name", ""),
            "description": profile_data.get("description", ""),
            "profile_type": profile_data.get("profile_type", ""),
            "parse_count": profile_data.get("parse_count", 0),
            "is_active": profile_data.get("is_active", False),
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
    print(f"Exported to {EXPORT_PATH}")


if __name__ == "__main__":
    main()
