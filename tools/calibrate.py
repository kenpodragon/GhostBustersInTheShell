#!/usr/bin/env python3
"""Phase 2.4: Score Calibration & Weight Optimization.

Runs heuristic detection against a labeled test corpus and optimizes weights
to maximize separation between AI and human text scores.

Usage (from code/ directory):
    # Run inside Docker container:
    docker compose exec app python tools/calibrate.py

    # Or with specific commands:
    docker compose exec app python tools/calibrate.py score      # Score corpus + report
    docker compose exec app python tools/calibrate.py optimize   # Grid search weights
    docker compose exec app python tools/calibrate.py compare    # A/B: heuristic vs current
    docker compose exec app python tools/calibrate.py regression # Regression test suite
"""
import json
import sys
import os
import csv
import math
import copy
import itertools
from pathlib import Path
from datetime import datetime

# Add backend to path so we can import utils
# In Docker, backend is at /app; locally, it's relative to this script
_backend_docker = "/app"
_backend_local = os.path.join(os.path.dirname(__file__), "..", "backend")
if os.path.isdir(os.path.join(_backend_docker, "utils")):
    sys.path.insert(0, _backend_docker)
else:
    sys.path.insert(0, _backend_local)

from utils.detector import detect_ai_patterns
from utils.heuristics.scoring import combine_signals, estimate_confidence, detect_genre
from utils.heuristics.reference_data import HEURISTIC_WEIGHTS, GENRE_BASELINES

# Paths
# Support both Docker (/local_data/) and local dev paths
_docker_corpus = Path("/local_data/test_corpus/corpus.json")
_local_corpus = Path(__file__).parent.parent.parent / "local_data" / "test_corpus" / "corpus.json"
CORPUS_PATH = _docker_corpus if _docker_corpus.exists() else _local_corpus

_docker_results = Path("/local_data/test_corpus/results")
_local_results = Path(__file__).parent.parent.parent / "local_data" / "test_corpus" / "results"
RESULTS_DIR = _docker_results if _docker_corpus.exists() else _local_results


def load_corpus() -> list[dict]:
    """Load test corpus from JSON."""
    with open(CORPUS_PATH) as f:
        data = json.load(f)
    return data["samples"]


def score_corpus(samples: list[dict], use_lm_signals: bool = False) -> list[dict]:
    """Run detector on every sample, return enriched results."""
    results = []
    for sample in samples:
        text = sample["text"]
        detection = detect_ai_patterns(text, use_lm_signals=use_lm_signals)

        # Extract document-level signals by re-running the internal function
        # We need the raw signals for per-heuristic analysis
        from utils.detector import _document_level_patterns, _split_sentences
        sentences = _split_sentences(text)
        _, doc_signals = _document_level_patterns(text, sentences, use_lm_signals=use_lm_signals)

        results.append({
            "id": sample["id"],
            "label": sample["label"],
            "genre": sample["genre"],
            "source": sample.get("source", "unknown"),
            "word_count": len(text.split()),
            "detected_genre": detection["genre"],
            "overall_score": detection["overall_score"],
            "signal_count": detection["signal_count"],
            "confidence": detection["confidence"],
            "doc_signals": doc_signals,
            "pattern_names": [p["pattern"] for p in detection["detected_patterns"]],
        })

    return results


