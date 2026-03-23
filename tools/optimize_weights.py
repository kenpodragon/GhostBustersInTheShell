#!/usr/bin/env python3
"""Goal-based weight optimizer for AI detection heuristics.

Uses multiple optimization agents to find weight combinations that push:
- Human scores < 10
- AI scores > 80

Agents:
1. Genetic Algorithm — evolves populations of weight vectors
2. Simulated Annealing — explores neighborhood of current best
3. Gradient-Free Hill Climbing — greedy local search with restarts

Each agent optimizes the same loss function independently, then we compare.
"""
import json
import sys
import os
import math
import random
import copy
from collections import defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from utils.detector import (
    _split_sentences, _score_sentence, _split_paragraphs, _score_paragraph,
    _document_level_patterns,
)
from utils.heuristics.scoring import composite_score, detect_genre, combine_signals
from utils.heuristics.reference_data import HEURISTIC_WEIGHTS, GENRE_BASELINES


# ── Data Loading ──────────────────────────────────────────────────────

def load_corpus(path="/local_data/test_corpus/corpus.json"):
    with open(path) as f:
        corpus = json.load(f)
    return corpus["samples"]


def extract_signals(samples):
    """Run detection on all samples, capture raw per-heuristic signals.

    Returns list of dicts: {id, label, genre, sentence_score, paragraph_score,
    document_signals: {name: raw_score}, sentence_signals: {name: count},
    paragraph_signals: {name: score}, all_patterns: [...]}
    """
    results = []
    for s in samples:
        text = s["text"]
        label = s["label"]
        sid = s.get("id", "unknown")

        sentences = _split_sentences(text)
        if not sentences:
            results.append({
                "id": sid, "label": label, "genre": "general",
                "sentence_score": 0, "paragraph_score": 0,
                "document_signals": {}, "sentence_signals": {},
                "paragraph_signals": {}, "all_patterns": [],
                "sentence_signal_count": 0, "paragraph_signal_count": 0,
                "document_signal_count": 0,
            })
            continue

        # Sentence-level
        all_patterns = []
        sentence_results = []
        for i, sent in enumerate(sentences):
            score, patterns = _score_sentence(sent, sentences)
            sentence_results.append({"score": score, "patterns": patterns})
            all_patterns.extend(patterns)

        scores = [sr["score"] for sr in sentence_results]
        if scores:
            nonzero = [s for s in scores if s > 0]
            if nonzero:
                sentence_overall = sum(nonzero) / len(nonzero)
                weight_factor = len(nonzero) / len(scores)
                sentence_overall *= max(0.5, weight_factor)
            else:
                sentence_overall = 0
        else:
            sentence_overall = 0

        # Sentence signal counts
        sent_signal_counts = {}
        for sr in sentence_results:
            for p in sr["patterns"]:
                name = p["pattern"]
                sent_signal_counts[name] = sent_signal_counts.get(name, 0) + 1

        # Paragraph-level
        paragraphs = _split_paragraphs(text)
        para_signals_all = {}
        para_scores = []
        for i, para in enumerate(paragraphs):
            para_score, para_patterns, para_signals = _score_paragraph(para, i, len(paragraphs))
            para_scores.append(para_score)
            all_patterns.extend(para_patterns)
            para_signals_all.update(para_signals)

        paragraph_overall = sum(para_scores) / len(para_scores) if para_scores else 0

        # Document-level
        doc_patterns, doc_signals = _document_level_patterns(text, sentences)
        all_patterns.extend(doc_patterns)

        genre = detect_genre(text)

        sentence_signal_count = len(set(
            p["pattern"] for sr in sentence_results for p in sr["patterns"]
        ))
        paragraph_signal_count = len(para_signals_all)
        document_signal_count = len(doc_signals)

        results.append({
            "id": sid, "label": label, "genre": genre,
            "sentence_score": sentence_overall,
            "paragraph_score": paragraph_overall,
            "document_signals": dict(doc_signals),
            "sentence_signals": sent_signal_counts,
            "paragraph_signals": dict(para_signals_all),
            "all_patterns": all_patterns,
            "sentence_signal_count": sentence_signal_count,
            "paragraph_signal_count": paragraph_signal_count,
            "document_signal_count": document_signal_count,
        })

    return results


