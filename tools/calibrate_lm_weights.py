#!/usr/bin/env python3
"""Phase 3.8.1: LM Signal Weight Calibration.

Tests multiple weight configurations for the 8 LM signals to find optimal settings.
Runs entirely in-memory by monkey-patching HEURISTIC_WEIGHTS — no Docker rebuild needed.

Usage (inside Docker):
    python /tools/calibrate_lm_weights.py
"""
import json
import sys
import os
import copy
import random
from pathlib import Path

# Add backend to path
_backend_docker = "/app"
_backend_local = os.path.join(os.path.dirname(__file__), "..", "backend")
if os.path.isdir(os.path.join(_backend_docker, "utils")):
    sys.path.insert(0, _backend_docker)
else:
    sys.path.insert(0, _backend_local)

from utils.detector import detect_ai_patterns
from utils.heuristics import reference_data

# Corpus path
_docker_corpus = Path("/local_data/test_corpus/corpus.json")
_local_corpus = Path(__file__).parent.parent.parent / "local_data" / "test_corpus" / "corpus.json"
CORPUS_PATH = _docker_corpus if _docker_corpus.exists() else _local_corpus

LM_SIGNALS = [
    "compression_ratio_sentence", "compression_ratio_document",
    "repetition_density", "ngram_perplexity", "ngram_burstiness",
    "zipf_deviation_v2", "mattr_v2", "ttr_variance",
]

# Old signals that get skipped when LM is on
OLD_SIGNALS = ["compression_ratio", "zipf_deviation", "mattr"]


def load_corpus():
    with open(CORPUS_PATH) as f:
        data = json.load(f)
    return data["samples"]


def score_with_weights(samples, lm_weights, use_lm=True):
    """Score corpus with specific LM signal weights. Returns metrics dict."""
    # Monkey-patch weights
    original_weights = copy.deepcopy(reference_data.HEURISTIC_WEIGHTS)
    for signal, weight in lm_weights.items():
        reference_data.HEURISTIC_WEIGHTS[signal] = weight

    ai_scores = []
    human_scores = []

    for sample in samples:
        text = sample["text"]
        result = detect_ai_patterns(text, use_lm_signals=use_lm)
        score = result["overall_score"]

        if sample["label"] == "ai":
            ai_scores.append(score)
        elif sample["label"] == "human":
            human_scores.append(score)

    # Restore original weights
    reference_data.HEURISTIC_WEIGHTS.update(original_weights)

    ai_avg = sum(ai_scores) / len(ai_scores) if ai_scores else 0
    human_avg = sum(human_scores) / len(human_scores) if human_scores else 0
    separation = ai_avg - human_avg

    # Accuracy at multiple thresholds
    best_accuracy = 0
    best_threshold = 20
    best_f1 = 0
    for threshold in range(15, 55, 5):
        tp = sum(1 for s in ai_scores if s >= threshold)
        tn = sum(1 for s in human_scores if s < threshold)
        fp = sum(1 for s in human_scores if s >= threshold)
        fn = sum(1 for s in ai_scores if s < threshold)
        total = tp + tn + fp + fn
        accuracy = (tp + tn) / total if total > 0 else 0
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
        if accuracy > best_accuracy:
            best_accuracy = accuracy
            best_threshold = threshold
            best_f1 = f1

    return {
        "ai_avg": ai_avg,
        "human_avg": human_avg,
        "separation": separation,
        "best_accuracy": best_accuracy * 100,
        "best_threshold": best_threshold,
        "best_f1": best_f1 * 100,
        "fp_count": sum(1 for s in human_scores if s >= best_threshold),
        "fn_count": sum(1 for s in ai_scores if s < best_threshold),
    }


def print_result(name, metrics):
    print(f"  {name:40s}  AI={metrics['ai_avg']:5.1f}  HU={metrics['human_avg']:5.1f}  "
          f"Sep={metrics['separation']:+5.1f}  Acc={metrics['best_accuracy']:5.1f}%  "
          f"F1={metrics['best_f1']:5.1f}  @thr={metrics['best_threshold']:2d}  "
          f"FP={metrics['fp_count']}  FN={metrics['fn_count']}")