def print_score_report(results: list[dict]):
    """Print detailed scoring report."""
    ai_results = [r for r in results if r["label"] == "ai"]
    human_results = [r for r in results if r["label"] == "human"]

    ai_scores = [r["overall_score"] for r in ai_results]
    human_scores = [r["overall_score"] for r in human_results]

    print("=" * 78)
    print("CALIBRATION SCORE REPORT")
    print("=" * 78)
    print(f"Corpus: {len(results)} samples ({len(ai_results)} AI, {len(human_results)} human)")
    print()

    # Summary stats
    print("OVERALL SCORES")
    print("-" * 50)
    print(f"  AI texts:    min={min(ai_scores):.1f}  avg={sum(ai_scores)/len(ai_scores):.1f}  "
          f"max={max(ai_scores):.1f}  median={sorted(ai_scores)[len(ai_scores)//2]:.1f}")
    print(f"  Human texts: min={min(human_scores):.1f}  avg={sum(human_scores)/len(human_scores):.1f}  "
          f"max={max(human_scores):.1f}  median={sorted(human_scores)[len(human_scores)//2]:.1f}")
    print()

    # Separation metric
    ai_avg = sum(ai_scores) / len(ai_scores)
    human_avg = sum(human_scores) / len(human_scores)
    separation = ai_avg - human_avg
    print(f"  SEPARATION (AI avg - Human avg): {separation:.1f}")
    print()

    # Classification accuracy at various thresholds
    print("CLASSIFICATION ACCURACY (at threshold)")
    print("-" * 50)
    for threshold in [20, 25, 30, 35, 40, 45, 50]:
        ai_correct = sum(1 for s in ai_scores if s >= threshold)
        human_correct = sum(1 for s in human_scores if s < threshold)
        total_correct = ai_correct + human_correct
        accuracy = total_correct / len(results) * 100
        precision = ai_correct / max(1, ai_correct + (len(human_results) - human_correct)) * 100
        recall = ai_correct / len(ai_results) * 100
        f1 = 2 * precision * recall / max(1, precision + recall)
        print(f"  threshold={threshold:3d}:  accuracy={accuracy:5.1f}%  "
              f"precision={precision:5.1f}%  recall={recall:5.1f}%  F1={f1:5.1f}")
    print()

    # Per-genre breakdown
    print("PER-GENRE BREAKDOWN")
    print("-" * 50)
    genres = sorted(set(r["genre"] for r in results))
    for genre in genres:
        genre_ai = [r["overall_score"] for r in ai_results if r["genre"] == genre]
        genre_human = [r["overall_score"] for r in human_results if r["genre"] == genre]
        if genre_ai:
            ai_str = f"AI: avg={sum(genre_ai)/len(genre_ai):.1f} ({len(genre_ai)} samples)"
        else:
            ai_str = "AI: (none)"
        if genre_human:
            human_str = f"Human: avg={sum(genre_human)/len(genre_human):.1f} ({len(genre_human)} samples)"
        else:
            human_str = "Human: (none)"
        print(f"  {genre:15s}  {ai_str:40s}  {human_str}")
    print()

    # Per-sample detail
    print("INDIVIDUAL SCORES (sorted by score)")
    print("-" * 78)
    for r in sorted(results, key=lambda x: x["overall_score"], reverse=True):
        marker = "AI" if r["label"] == "ai" else "HU"
        correct = (r["label"] == "ai" and r["overall_score"] >= 35) or \
                  (r["label"] == "human" and r["overall_score"] < 35)
        status = "OK" if correct else "XX"
        print(f"  [{marker}] {status} {r['overall_score']:5.1f}  signals={r['signal_count']:2d}  "
              f"genre={r['genre']:12s}  detected={r['detected_genre']:10s}  {r['id']}")
    print()

    # Per-heuristic analysis
    print_heuristic_analysis(results)

    # Misclassifications
    print("MISCLASSIFICATIONS (at threshold=35)")
    print("-" * 50)
    false_negatives = [r for r in ai_results if r["overall_score"] < 35]
    false_positives = [r for r in human_results if r["overall_score"] >= 35]
    if false_negatives:
        print(f"  False negatives (AI scored < 35): {len(false_negatives)}")
        for r in false_negatives:
            print(f"    {r['id']}: score={r['overall_score']:.1f}, signals={r['signal_count']}, "
                  f"patterns={r['pattern_names'][:5]}")
    else:
        print("  False negatives: NONE")
    if false_positives:
        print(f"  False positives (Human scored >= 35): {len(false_positives)}")
        for r in false_positives:
            print(f"    {r['id']}: score={r['overall_score']:.1f}, signals={r['signal_count']}, "
                  f"patterns={r['pattern_names'][:5]}")
    else:
        print("  False positives: NONE")