# ── Scoring with custom weights ───────────────────────────────────────

def score_with_weights(sample, weights, tier_weights=(0.45, 0.30, 0.25),
                       count_bonus_factor=3, count_bonus_max=15,
                       convergence_max=10, density_max=10):
    """Recompute a sample's overall score using custom heuristic weights.

    This replaces combine_signals + composite_score with parameterized versions.
    """
    # Recompute document-level combined score with custom weights
    doc_signals = sample["document_signals"]
    active = {k: v for k, v in doc_signals.items()
              if v > 0 and weights.get(k, 0.5) > 0}

    if active:
        weighted_sum = sum(v * weights.get(k, 0.5) for k, v in active.items())
        weight_total = sum(weights.get(k, 0.5) for k in active)
        doc_base = weighted_sum / weight_total if weight_total > 0 else 0

        meaningful = [k for k in active if weights.get(k, 0) >= 0.3]
        count_bonus = min(count_bonus_max, max(0, len(meaningful) - 2) * count_bonus_factor)

        high_conf = [v for k, v in active.items() if weights.get(k, 0) >= 0.7]
        if len(high_conf) >= 3 and sum(high_conf) / len(high_conf) > 30:
            count_bonus += 5

        doc_combined = min(100, doc_base + count_bonus)
    else:
        doc_combined = 0

    # Sentence and paragraph scores are harder to recompute without re-running
    # all checks, so we use the pre-computed values. The main tuning lever is
    # document-level weights + tier weights + bonus params.
    sent_score = sample["sentence_score"]
    para_score = sample["paragraph_score"]

    # Composite with custom tier weights
    tw_sent, tw_para, tw_doc = tier_weights
    weighted = sent_score * tw_sent + para_score * tw_para + doc_combined * tw_doc

    # Convergence bonus
    scores_list = [sent_score, para_score, doc_combined]
    non_zero = [s for s in scores_list if s > 0]
    if len(non_zero) >= 2:
        mean = sum(non_zero) / len(non_zero)
        variance = sum((s - mean) ** 2 for s in non_zero) / len(non_zero)
        convergence_bonus = min(convergence_max, (100 - variance) / 10) if variance < 100 else 0
    else:
        convergence_bonus = 0

    # Density bonus
    total_sigs = (sample["sentence_signal_count"] +
                  sample["paragraph_signal_count"] +
                  sample["document_signal_count"])
    tiers_with = sum(1 for s in [sample["sentence_signal_count"],
                                  sample["paragraph_signal_count"],
                                  sample["document_signal_count"]] if s > 0)
    density_bonus = 0
    if tiers_with >= 3 and total_sigs >= 8:
        density_bonus = min(density_max, (total_sigs - 8) * 2)
    elif tiers_with >= 2 and total_sigs >= 5:
        density_bonus = min(density_max // 2, total_sigs - 5)

    overall = min(100, weighted + convergence_bonus + density_bonus)

    # Genre dampening
    genre = sample["genre"]
    genre_baseline = GENRE_BASELINES.get(genre, GENRE_BASELINES["general"])
    human_ceil = genre_baseline["human_ceil"]
    if human_ceil > 25 and overall < human_ceil + 10:
        dampening = (human_ceil - 25) / 25
        dampened = overall * (1 - dampening * 0.3)
        overall = max(dampened, overall * 0.7)

    return round(overall, 1)


# ── Loss Function ─────────────────────────────────────────────────────

def compute_loss(samples, weights, tier_weights=(0.45, 0.30, 0.25),
                 count_bonus_factor=3, count_bonus_max=15,
                 convergence_max=10, density_max=10):
    """Loss function: penalize human scores > 10 and AI scores < 80.

    Loss = sum of penalties:
    - For each human sample: max(0, score - 10)^2
    - For each AI sample: max(0, 80 - score)^2
    - Small penalty for Ghost Touched misclassification

    Lower is better. Zero means all targets met.
    """
    total_loss = 0
    human_scores = []
    ai_scores = []

    for s in samples:
        score = score_with_weights(s, weights, tier_weights,
                                   count_bonus_factor, count_bonus_max,
                                   convergence_max, density_max)
        label = s["label"]

        if label == "human":
            human_scores.append(score)
            if score > 10:
                total_loss += (score - 10) ** 2
        elif label == "ai":
            ai_scores.append(score)
            if score < 80:
                total_loss += (80 - score) ** 2
        # mixed/ai_humanized/ai_polished/ai_paraphrased — smaller penalty
        elif label in ("mixed", "ai_polished", "ai_paraphrased"):
            if score < 30:
                total_loss += (30 - score) ** 1.5
        elif label == "ai_humanized":
            pass  # no penalty — humanized text is designed to evade

    return total_loss, human_scores, ai_scores


def report(label, weights, tier_weights, samples, extra_params=None):
    """Print a report for a weight configuration."""
    params = extra_params or {}
    loss, human_scores, ai_scores = compute_loss(
        samples, weights, tier_weights,
        params.get("count_bonus_factor", 3),
        params.get("count_bonus_max", 15),
        params.get("convergence_max", 10),
        params.get("density_max", 10),
    )
    h_avg = sum(human_scores) / len(human_scores) if human_scores else 0
    a_avg = sum(ai_scores) / len(ai_scores) if ai_scores else 0
    h_max = max(human_scores) if human_scores else 0
    a_min = min(ai_scores) if ai_scores else 0
    h_under_10 = sum(1 for s in human_scores if s <= 10)
    a_over_80 = sum(1 for s in ai_scores if s >= 80)
    separation = a_avg - h_avg

    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"{'='*60}")
    print(f"  Loss: {loss:.1f}")
    print(f"  Human: avg={h_avg:.1f}, max={h_max:.1f}, ≤10: {h_under_10}/{len(human_scores)}")
    print(f"  AI:    avg={a_avg:.1f}, min={a_min:.1f}, ≥80: {a_over_80}/{len(ai_scores)}")
    print(f"  Separation: {separation:.1f}")
    print(f"  Tier weights: sent={tier_weights[0]:.2f} para={tier_weights[1]:.2f} doc={tier_weights[2]:.2f}")
    if extra_params:
        print(f"  Bonus params: {extra_params}")

    # Top 5 changed weights
    changed = []
    for k, v in sorted(weights.items()):
        orig = HEURISTIC_WEIGHTS.get(k, 0.5)
        if abs(v - orig) > 0.05:
            changed.append((k, orig, v))
    if changed:
        print(f"  Weight changes (top 10):")
        changed.sort(key=lambda x: abs(x[2] - x[1]), reverse=True)
        for name, orig, new in changed[:10]:
            print(f"    {name:30s}: {orig:.2f} -> {new:.2f} ({'+' if new > orig else ''}{new-orig:.2f})")

    return loss, h_avg, a_avg, separation


