#!/usr/bin/env python3
"""Corpus convergence analysis — measures per-element stability as documents are added.

Usage (inside Docker container):
    python tools/convergence_analysis.py --corpus-dir /path/to/txt/files --label stephen
    python tools/convergence_analysis.py --corpus-dir /path/to/txt/files --label stephen --seed 42
    python tools/convergence_analysis.py --corpus-dir /path/to/txt/files --label baseline --seed 42 --genre-analysis

Outputs:
    - JSON results: local_data/convergence_results/<label>_seed<N>_<timestamp>.json
    - Summary to stdout
"""
import argparse
import json
import os
import random
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from utils.voice_generator import generate_voice_profile
from utils.convergence_tracker import ElementTracker, ConvergenceComputer, ELEMENT_CATEGORIES


def parse_args():
    parser = argparse.ArgumentParser(description="Corpus convergence analysis")
    parser.add_argument("--corpus-dir", required=True, help="Directory of .txt files")
    parser.add_argument("--label", default="corpus", help="Label for output files")
    parser.add_argument("--seed", type=int, default=None, help="Shuffle seed (omit for no shuffle)")
    parser.add_argument("--min-words", type=int, default=500, help="Skip files under this word count")
    parser.add_argument("--genre-analysis", action="store_true", help="Group results by filename prefix (genre)")
    parser.add_argument("--output-dir", default=None, help="Output directory (default: local_data/convergence_results/)")
    return parser.parse_args()


def extract_genre(filename: str) -> str:
    """Extract genre prefix from filename (e.g., 'ap_top_...' -> 'ap_top')."""
    parts = filename.split("_")
    if len(parts) >= 2:
        prefix = parts[0]
        if prefix in ("ap",) and len(parts) > 1:
            return f"{parts[0]}_{parts[1]}"
        return prefix
    return "unknown"