def print_heuristic_analysis(results: list[dict]):
    """Analyze per-heuristic discrimination power."""
    print("PER-HEURISTIC DISCRIMINATION")
    print("-" * 78)

    ai_results = [r for r in results if r["label"] == "ai"]
    human_results = [r for r in results if r["label"] == "human"]

    # Collect all signal names
    all_signals = set()
    for r in results:
        all_signals.update(r["doc_signals"].keys())

    heuristic_stats = []
    for signal in sorted(all_signals):
        ai_scores = [r["doc_signals"].get(signal, 0) for r in ai_results]
        human_scores = [r["doc_signals"].get(signal, 0) for r in human_results]

        ai_avg = sum(ai_scores) / len(ai_scores) if ai_scores else 0
        human_avg = sum(human_scores) / len(human_scores) if human_scores else 0
        ai_fire_rate = sum(1 for s in ai_scores if s > 0) / len(ai_scores) * 100 if ai_scores else 0
        human_fire_rate = sum(1 for s in human_scores if s > 0) / len(human_scores) * 100 if human_scores else 0

        discrimination = ai_avg - human_avg
        fire_diff = ai_fire_rate - human_fire_rate
        current_weight = HEURISTIC_WEIGHTS.get(signal, 0.5)

        heuristic_stats.append({
            "signal": signal,
            "ai_avg": ai_avg,
            "human_avg": human_avg,
            "discrimination": discrimination,
            "ai_fire": ai_fire_rate,
            "human_fire": human_fire_rate,
            "fire_diff": fire_diff,
            "weight": current_weight,
        })

    # Sort by discrimination power
    heuristic_stats.sort(key=lambda x: x["discrimination"], reverse=True)

    print(f"  {'Signal':30s}  {'AI avg':>7s}  {'Hum avg':>7s}  {'Discrim':>7s}  "
          f"{'AI fire%':>8s}  {'Hum fire%':>9s}  {'Weight':>6s}")
    print(f"  {'':30s}  {'':>7s}  {'':>7s}  {'':>7s}  {'':>8s}  {'':>9s}  {'':>6s}")
    for h in heuristic_stats:
        quality = "***" if h["discrimination"] > 20 else "**" if h["discrimination"] > 10 else "*" if h["discrimination"] > 5 else ""
        print(f"  {h['signal']:30s}  {h['ai_avg']:7.1f}  {h['human_avg']:7.1f}  "
              f"{h['discrimination']:+7.1f}  {h['ai_fire']:7.1f}%  {h['human_fire']:8.1f}%  "
              f"{h['weight']:5.2f}  {quality}")
    print()


def optimize_weights(results: list[dict], iterations: int = 5000) -> dict:
    """Grid search / random search to optimize heuristic weights.

    Maximizes: AI avg score - Human avg score, with penalties for:
    - Human scores above threshold (false positives)
    - AI scores below threshold (false negatives)
    """
    import random
    random.seed(42)

    ai_results = [r for r in results if r["label"] == "ai"]
    human_results = [r for r in results if r["label"] == "human"]

    # Get all signal names that appear in corpus
    all_signals = set()
    for r in results:
        all_signals.update(r["doc_signals"].keys())

    # Current weights as baseline
    best_weights = dict(HEURISTIC_WEIGHTS)
    best_score = _evaluate_weights(best_weights, ai_results, human_results)

    print(f"Baseline objective: {best_score:.2f}")
    print(f"Optimizing {len(all_signals)} heuristic weights over {iterations} iterations...")
    print()

    for i in range(iterations):
        # Random perturbation of current best weights
        candidate = dict(best_weights)

        # Mutate 1-5 random weights
        num_mutations = random.randint(1, 5)
        signals_to_mutate = random.sample(list(all_signals), min(num_mutations, len(all_signals)))

        for signal in signals_to_mutate:
            current = candidate.get(signal, 0.5)
            # Random perturbation within [0.1, 1.0]
            delta = random.gauss(0, 0.15)
            candidate[signal] = max(0.1, min(1.0, current + delta))

        score = _evaluate_weights(candidate, ai_results, human_results)

        if score > best_score:
            best_weights = candidate
            best_score = score
            if i % 100 == 0 or score > best_score - 0.01:
                print(f"  iter {i:5d}: new best objective = {best_score:.2f}")

    print()
    print(f"Final objective: {best_score:.2f}")
    return best_weights