# ── Agent 1: Genetic Algorithm ────────────────────────────────────────

def genetic_algorithm(samples, generations=200, pop_size=80, mutation_rate=0.15):
    """Evolve a population of weight vectors using selection + crossover + mutation."""
    print("\n>>> AGENT 1: Genetic Algorithm <<<")

    weight_names = [k for k in HEURISTIC_WEIGHTS if HEURISTIC_WEIGHTS[k] > 0]
    killed = [k for k in HEURISTIC_WEIGHTS if HEURISTIC_WEIGHTS[k] == 0]

    def random_individual():
        weights = dict(HEURISTIC_WEIGHTS)
        tier = [random.uniform(0.2, 0.6), random.uniform(0.1, 0.5), random.uniform(0.1, 0.5)]
        tier_sum = sum(tier)
        tier = tuple(t / tier_sum for t in tier)
        params = {
            "count_bonus_factor": random.uniform(1, 8),
            "count_bonus_max": random.uniform(10, 30),
            "convergence_max": random.uniform(5, 20),
            "density_max": random.uniform(5, 20),
        }
        for name in weight_names:
            weights[name] = random.uniform(0, 2.0)
        for name in killed:
            weights[name] = random.uniform(0, 0.5)  # allow resurrection
        return weights, tier, params

    def fitness(individual):
        weights, tier, params = individual
        loss, _, _ = compute_loss(samples, weights, tier,
                                  params["count_bonus_factor"],
                                  params["count_bonus_max"],
                                  params["convergence_max"],
                                  params["density_max"])
        return -loss  # higher fitness = lower loss

    def crossover(a, b):
        w_a, t_a, p_a = a
        w_b, t_b, p_b = b
        child_w = {}
        for k in w_a:
            child_w[k] = w_a[k] if random.random() < 0.5 else w_b[k]
        child_t = tuple(t_a[i] if random.random() < 0.5 else t_b[i] for i in range(3))
        t_sum = sum(child_t)
        child_t = tuple(t / t_sum for t in child_t)
        child_p = {}
        for k in p_a:
            child_p[k] = p_a[k] if random.random() < 0.5 else p_b[k]
        return child_w, child_t, child_p

    def mutate(individual):
        weights, tier, params = individual
        weights = dict(weights)
        params = dict(params)
        for name in weight_names + killed:
            if random.random() < mutation_rate:
                weights[name] = max(0, weights[name] + random.gauss(0, 0.3))
                weights[name] = min(3.0, weights[name])
        if random.random() < mutation_rate:
            idx = random.randint(0, 2)
            tier = list(tier)
            tier[idx] += random.gauss(0, 0.05)
            tier = [max(0.05, t) for t in tier]
            t_sum = sum(tier)
            tier = tuple(t / t_sum for t in tier)
        for k in params:
            if random.random() < mutation_rate:
                params[k] = max(0, params[k] + random.gauss(0, 2))
        return weights, tier, params

    # Initialize population
    pop = [random_individual() for _ in range(pop_size)]
    best = None
    best_fitness = float('-inf')

    for gen in range(generations):
        scored = [(fitness(ind), ind) for ind in pop]
        scored.sort(key=lambda x: x[0], reverse=True)

        if scored[0][0] > best_fitness:
            best_fitness = scored[0][0]
            best = scored[0][1]

        if gen % 50 == 0:
            print(f"  Gen {gen:4d}: best_loss={-best_fitness:.1f}")

        # Selection: top 30% survive
        survivors = [ind for _, ind in scored[:int(pop_size * 0.3)]]

        # Breed next generation
        next_pop = list(survivors)
        while len(next_pop) < pop_size:
            p1, p2 = random.sample(survivors, 2)
            child = crossover(p1, p2)
            child = mutate(child)
            next_pop.append(child)

        pop = next_pop

    print(f"  Final: best_loss={-best_fitness:.1f}")
    return best