def main():
    print("Loading corpus...")
    samples = load_corpus()
    ai_count = sum(1 for s in samples if s["label"] == "ai")
    human_count = sum(1 for s in samples if s["label"] == "human")
    print(f"Loaded {len(samples)} samples ({ai_count} AI, {human_count} human)\n")

    # === Experiment 1: Baseline (no LM signals) ===
    print("=" * 120)
    print("EXPERIMENT 1: BASELINE (no LM signals)")
    print("=" * 120)
    baseline_weights = {s: 0.0 for s in LM_SIGNALS}
    baseline = score_with_weights(samples, baseline_weights, use_lm=False)
    print_result("Baseline (heuristics only)", baseline)
    print()

    # === Experiment 2: Current weights (from implementation) ===
    print("=" * 120)
    print("EXPERIMENT 2: CURRENT WEIGHTS (as shipped)")
    print("=" * 120)
    current_weights = {
        "compression_ratio_sentence": 0.7, "compression_ratio_document": 0.7,
        "repetition_density": 0.6, "ngram_perplexity": 0.8,
        "ngram_burstiness": 0.8, "zipf_deviation_v2": 0.6,
        "mattr_v2": 0.5, "ttr_variance": 0.5,
    }
    current = score_with_weights(samples, current_weights, use_lm=True)
    print_result("Current weights", current)
    print()

    # === Experiment 3: Minimal weights (all 0.1) ===
    print("=" * 120)
    print("EXPERIMENT 3: MINIMAL WEIGHTS (all 0.1)")
    print("=" * 120)
    minimal_weights = {s: 0.1 for s in LM_SIGNALS}
    minimal = score_with_weights(samples, minimal_weights, use_lm=True)
    print_result("All signals at 0.1", minimal)
    print()

    # === Experiment 4: High weights (all 1.0) ===
    print("=" * 120)
    print("EXPERIMENT 4: HIGH WEIGHTS (all 1.0)")
    print("=" * 120)
    high_weights = {s: 1.0 for s in LM_SIGNALS}
    high = score_with_weights(samples, high_weights, use_lm=True)
    print_result("All signals at 1.0", high)
    print()

    # === Experiment 5: Kill noise, keep promising ===
    print("=" * 120)
    print("EXPERIMENT 5: SELECTIVE (kill noise, keep promising)")
    print("=" * 120)
    configs = {
        "Kill doc_compress + zipf_v2": {
            "compression_ratio_sentence": 0.7, "compression_ratio_document": 0.0,
            "repetition_density": 0.6, "ngram_perplexity": 0.8,
            "ngram_burstiness": 0.8, "zipf_deviation_v2": 0.0,
            "mattr_v2": 0.5, "ttr_variance": 0.5,
        },
        "Kill all noise (doc_comp+zipf+burst)": {
            "compression_ratio_sentence": 0.7, "compression_ratio_document": 0.0,
            "repetition_density": 0.6, "ngram_perplexity": 0.8,
            "ngram_burstiness": 0.0, "zipf_deviation_v2": 0.0,
            "mattr_v2": 0.5, "ttr_variance": 0.5,
        },
        "Only corpus signals (B1+B2)": {
            "compression_ratio_sentence": 0.0, "compression_ratio_document": 0.0,
            "repetition_density": 0.0, "ngram_perplexity": 0.8,
            "ngram_burstiness": 0.8, "zipf_deviation_v2": 0.0,
            "mattr_v2": 0.0, "ttr_variance": 0.0,
        },
        "Only Category A (entropy)": {
            "compression_ratio_sentence": 0.7, "compression_ratio_document": 0.7,
            "repetition_density": 0.6, "ngram_perplexity": 0.0,
            "ngram_burstiness": 0.0, "zipf_deviation_v2": 0.0,
            "mattr_v2": 0.0, "ttr_variance": 0.0,
        },
        "Only Category C (stats)": {
            "compression_ratio_sentence": 0.0, "compression_ratio_document": 0.0,
            "repetition_density": 0.0, "ngram_perplexity": 0.0,
            "ngram_burstiness": 0.0, "zipf_deviation_v2": 0.6,
            "mattr_v2": 0.5, "ttr_variance": 0.5,
        },
        "Only mattr_v2 + ttr_variance": {
            "compression_ratio_sentence": 0.0, "compression_ratio_document": 0.0,
            "repetition_density": 0.0, "ngram_perplexity": 0.0,
            "ngram_burstiness": 0.0, "zipf_deviation_v2": 0.0,
            "mattr_v2": 0.5, "ttr_variance": 0.5,
        },
        "Kill everything except perplexity": {
            "compression_ratio_sentence": 0.0, "compression_ratio_document": 0.0,
            "repetition_density": 0.0, "ngram_perplexity": 0.8,
            "ngram_burstiness": 0.0, "zipf_deviation_v2": 0.0,
            "mattr_v2": 0.0, "ttr_variance": 0.0,
        },
        "Perplexity high + mattr low": {
            "compression_ratio_sentence": 0.0, "compression_ratio_document": 0.0,
            "repetition_density": 0.0, "ngram_perplexity": 1.0,
            "ngram_burstiness": 0.0, "zipf_deviation_v2": 0.0,
            "mattr_v2": 0.3, "ttr_variance": 0.3,
        },
    }
    for name, weights in configs.items():
        result = score_with_weights(samples, weights, use_lm=True)
        print_result(name, result)
    print()

    # === Experiment 6: Random search (500 iterations) ===
    print("=" * 120)
    print("EXPERIMENT 6: RANDOM SEARCH (500 iterations)")
    print("=" * 120)

    best_loss = float("inf")
    best_config = None
    best_metrics = None

    for i in range(500):
        # Random weights 0.0-1.0 for each signal, but bias toward killing noise
        weights = {}
        for signal in LM_SIGNALS:
            # 30% chance of weight=0 (kill), rest uniform 0.1-1.0
            if random.random() < 0.3:
                weights[signal] = 0.0
            else:
                weights[signal] = round(random.uniform(0.1, 1.0), 2)

        metrics = score_with_weights(samples, weights, use_lm=True)

        # Loss: minimize human avg, maximize AI avg, maximize separation
        # Penalize if worse than baseline
        loss = (
            metrics["human_avg"] * 2        # heavily penalize high human scores
            - metrics["ai_avg"] * 1          # reward high AI scores
            - metrics["separation"] * 1.5    # reward separation
            + metrics["fp_count"] * 5        # penalize false positives
            + max(0, baseline["best_accuracy"] - metrics["best_accuracy"]) * 3  # penalize accuracy drop
        )

        if loss < best_loss:
            best_loss = loss
            best_config = weights.copy()
            best_metrics = metrics.copy()
            if (i + 1) % 50 == 0 or i < 5:
                print(f"  [iter {i+1:3d}] loss={loss:.1f}", end="  ")
                print_result(f"best so far", best_metrics)

    print()
    print("BEST RANDOM SEARCH RESULT:")
    print_result("Best config", best_metrics)
    print(f"  Weights: {json.dumps(best_config, indent=2)}")
    print()

    # === Summary ===
    print("=" * 120)
    print("SUMMARY COMPARISON")
    print("=" * 120)
    print_result("Baseline (no LM)", baseline)
    print_result("Current weights", current)
    print_result("Minimal (0.1)", minimal)
    print_result("High (1.0)", high)
    for name, weights in configs.items():
        result = score_with_weights(samples, weights, use_lm=True)
        print_result(name, result)
    print_result("Best random search", best_metrics)
    print()

    # Delta from baseline
    print("DELTA FROM BASELINE:")
    print(f"  Best random: Acc {best_metrics['best_accuracy'] - baseline['best_accuracy']:+.1f}%  "
          f"Sep {best_metrics['separation'] - baseline['separation']:+.1f}  "
          f"HuAvg {best_metrics['human_avg'] - baseline['human_avg']:+.1f}  "
          f"AIAvg {best_metrics['ai_avg'] - baseline['ai_avg']:+.1f}")


if __name__ == "__main__":
    main()