def run_analysis(args):
    corpus_dir = Path(args.corpus_dir)
    txt_files = sorted(corpus_dir.glob("*.txt"))

    if not txt_files:
        print(f"No .txt files found in {corpus_dir}")
        sys.exit(1)

    if args.seed is not None:
        random.seed(args.seed)
        random.shuffle(txt_files)

    print(f"Found {len(txt_files)} files in {corpus_dir}")
    print(f"Label: {args.label}, Seed: {args.seed}, Min words: {args.min_words}")

    trackers = {}
    cumulative_words = 0
    convergence_curves = {}
    files_parsed = 0
    files_skipped = 0
    genre_elements = {}

    for i, fpath in enumerate(txt_files):
        text = fpath.read_text(encoding="utf-8", errors="replace")
        word_count = len(text.split())

        if word_count < args.min_words:
            files_skipped += 1
            continue

        try:
            result = generate_voice_profile(text)
        except Exception as e:
            print(f"  ERROR parsing {fpath.name}: {e}")
            files_skipped += 1
            continue

        cumulative_words += word_count
        files_parsed += 1

        if args.genre_analysis:
            genre = extract_genre(fpath.name)
            if genre not in genre_elements:
                genre_elements[genre] = {}

        for el_name, el_data in result.items():
            weight = el_data.get("weight", 0)

            if el_name not in trackers:
                trackers[el_name] = ElementTracker(el_name)
                convergence_curves[el_name] = []

            trackers[el_name].update(weight, cumulative_words)

            t = trackers[el_name]
            convergence_curves[el_name].append({
                "file_index": files_parsed,
                "cumulative_words": cumulative_words,
                "mean": t.mean,
                "rolling_delta": t.rolling_delta,
                "cv": t.cv,
                "converged": t.converged,
            })

            if args.genre_analysis:
                genre = extract_genre(fpath.name)
                if el_name not in genre_elements[genre]:
                    genre_elements[genre][el_name] = []
                genre_elements[genre][el_name].append(weight)

        if files_parsed % 10 == 0 or files_parsed == 1:
            cc = ConvergenceComputer()
            for t in trackers.values():
                cc.add_tracker(t)
            comp = cc.compute_completeness()
            print(f"  [{files_parsed}/{len(txt_files) - files_skipped}] "
                  f"{cumulative_words:,} words — {comp['pct']}% converged "
                  f"({comp['elements_converged']}/{comp['elements_total']})")

    cc = ConvergenceComputer()
    for t in trackers.values():
        cc.add_tracker(t)
    completeness = cc.compute_completeness()

    element_table = []
    for name, t in sorted(trackers.items()):
        element_table.append({
            "name": name,
            "category": ELEMENT_CATEGORIES.get(name, "unknown"),
            "converged": t.converged,
            "converged_at_words": t.converged_at_words,
            "final_mean": round(t.mean, 6),
            "final_cv": round(t.cv, 4),
            "final_rolling_delta": round(t.rolling_delta, 6),
            "near_zero": t.mean < 0.01,
        })

    category_summary = {}
    for el in element_table:
        cat = el["category"]
        if cat not in category_summary:
            category_summary[cat] = {"elements": 0, "converged": 0, "convergence_words": []}
        category_summary[cat]["elements"] += 1
        if el["converged"]:
            category_summary[cat]["converged"] += 1
            if el["converged_at_words"]:
                category_summary[cat]["convergence_words"].append(el["converged_at_words"])
    for cat, data in category_summary.items():
        words = data["convergence_words"]
        data["avg_convergence_words"] = round(sum(words) / len(words)) if words else None
        data["max_convergence_words"] = max(words) if words else None

    genre_variance = {}
    if args.genre_analysis and genre_elements:
        import statistics
        for el_name in trackers:
            genre_means = []
            for genre, elements in genre_elements.items():
                if el_name in elements and len(elements[el_name]) >= 3:
                    genre_means.append(statistics.mean(elements[el_name]))
            if len(genre_means) >= 2:
                genre_variance[el_name] = {
                    "stddev_across_genres": round(statistics.stdev(genre_means), 6),
                    "mean_across_genres": round(statistics.mean(genre_means), 6),
                    "cv_across_genres": round(
                        statistics.stdev(genre_means) / statistics.mean(genre_means), 4
                    ) if statistics.mean(genre_means) > 0.01 else 0,
                    "genre_count": len(genre_means),
                }

    tier_thresholds = {}
    for target_pct, tier_name in [(50, "bronze"), (75, "silver"), (90, "gold")]:
        max_steps = files_parsed
        for step in range(1, max_steps + 1):
            converged_at_step = 0
            total_at_step = 0
            for el_name, curve in convergence_curves.items():
                if step <= len(curve):
                    total_at_step += 1
                    if curve[step - 1]["converged"]:
                        converged_at_step += 1
            if total_at_step > 0:
                pct = converged_at_step / total_at_step * 100
                if pct >= target_pct:
                    tier_thresholds[tier_name] = {
                        "word_count": convergence_curves[list(convergence_curves.keys())[0]][step - 1]["cumulative_words"],
                        "file_count": step,
                        "pct_converged": round(pct, 1),
                    }
                    break

    results = {
        "label": args.label,
        "seed": args.seed,
        "timestamp": datetime.now().isoformat(),
        "files_total": len(txt_files),
        "files_parsed": files_parsed,
        "files_skipped": files_skipped,
        "total_words": cumulative_words,
        "completeness": completeness,
        "tier_thresholds": tier_thresholds,
        "element_table": element_table,
        "category_summary": category_summary,
        "genre_variance": genre_variance if genre_variance else None,
        "convergence_curves": convergence_curves,
    }

    output_dir = Path(args.output_dir) if args.output_dir else (
        Path(__file__).resolve().parent.parent.parent / "local_data" / "convergence_results"
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    seed_str = f"_seed{args.seed}" if args.seed is not None else "_noseed"
    output_file = output_dir / f"{args.label}{seed_str}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nResults saved to: {output_file}")

    print(f"\n{'='*60}")
    print(f"CONVERGENCE ANALYSIS: {args.label}")
    print(f"{'='*60}")
    print(f"Files parsed: {files_parsed} ({files_skipped} skipped)")
    print(f"Total words: {cumulative_words:,}")
    print(f"Completeness: {completeness['pct']}% — {completeness['tier_label'] or 'No tier'}")
    print(f"\nTier Thresholds:")
    for tier_name in ("bronze", "silver", "gold"):
        if tier_name in tier_thresholds:
            t = tier_thresholds[tier_name]
            print(f"  {tier_name.capitalize()}: {t['word_count']:,} words ({t['file_count']} files, {t['pct_converged']}%)")
        else:
            print(f"  {tier_name.capitalize()}: NOT REACHED")

    print(f"\nCategory Summary:")
    for cat, data in sorted(category_summary.items()):
        avg = f"{data['avg_convergence_words']:,}" if data['avg_convergence_words'] else "N/A"
        print(f"  {cat}: {data['converged']}/{data['elements']} converged (avg: {avg} words)")

    unconverged = [e for e in element_table if not e["converged"]]
    if unconverged:
        print(f"\nUnconverged elements ({len(unconverged)}):")
        for e in unconverged:
            print(f"  {e['name']} ({e['category']}): CV={e['final_cv']}, delta={e['final_rolling_delta']}")

    return results


if __name__ == "__main__":
    args = parse_args()
    run_analysis(args)