# ── Agent 2: Simulated Annealing ──────────────────────────────────────

def simulated_annealing(samples, iterations=10000, temp_start=100, temp_end=0.1):
    """Simulated annealing with exponential cooling."""
    print("\n>>> AGENT 2: Simulated Annealing <<<")

    weight_names = list(HEURISTIC_WEIGHTS.keys())

    weights = dict(HEURISTIC_WEIGHTS)
    tier = (0.45, 0.30, 0.25)
    params = {"count_bonus_factor": 3, "count_bonus_max": 15,
              "convergence_max": 10, "density_max": 10}

    current_loss, _, _ = compute_loss(samples, weights, tier,
                                       params["count_bonus_factor"],
                                       params["count_bonus_max"],
                                       params["convergence_max"],
                                       params["density_max"])
    best_weights = dict(weights)
    best_tier = tier
    best_params = dict(params)
    best_loss = current_loss

    cooling = (temp_end / temp_start) ** (1.0 / iterations)

    temp = temp_start
    for i in range(iterations):
        # Perturb
        new_weights = dict(weights)
        new_tier = list(tier)
        new_params = dict(params)

        # Mutate 1-3 weights
        for _ in range(random.randint(1, 3)):
            name = random.choice(weight_names)
            new_weights[name] = max(0, min(3.0, new_weights[name] + random.gauss(0, 0.2)))

        # Occasionally mutate tier weights
        if random.random() < 0.2:
            idx = random.randint(0, 2)
            new_tier[idx] += random.gauss(0, 0.03)
            new_tier = [max(0.05, t) for t in new_tier]
            t_sum = sum(new_tier)
            new_tier = [t / t_sum for t in new_tier]

        # Occasionally mutate bonus params
        if random.random() < 0.15:
            k = random.choice(list(new_params.keys()))
            new_params[k] = max(0, new_params[k] + random.gauss(0, 1.5))

        new_tier_t = tuple(new_tier)
        new_loss, _, _ = compute_loss(samples, new_weights, new_tier_t,
                                       new_params["count_bonus_factor"],
                                       new_params["count_bonus_max"],
                                       new_params["convergence_max"],
                                       new_params["density_max"])

        delta = new_loss - current_loss
        if delta < 0 or random.random() < math.exp(-delta / temp):
            weights = new_weights
            tier = new_tier_t
            params = new_params
            current_loss = new_loss

            if current_loss < best_loss:
                best_loss = current_loss
                best_weights = dict(weights)
                best_tier = tier
                best_params = dict(params)

        temp *= cooling

        if i % 2000 == 0:
            print(f"  Iter {i:6d}: loss={current_loss:.1f}, best={best_loss:.1f}, temp={temp:.2f}")

    print(f"  Final: best_loss={best_loss:.1f}")
    return best_weights, best_tier, best_params