def _evaluate_weights(weights: dict, ai_results: list, human_results: list) -> float:
    """Evaluate a weight configuration. Higher is better.

    Objective = separation + accuracy_bonus - false_positive_penalty - false_negative_penalty
    """
    threshold = 35

    # Re-score all samples with candidate weights
    ai_scores = []
    for r in ai_results:
        score = _rescore_with_weights(r, weights)
        ai_scores.append(score)

    human_scores = []
    for r in human_results:
        score = _rescore_with_weights(r, weights)
        human_scores.append(score)

    ai_avg = sum(ai_scores) / len(ai_scores) if ai_scores else 0
    human_avg = sum(human_scores) / len(human_scores) if human_scores else 0

    # Primary objective: maximize separation
    separation = ai_avg - human_avg

    # Accuracy bonus
    ai_correct = sum(1 for s in ai_scores if s >= threshold)
    human_correct = sum(1 for s in human_scores if s < threshold)
    accuracy = (ai_correct + human_correct) / (len(ai_scores) + len(human_scores))
    accuracy_bonus = accuracy * 20

    # Penalty for false positives (human text scored as AI) — heavy penalty
    false_positives = sum(max(0, s - threshold) for s in human_scores)
    fp_penalty = false_positives * 2

    # Penalty for false negatives (AI text scored below threshold)
    false_negatives = sum(max(0, threshold - s) for s in ai_scores)
    fn_penalty = false_negatives * 0.5

    # Penalty for human scores being too high in general
    human_high_penalty = sum(max(0, s - 20) for s in human_scores) * 0.5

    return separation + accuracy_bonus - fp_penalty - fn_penalty - human_high_penalty


def _rescore_with_weights(result: dict, weights: dict) -> float:
    """Re-compute the document-level combined score with different weights.

    Note: This only re-weights the document-level signals (40% of final score).
    Sentence-level scoring is not re-weighted here (would need full re-analysis).
    For calibration purposes, we focus on document-level signal weights.
    """
    signals = result["doc_signals"]
    active = {k: v for k, v in signals.items() if v > 0}
    if not active:
        return 0

    weighted_sum = 0
    weight_total = 0
    for name, score in active.items():
        w = weights.get(name, 0.5)
        weighted_sum += score * w
        weight_total += w

    if weight_total == 0:
        return 0

    base_score = weighted_sum / weight_total

    count_bonus = min(20, (len(active) - 1) * 4)

    high_conf_signals = [s for n, s in active.items()
                         if weights.get(n, 0) >= 0.7]
    if len(high_conf_signals) >= 3:
        avg_high = sum(high_conf_signals) / len(high_conf_signals)
        if avg_high > 30:
            count_bonus += 5

    doc_combined = min(100, base_score + count_bonus)

    # Approximate the 60/40 blend using original overall as proxy for sentence component
    # We use the original overall score to back-calculate the sentence component
    original_overall = result["overall_score"]
    original_doc = combine_signals(signals)
    if original_doc > 0:
        # original_overall = sentence * 0.6 + original_doc * 0.4
        # sentence = (original_overall - original_doc * 0.4) / 0.6
        sentence_component = (original_overall - original_doc * 0.4) / 0.6
        sentence_component = max(0, min(100, sentence_component))
    else:
        sentence_component = original_overall

    return min(100, sentence_component * 0.6 + doc_combined * 0.4)


