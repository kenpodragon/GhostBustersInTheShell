#!/usr/bin/env python3
"""Reparse modern human baseline corpus with 65 elements.

The baseline (518 files in local_data/modern_human_td/) was originally parsed
with 29 elements. This script reparses with the full 65-element pipeline
(Tier 1 regex + Tier 2 spaCy + Tier 3 VADER/TF-IDF).

Usage (inside Docker container):
    python tools/reparse_baseline_65.py

Requires: spaCy, VADER, scikit-learn available in the container.
Output: Aggregate baseline profile exported to docs/voice_profiles/
"""
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend"))
if not os.path.isdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend")):
    sys.path.insert(0, "/app")

from utils.voice_generator import generate_voice_profile

CORPUS_DIR = Path(__file__).resolve().parent.parent.parent / "local_data" / "modern_human_td"
EXPORT_DIR = Path(__file__).resolve().parent.parent.parent / "docs" / "voice_profiles"
MIN_WORDS = 500


def main():
    txt_files = sorted(CORPUS_DIR.glob("*.txt"))
    print(f"Found {len(txt_files)} .txt files in {CORPUS_DIR}")

    element_sums = {}
    parsed = 0
    skipped = 0
    errors = 0
    start = time.time()

    for i, fpath in enumerate(txt_files, 1):
        text = fpath.read_text(encoding="utf-8", errors="replace")
        word_count = len(text.split())

        if word_count < MIN_WORDS:
            skipped += 1
            continue

        try:
            result = generate_voice_profile(text)
        except Exception as e:
            print(f"  ERROR [{i}] {fpath.name}: {e}")
            errors += 1
            continue

        parsed += 1
        for el_name, el_data in result.items():
            if el_name not in element_sums:
                element_sums[el_name] = {
                    "weight_sum": 0.0,
                    "count": 0,
                    "category": el_data.get("category", ""),
                    "element_type": el_data.get("element_type", ""),
                    "tags": el_data.get("tags", []),
                }
            element_sums[el_name]["weight_sum"] += el_data.get("weight", 0)
            element_sums[el_name]["count"] += 1

        if parsed % 50 == 0:
            elapsed = time.time() - start
            print(f"  [{parsed}/{len(txt_files)}] {elapsed:.0f}s elapsed, {len(element_sums)} elements")

    elements = []
    for el_name, data in sorted(element_sums.items()):
        avg_weight = data["weight_sum"] / data["count"] if data["count"] > 0 else 0
        elements.append({
            "name": el_name,
            "category": data["category"],
            "element_type": data["element_type"],
            "weight": round(avg_weight, 6),
            "tags": data["tags"],
        })

    elapsed = time.time() - start
    print(f"\nDone: {parsed} parsed, {skipped} skipped (<{MIN_WORDS} words), {errors} errors")
    print(f"Elements: {len(elements)}, Time: {elapsed:.1f}s")

    export = {
        "profile_name": "Modern Human Baseline",
        "element_count": len(elements),
        "parse_count": parsed,
        "exported_at": datetime.now().isoformat(),
        "elements": elements,
    }
    export_path = EXPORT_DIR / f"modern_human_baseline_export_{datetime.now().strftime('%Y%m%d')}_{len(elements)}.json"
    with open(export_path, "w") as f:
        json.dump(export, f, indent=2)
    print(f"Exported to: {export_path}")


if __name__ == "__main__":
    main()