# ── Agent 3: Hill Climbing with Restarts ──────────────────────────────

def hill_climbing(samples, restarts=20, steps_per_restart=2000):
    """Greedy local search with random restarts."""
    print("\n>>> AGENT 3: Hill Climbing with Restarts <<<")

    weight_names = list(HEURISTIC_WEIGHTS.keys())
    global_best_loss = float('inf')
    global_best = None

    for r in range(restarts):
        # Random starting point
        weights = {}
        for k, v in HEURISTIC_WEIGHTS.items():
            if v == 0:
                weights[k] = random.uniform(0, 0.3)
            else:
                weights[k] = max(0, v + random.gauss(0, 0.5))
        tier = [random.uniform(0.25, 0.55), random.uniform(0.15, 0.45), random.uniform(0.1, 0.4)]
        t_sum = sum(tier)
        tier = tuple(t / t_sum for t in tier)
        params = {
            "count_bonus_factor": random.uniform(1, 6),
            "count_bonus_max": random.uniform(10, 25),
            "convergence_max": random.uniform(5, 15),
            "density_max": random.uniform(5, 15),
        }

        current_loss, _, _ = compute_loss(samples, weights, tier,
                                           params["count_bonus_factor"],
                                           params["count_bonus_max"],
                                           params["convergence_max"],
                                           params["density_max"])

        for step in range(steps_per_restart):
            # Try small perturbation
            new_weights = dict(weights)
            name = random.choice(weight_names)
            new_weights[name] = max(0, min(3.0, new_weights[name] + random.gauss(0, 0.15)))

            new_tier = list(tier)
            new_params = dict(params)
            if random.random() < 0.2:
                idx = random.randint(0, 2)
                new_tier[idx] += random.gauss(0, 0.02)
                new_tier = [max(0.05, t) for t in new_tier]
                t_sum = sum(new_tier)
                new_tier = [t / t_sum for t in new_tier]
            if random.random() < 0.15:
                k = random.choice(list(new_params.keys()))
                new_params[k] = max(0, new_params[k] + random.gauss(0, 1))

            new_tier_t = tuple(new_tier)
            new_loss, _, _ = compute_loss(samples, new_weights, new_tier_t,
                                           new_params["count_bonus_factor"],
                                           new_params["count_bonus_max"],
                                           new_params["convergence_max"],
                                           new_params["density_max"])

            if new_loss < current_loss:
                weights = new_weights
                tier = new_tier_t
                params = new_params
                current_loss = new_loss

        if current_loss < global_best_loss:
            global_best_loss = current_loss
            global_best = (dict(weights), tier, dict(params))
            print(f"  Restart {r+1:2d}: new best loss={global_best_loss:.1f}")

    print(f"  Final: best_loss={global_best_loss:.1f}")
    return global_best


# ── Main ──────────────────────────────────────────────────────────────