def print_weight_comparison(original: dict, optimized: dict):
    """Show weight changes."""
    print("WEIGHT CHANGES")
    print("=" * 60)
    print(f"  {'Signal':30s}  {'Original':>8s}  {'Optimized':>9s}  {'Change':>8s}")
    print(f"  {'-'*30}  {'-'*8}  {'-'*9}  {'-'*8}")

    all_keys = sorted(set(list(original.keys()) + list(optimized.keys())))
    for key in all_keys:
        orig = original.get(key, 0.5)
        opt = optimized.get(key, 0.5)
        change = opt - orig
        marker = " **" if abs(change) > 0.1 else ""
        print(f"  {key:30s}  {orig:8.3f}  {opt:9.3f}  {change:+8.3f}{marker}")
    print()


def generate_updated_reference_data(optimized_weights: dict) -> str:
    """Generate updated HEURISTIC_WEIGHTS for reference_data.py."""
    lines = ["HEURISTIC_WEIGHTS = {"]
    items = sorted(optimized_weights.items())

    # Group by category for readability
    for key, val in items:
        lines.append(f'    "{key}": {val:.2f},')
    lines.append("}")
    return "\n".join(lines)


def run_regression_test(results: list[dict]):
    """Run regression tests against calibration targets."""
    print("REGRESSION TEST SUITE")
    print("=" * 60)

    ai_results = [r for r in results if r["label"] == "ai"]
    human_results = [r for r in results if r["label"] == "human"]

    ai_scores = [r["overall_score"] for r in ai_results]
    human_scores = [r["overall_score"] for r in human_results]

    ai_avg = sum(ai_scores) / len(ai_scores)
    human_avg = sum(human_scores) / len(human_scores)

    tests = [
        # Core targets (must pass)
        ("AI average score > 35", ai_avg > 35),
        ("Human average score < 25", human_avg < 25),
        ("Separation (AI - Human) > 15", (ai_avg - human_avg) > 15),
        ("No human text scores > 50", all(s < 50 for s in human_scores)),
        ("All AI texts score > 15", all(s > 15 for s in ai_scores)),
        ("70%+ AI texts score > 30", sum(1 for s in ai_scores if s > 30) / len(ai_scores) > 0.7),
        ("90%+ human texts score < 30", sum(1 for s in human_scores if s < 30) / len(human_scores) > 0.9),
    ]

    # Stretch targets (informational, don't affect pass/fail)
    stretch = [
        ("AI average score > 45", ai_avg > 45),
        ("Human average score < 18", human_avg < 18),
        ("Separation > 25", (ai_avg - human_avg) > 25),
        ("85%+ AI texts score > 35", sum(1 for s in ai_scores if s > 35) / len(ai_scores) > 0.85),
    ]

    passed = 0
    for name, result in tests:
        status = "PASS" if result else "FAIL"
        symbol = "+" if result else "X"
        print(f"  [{symbol}] {status}: {name}")
        if result:
            passed += 1

    print()
    print(f"  {passed}/{len(tests)} core tests passed")

    print()
    print("STRETCH TARGETS (informational)")
    print("-" * 50)
    for name, result in stretch:
        status = "HIT" if result else "MISS"
        symbol = "+" if result else "-"
        print(f"  [{symbol}] {status}: {name}")

    # Per-genre regression
    print()
    print("PER-GENRE REGRESSION")
    print("-" * 50)
    genres = sorted(set(r["genre"] for r in results))
    for genre in genres:
        genre_ai = [r["overall_score"] for r in ai_results if r["genre"] == genre]
        genre_human = [r["overall_score"] for r in human_results if r["genre"] == genre]
        baseline = GENRE_BASELINES.get(genre, GENRE_BASELINES.get("general"))

        if genre_ai:
            ai_avg_g = sum(genre_ai) / len(genre_ai)
            meets_floor = ai_avg_g >= baseline["ai_floor"]
            print(f"  {genre:15s} AI avg={ai_avg_g:5.1f}  floor={baseline['ai_floor']}  "
                  f"{'PASS' if meets_floor else 'FAIL'}")

        if genre_human:
            human_avg_g = sum(genre_human) / len(genre_human)
            meets_ceil = human_avg_g <= baseline["human_ceil"]
            print(f"  {genre:15s} HU avg={human_avg_g:5.1f}  ceil={baseline['human_ceil']}  "
                  f"{'PASS' if meets_ceil else 'FAIL'}")

    return passed == len(tests)


def save_results(results: list[dict], optimized_weights: dict = None):
    """Save results to disk for analysis."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Save raw results
    results_file = RESULTS_DIR / f"calibration_{timestamp}.json"
    with open(results_file, "w") as f:
        json.dump({
            "timestamp": timestamp,
            "sample_count": len(results),
            "results": results,
            "optimized_weights": optimized_weights,
        }, f, indent=2, default=str)
    print(f"Results saved to: {results_file}")

    # Save CSV for spreadsheet analysis
    csv_file = RESULTS_DIR / f"scores_{timestamp}.csv"
    with open(csv_file, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "label", "genre", "detected_genre", "overall_score",
                         "signal_count", "word_count", "conf_low", "conf_high"])
        for r in results:
            writer.writerow([
                r["id"], r["label"], r["genre"], r["detected_genre"],
                r["overall_score"], r["signal_count"], r["word_count"],
                r["confidence"][0], r["confidence"][1],
            ])
    print(f"CSV saved to: {csv_file}")


def main():
    command = sys.argv[1] if len(sys.argv) > 1 else "score"
    use_lm_signals = "--use-lm-signals" in sys.argv

    print(f"Loading corpus from {CORPUS_PATH}...")
    samples = load_corpus()
    print(f"Loaded {len(samples)} samples")
    if use_lm_signals:
        print("  LM signals: ENABLED")
    print()

    print("Scoring all samples...")
    results = score_corpus(samples, use_lm_signals=use_lm_signals)
    print(f"Scored {len(results)} samples")
    print()

    if command == "score":
        print_score_report(results)
        save_results(results)

    elif command == "optimize":
        print_score_report(results)
        print()
        print("=" * 78)
        print("STARTING WEIGHT OPTIMIZATION")
        print("=" * 78)
        print()

        optimized = optimize_weights(results, iterations=5000)
        print_weight_comparison(HEURISTIC_WEIGHTS, optimized)

        # Re-score with optimized weights and show improvement
        print("RE-SCORING WITH OPTIMIZED WEIGHTS")
        print("=" * 60)
        for r in results:
            r["optimized_score"] = _rescore_with_weights(r, optimized)

        ai_orig = [r["overall_score"] for r in results if r["label"] == "ai"]
        ai_opt = [r["optimized_score"] for r in results if r["label"] == "ai"]
        human_orig = [r["overall_score"] for r in results if r["label"] == "human"]
        human_opt = [r["optimized_score"] for r in results if r["label"] == "human"]

        print(f"  AI avg:    {sum(ai_orig)/len(ai_orig):.1f} -> {sum(ai_opt)/len(ai_opt):.1f}")
        print(f"  Human avg: {sum(human_orig)/len(human_orig):.1f} -> {sum(human_opt)/len(human_opt):.1f}")
        print(f"  Separation: {sum(ai_orig)/len(ai_orig) - sum(human_orig)/len(human_orig):.1f} -> "
              f"{sum(ai_opt)/len(ai_opt) - sum(human_opt)/len(human_opt):.1f}")
        print()

        # Generate code
        print("GENERATED CODE (for reference_data.py)")
        print("-" * 50)
        print(generate_updated_reference_data(optimized))
        print()

        save_results(results, optimized)

    elif command == "compare":
        # A/B comparison: show current vs hypothetical scoring
        print_score_report(results)

    elif command == "regression":
        all_passed = run_regression_test(results)
        save_results(results)
        sys.exit(0 if all_passed else 1)

    else:
        print(f"Unknown command: {command}")
        print("Usage: calibrate.py [score|optimize|compare|regression]")
        sys.exit(1)


if __name__ == "__main__":
    main()