def main():
    random.seed(42)

    print("Loading corpus...")
    samples = load_corpus()
    print(f"Loaded {len(samples)} samples")

    print("Extracting signals from all samples (this takes a moment)...")
    signal_data = extract_signals(samples)
    print(f"Extracted signals for {len(signal_data)} samples")

    # Current baseline
    print("\n" + "=" * 60)
    print("  CURRENT BASELINE")
    print("=" * 60)
    report("Current weights", HEURISTIC_WEIGHTS, (0.45, 0.30, 0.25), signal_data)

    # Run all three agents
    print("\n" + "#" * 60)
    print("  RUNNING OPTIMIZATION AGENTS")
    print("#" * 60)

    # Agent 1: Genetic Algorithm
    ga_weights, ga_tier, ga_params = genetic_algorithm(signal_data,
                                                        generations=300,
                                                        pop_size=100)
    ga_loss, ga_h, ga_a, ga_sep = report("Agent 1: Genetic Algorithm",
                                          ga_weights, ga_tier, signal_data, ga_params)

    # Agent 2: Simulated Annealing
    sa_weights, sa_tier, sa_params = simulated_annealing(signal_data,
                                                          iterations=15000)
    sa_loss, sa_h, sa_a, sa_sep = report("Agent 2: Simulated Annealing",
                                          sa_weights, sa_tier, signal_data, sa_params)

    # Agent 3: Hill Climbing
    hc_result = hill_climbing(signal_data, restarts=30, steps_per_restart=3000)
    hc_weights, hc_tier, hc_params = hc_result
    hc_loss, hc_h, hc_a, hc_sep = report("Agent 3: Hill Climbing",
                                           hc_weights, hc_tier, signal_data, hc_params)

    # Pick winner
    results = [
        ("Genetic Algorithm", ga_loss, ga_weights, ga_tier, ga_params, ga_h, ga_a, ga_sep),
        ("Simulated Annealing", sa_loss, sa_weights, sa_tier, sa_params, sa_h, sa_a, sa_sep),
        ("Hill Climbing", hc_loss, hc_weights, hc_tier, hc_params, hc_h, hc_a, hc_sep),
    ]
    results.sort(key=lambda x: x[1])

    winner_name, winner_loss, winner_weights, winner_tier, winner_params, w_h, w_a, w_sep = results[0]

    print("\n" + "#" * 60)
    print(f"  WINNER: {winner_name}")
    print(f"  Loss: {winner_loss:.1f}")
    print(f"  Human avg: {w_h:.1f}, AI avg: {w_a:.1f}, Separation: {w_sep:.1f}")
    print("#" * 60)

    # Detailed per-sample breakdown for winner
    print("\nPer-sample scores with winning weights:")
    print(f"{'ID':40s} {'Label':15s} {'Score':>6s} {'Category'}")
    print("-" * 80)
    for s in signal_data:
        score = score_with_weights(s, winner_weights, winner_tier,
                                    winner_params.get("count_bonus_factor", 3),
                                    winner_params.get("count_bonus_max", 15),
                                    winner_params.get("convergence_max", 10),
                                    winner_params.get("density_max", 10))
        cat = "Ghost Written" if score >= 45 else "Ghost Touched" if score > 20 else "Clean"
        flag = ""
        if s["label"] == "human" and score > 10:
            flag = " *** HUMAN OVER 10"
        elif s["label"] == "ai" and score < 80:
            flag = " *** AI UNDER 80"
        print(f"{s['id']:40s} {s['label']:15s} {score:6.1f}  {cat}{flag}")

    # Save winning weights
    output = {
        "winner": winner_name,
        "loss": winner_loss,
        "weights": {k: round(v, 4) for k, v in winner_weights.items()},
        "tier_weights": {
            "sentence": round(winner_tier[0], 4),
            "paragraph": round(winner_tier[1], 4),
            "document": round(winner_tier[2], 4),
        },
        "bonus_params": {k: round(v, 4) for k, v in winner_params.items()},
        "metrics": {
            "human_avg": round(w_h, 1),
            "ai_avg": round(w_a, 1),
            "separation": round(w_sep, 1),
        },
    }
    out_path = "/local_data/test_corpus/results/optimization_results.json"
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nResults saved to {out_path}")


if __name__ == "__main__":
    main()
