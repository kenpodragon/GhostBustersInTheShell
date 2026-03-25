#!/usr/bin/env python3
"""
Phase 3.11: AI + Heuristic Detection Pipeline Combo Testing

Tests 4 pipeline variations across the corpus to find optimal detection architecture.
Each variation combines AI analysis and Python heuristics differently.

Usage:
    python test_ai_combos.py --variation A --prompt-version 1
    python test_ai_combos.py --variation B --prompt-version 1
    python test_ai_combos.py --variation C --prompt-version 1
    python test_ai_combos.py --variation D --prompt-version 1
    python test_ai_combos.py --compare  (compare all results)
"""

import json
import os
import sys
import subprocess
import re
import time
import argparse
import urllib.request
from datetime import datetime
from pathlib import Path

# Paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
CORPUS_PATH = PROJECT_ROOT / "local_data" / "test_corpus" / "corpus.json"
RESULTS_DIR = PROJECT_ROOT / "local_data" / "ai_detection_combos"
API_BASE = "http://localhost:8066"

# Detection guide for Variation C and D
DETECTION_GUIDE = """
# AI Text Detection Guide

## High-Confidence AI Signals (when present, strong indicator of AI)
1. **Buzzword density**: Words like "leverage", "robust", "innovative", "transformative", "navigate", "foster", "facilitate", "comprehensive", "multifaceted", "nuanced", "delve", "paradigm", "holistic", "synergy", "streamline", "optimize", "embrace", "tapestry", "intersection", "realm", "underscore", "stakeholder"
2. **Triadic lists**: AI defaults to listing exactly 3 items. Humans list 2 or 4+.
3. **Trailing participial phrases**: Sentences ending with "-ing" phrases ("...improving outcomes across the board")
4. **Em dash overuse**: AI (especially post-GPT-4) uses em dashes at 10-20 per 1000 words. Humans use 0-3.
5. **Uniform sentence length**: AI sentences cluster at 15-25 words. Human writing varies wildly (3 to 40+).
6. **No first-person pronouns**: AI defaults to impersonal third-person. Humans use "I", "me", "my".
7. **No questions or exclamations**: All-declarative text is an AI tell.
8. **Self-contained paragraphs**: Each paragraph is an island. Humans cross-reference, callback, digress.
9. **No digressions**: AI stays unnaturally focused. Humans tangent.
10. **AI opening phrases**: "In today's rapidly...", "It's worth noting...", "When it comes to..."
11. **Hedge clustering**: "potentially", "arguably", "perhaps", "it could be said" — AI hedges constantly.
12. **Sensory rotation**: AI systematically covers all 5 senses. Humans focus on 1-2.

## Human Tells (presence suggests human writing)
1. **Contractions**: "don't", "it's", "I've" — AI underuses these
2. **First-person pronouns**: "I think", "I've noticed", "my experience"
3. **Specific names/dates/numbers**: Real specifics, not vague abstractions
4. **Irregular punctuation**: Exclamation marks, ellipses, parentheticals
5. **Digressions**: Tangential thoughts, asides, anecdotes
6. **Questions**: Rhetorical or direct questions
7. **Emotional volatility**: Shifts in tone, sarcasm, humor
8. **Typos/self-corrections**: Natural imperfections

## Scoring Guidance
- 0-20: Clean (human) — few or no AI signals, human tells present
- 21-44: Ghost Touched (assisted) — some AI signals mixed with human tells
- 45-100: Ghost Written (AI) — dominant AI patterns, few human tells
"""

# Prompt templates for each variation
PROMPTS = {
    # --- VARIATION A: AI parallel (no heuristic context) ---
    "A_v1": """You are an AI text detection expert. Analyze this text and determine if it was written by AI or a human.

Score from 0 (definitely human) to 100 (definitely AI).
Identify specific patterns that indicate AI or human authorship.

Return ONLY valid JSON:
{{"overall_score": 0-100, "analysis_mode": "ai", "detected_patterns": [{{"pattern": "name", "detail": "description"}}], "reasoning": "brief explanation"}}

Text:
---
{text}
---""",

    "A_v2": """You are a forensic text analyst specializing in distinguishing AI-generated from human-written content. You have deep expertise in computational linguistics, stylometry, and LLM output patterns.

Analyze this text carefully. Look for:
- Vocabulary: buzzwords, hedge words, vague abstractions vs specific details
- Structure: sentence length uniformity, triadic lists, self-contained paragraphs
- Voice: first-person usage, contractions, questions, digressions, emotional range
- Patterns: em dash usage, trailing participials, AI opening phrases, sensory rotation

Score 0 (definitely human) to 100 (definitely AI).

Return ONLY valid JSON:
{{"overall_score": 0-100, "analysis_mode": "ai", "confidence": "high|medium|low", "detected_patterns": [{{"pattern": "name", "detail": "description"}}], "human_tells": [{{"pattern": "name", "detail": "description"}}], "reasoning": "brief explanation"}}

Text:
---
{text}
---""",

    "A_v3": """Determine if this text is AI-generated or human-written. Score 0-100 (0=human, 100=AI).

Be calibrated: most AI text scores 60-90. Most human text scores 0-25. Don't cluster around 50.
Look for: buzzword density, sentence uniformity, missing first-person/contractions/questions, em dash overuse, triadic lists, trailing -ing phrases, self-contained paragraphs, no digressions.
Human tells: contractions, first-person, specific names/dates, irregular punctuation, tangents, emotional shifts.

Return ONLY valid JSON:
{{"overall_score": 0-100, "analysis_mode": "ai", "detected_patterns": [{{"pattern": "name", "detail": "description"}}], "reasoning": "one sentence"}}

Text:
---
{text}
---""",

    # --- VARIATION B: Heuristics first, passed to AI ---
    "B_v1": """You are an AI text detection expert. A heuristic analysis engine has already scored this text. Review both the text and the heuristic findings to produce a final assessment.

HEURISTIC RESULTS:
- Score: {heuristic_score}/100
- Classification: {heuristic_category} ({heuristic_confidence})
- Signal count: {signal_count}
- Genre detected: {genre}
- Patterns found: {patterns}

Now analyze the original text yourself, considering the heuristic findings. You may agree or disagree with the heuristic score. Look for patterns the heuristics may have missed (semantic coherence, topical depth, argumentative sophistication, personal anecdotes).

Return ONLY valid JSON:
{{"overall_score": 0-100, "analysis_mode": "ai_informed", "heuristic_agreement": "agree|partially|disagree", "detected_patterns": [{{"pattern": "name", "detail": "description"}}], "missed_by_heuristics": [{{"pattern": "name", "detail": "description"}}], "reasoning": "brief explanation"}}

Text:
---
{text}
---""",

    "B_v2": """A Python heuristic engine scored this text {heuristic_score}/100 ({heuristic_category}). It found {signal_count} signals: {patterns}

Your job: look deeper. The heuristics catch surface patterns but miss semantic and contextual tells. Focus on:
1. Does the argument have genuine depth or is it superficially coherent?
2. Are examples real and specific or generated filler?
3. Does the author's voice feel consistent or performed?
4. Are there signs of lived experience or just aggregated knowledge?

Score 0-100. Be calibrated: human text typically 0-25, AI text 60-90.

Return ONLY valid JSON:
{{"overall_score": 0-100, "analysis_mode": "ai_informed", "detected_patterns": [{{"pattern": "name", "detail": "description"}}], "reasoning": "one sentence"}}

Text:
---
{text}
---""",

    # --- VARIATION C: AI + Heuristics + Detection Guide ---
    "C_v1": """You are an AI text detection expert. You have been given:
1. A comprehensive detection guide with known AI patterns and human tells
2. Heuristic analysis results from a Python engine
3. The text to analyze

DETECTION GUIDE:
{detection_guide}

HEURISTIC RESULTS:
- Score: {heuristic_score}/100 ({heuristic_category}, {heuristic_confidence})
- Signals: {signal_count} | Genre: {genre}
- Patterns: {patterns}

Using ALL of this context, produce your final detection score. Cross-reference the guide's patterns against what you observe in the text. Note any patterns the heuristics missed that the guide describes.

Score 0-100. Be calibrated: human 0-25, AI 60-90.

Return ONLY valid JSON:
{{"overall_score": 0-100, "analysis_mode": "ai_full_context", "detected_patterns": [{{"pattern": "name", "detail": "description"}}], "guide_matches": ["pattern names from guide that apply"], "reasoning": "brief explanation"}}

Text:
---
{text}
---""",

    # --- VARIATION D: AI + Guide first, then heuristics added ---
    "D_v1": """You are an AI text detection expert with deep knowledge of LLM output patterns.

DETECTION GUIDE:
{detection_guide}

Using this guide, analyze the following text. Score 0-100 (0=human, 100=AI).
Focus on the guide's high-confidence signals and human tells. Be calibrated: human 0-25, AI 60-90.

Return ONLY valid JSON:
{{"overall_score": 0-100, "analysis_mode": "ai_guided", "detected_patterns": [{{"pattern": "name", "detail": "description"}}], "human_tells_found": [{{"pattern": "name", "detail": "description"}}], "reasoning": "brief explanation"}}

Text:
---
{text}
---""",
}


def load_corpus():
    """Load test corpus."""
    with open(CORPUS_PATH) as f:
        data = json.load(f)
    return data["samples"]


def call_heuristic_api(text):
    """Call our detector API with heuristics only."""
    payload = json.dumps({"text": text, "use_ai": False}).encode()
    req = urllib.request.Request(
        f"{API_BASE}/api/analyze",
        data=payload,
        headers={"Content-Type": "application/json"}
    )
    try:
        resp = urllib.request.urlopen(req, timeout=30)
        return json.loads(resp.read())
    except Exception as e:
        return {"overall_score": 0, "error": str(e)}


def call_claude_cli(prompt, model="sonnet"):
    """Call Claude CLI with a prompt. Returns parsed JSON or error dict."""
    try:
        result = subprocess.run(
            ["claude", "-p", prompt, "--model", model, "--output-format", "json"],
            capture_output=True, text=True, timeout=120
        )
        if result.returncode != 0:
            return {"error": f"CLI error: {result.stderr[:200]}"}

        output = result.stdout.strip()

        # Handle wrapper JSON from --output-format json
        try:
            wrapper = json.loads(output)
            if isinstance(wrapper, dict) and "result" in wrapper:
                inner = wrapper["result"]
            else:
                inner = output
        except json.JSONDecodeError:
            inner = output

        # Strip code fences
        if isinstance(inner, str):
            inner = re.sub(r'^```(?:json)?\s*', '', inner.strip())
            inner = re.sub(r'\s*```$', '', inner.strip())

        # Parse final JSON
        if isinstance(inner, str):
            return json.loads(inner)
        return inner

    except subprocess.TimeoutExpired:
        return {"error": "timeout"}
    except json.JSONDecodeError as e:
        return {"error": f"JSON parse error: {str(e)}", "raw": output[:500] if 'output' in dir() else ""}
    except Exception as e:
        return {"error": str(e)}


def classify_label(label):
    """Normalize corpus labels to binary AI/human."""
    if label in ("ai", "ai_humanized", "ai_paraphrased", "ai_polished"):
        return "ai"
    elif label in ("human",):
        return "human"
    elif label == "mixed":
        return "mixed"
    return label


def compute_metrics(results, threshold=25):
    """Compute accuracy metrics from results."""
    tp = fp = tn = fn = 0
    scores_ai = []
    scores_human = []

    for r in results:
        true_label = classify_label(r["true_label"])
        if true_label == "mixed":
            continue

        score = r.get("final_score", r.get("ai_score", r.get("heuristic_score", 0)))
        predicted_ai = score >= threshold

        if true_label == "ai":
            scores_ai.append(score)
            if predicted_ai:
                tp += 1
            else:
                fn += 1
        elif true_label == "human":
            scores_human.append(score)
            if predicted_ai:
                fp += 1
            else:
                tn += 1

    total = tp + fp + tn + fn
    accuracy = (tp + tn) / total if total else 0
    precision = tp / (tp + fp) if (tp + fp) else 0
    recall = tp / (tp + fn) if (tp + fn) else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0

    return {
        "accuracy": round(accuracy * 100, 1),
        "precision": round(precision * 100, 1),
        "recall": round(recall * 100, 1),
        "f1": round(f1 * 100, 1),
        "tp": tp, "fp": fp, "tn": tn, "fn": fn,
        "ai_avg": round(sum(scores_ai) / len(scores_ai), 1) if scores_ai else 0,
        "human_avg": round(sum(scores_human) / len(scores_human), 1) if scores_human else 0,
        "separation": round((sum(scores_ai) / len(scores_ai) if scores_ai else 0) - (sum(scores_human) / len(scores_human) if scores_human else 0), 1),
        "total_samples": total,
    }


def run_variation_a(samples, prompt_key, model="sonnet"):
    """Variation A: AI + Heuristics in parallel, combined score."""
    results = []
    prompt_template = PROMPTS[prompt_key]

    for i, sample in enumerate(samples):
        text = sample["text"]
        true_label = sample["label"]
        sample_id = sample.get("id", f"sample_{i}")

        print(f"  [{i+1}/{len(samples)}] {sample_id} ({true_label})...", end=" ", flush=True)

        # Run heuristics
        heuristic = call_heuristic_api(text)
        h_score = heuristic.get("overall_score", 0)

        # Run AI
        prompt = prompt_template.format(text=text[:3000])
        ai_result = call_claude_cli(prompt, model=model)
        ai_score = ai_result.get("overall_score", 0) if "error" not in ai_result else 0

        # Combine: weighted average (AI trusted more for semantic, heuristic for surface)
        final_score = round(ai_score * 0.6 + h_score * 0.4, 1)

        results.append({
            "id": sample_id,
            "true_label": true_label,
            "genre": sample.get("genre", ""),
            "heuristic_score": h_score,
            "ai_score": ai_score,
            "final_score": final_score,
            "ai_patterns": ai_result.get("detected_patterns", []),
            "ai_reasoning": ai_result.get("reasoning", ""),
            "ai_error": ai_result.get("error", None),
        })
        print(f"H={h_score} AI={ai_score} Final={final_score}")

    return results


def run_variation_b(samples, prompt_key, model="sonnet"):
    """Variation B: Heuristics first, results passed to AI."""
    results = []
    prompt_template = PROMPTS[prompt_key]

    for i, sample in enumerate(samples):
        text = sample["text"]
        true_label = sample["label"]
        sample_id = sample.get("id", f"sample_{i}")

        print(f"  [{i+1}/{len(samples)}] {sample_id} ({true_label})...", end=" ", flush=True)

        # Run heuristics first
        heuristic = call_heuristic_api(text)
        h_score = heuristic.get("overall_score", 0)
        classification = heuristic.get("classification", {})
        patterns = heuristic.get("detected_patterns", [])
        pattern_summary = "; ".join([f"{p['pattern']}: {p['detail'][:60]}" for p in patterns[:10]])

        # Pass heuristic context to AI
        prompt = prompt_template.format(
            text=text[:3000],
            heuristic_score=h_score,
            heuristic_category=classification.get("label", "Unknown"),
            heuristic_confidence=classification.get("confidence", "unknown"),
            signal_count=heuristic.get("signal_count", 0),
            genre=heuristic.get("genre", "unknown"),
            patterns=pattern_summary or "none detected",
        )
        ai_result = call_claude_cli(prompt, model=model)
        ai_score = ai_result.get("overall_score", 0) if "error" not in ai_result else h_score

        # AI score is the final (it had heuristic context)
        final_score = ai_score

        results.append({
            "id": sample_id,
            "true_label": true_label,
            "genre": sample.get("genre", ""),
            "heuristic_score": h_score,
            "ai_score": ai_score,
            "final_score": final_score,
            "ai_patterns": ai_result.get("detected_patterns", []),
            "missed_by_heuristics": ai_result.get("missed_by_heuristics", []),
            "ai_reasoning": ai_result.get("reasoning", ""),
            "ai_error": ai_result.get("error", None),
        })
        print(f"H={h_score} AI={ai_score} Final={final_score}")

    return results


def run_variation_c(samples, prompt_key, model="sonnet"):
    """Variation C: AI + Heuristics + Full Detection Guide."""
    results = []
    prompt_template = PROMPTS[prompt_key]

    for i, sample in enumerate(samples):
        text = sample["text"]
        true_label = sample["label"]
        sample_id = sample.get("id", f"sample_{i}")

        print(f"  [{i+1}/{len(samples)}] {sample_id} ({true_label})...", end=" ", flush=True)

        # Run heuristics
        heuristic = call_heuristic_api(text)
        h_score = heuristic.get("overall_score", 0)
        classification = heuristic.get("classification", {})
        patterns = heuristic.get("detected_patterns", [])
        pattern_summary = "; ".join([f"{p['pattern']}: {p['detail'][:60]}" for p in patterns[:10]])

        # AI gets everything: guide + heuristics + text
        prompt = prompt_template.format(
            text=text[:2500],
            detection_guide=DETECTION_GUIDE,
            heuristic_score=h_score,
            heuristic_category=classification.get("label", "Unknown"),
            heuristic_confidence=classification.get("confidence", "unknown"),
            signal_count=heuristic.get("signal_count", 0),
            genre=heuristic.get("genre", "unknown"),
            patterns=pattern_summary or "none detected",
        )
        ai_result = call_claude_cli(prompt, model=model)
        ai_score = ai_result.get("overall_score", 0) if "error" not in ai_result else h_score

        final_score = ai_score

        results.append({
            "id": sample_id,
            "true_label": true_label,
            "genre": sample.get("genre", ""),
            "heuristic_score": h_score,
            "ai_score": ai_score,
            "final_score": final_score,
            "ai_patterns": ai_result.get("detected_patterns", []),
            "guide_matches": ai_result.get("guide_matches", []),
            "ai_reasoning": ai_result.get("reasoning", ""),
            "ai_error": ai_result.get("error", None),
        })
        print(f"H={h_score} AI={ai_score} Final={final_score}")

    return results


def run_variation_d(samples, prompt_key, model="sonnet"):
    """Variation D: AI + Guide first, then heuristics, then combined."""
    results = []
    prompt_template = PROMPTS[prompt_key]

    for i, sample in enumerate(samples):
        text = sample["text"]
        true_label = sample["label"]
        sample_id = sample.get("id", f"sample_{i}")

        print(f"  [{i+1}/{len(samples)}] {sample_id} ({true_label})...", end=" ", flush=True)

        # AI with guide first (no heuristic context)
        prompt = prompt_template.format(
            text=text[:2500],
            detection_guide=DETECTION_GUIDE,
        )
        ai_result = call_claude_cli(prompt, model=model)
        ai_score = ai_result.get("overall_score", 0) if "error" not in ai_result else 0

        # Then heuristics
        heuristic = call_heuristic_api(text)
        h_score = heuristic.get("overall_score", 0)

        # Combined: weighted merge (AI primary, heuristics secondary)
        final_score = round(ai_score * 0.55 + h_score * 0.45, 1)

        results.append({
            "id": sample_id,
            "true_label": true_label,
            "genre": sample.get("genre", ""),
            "heuristic_score": h_score,
            "ai_score": ai_score,
            "final_score": final_score,
            "ai_patterns": ai_result.get("detected_patterns", []),
            "human_tells": ai_result.get("human_tells_found", []),
            "ai_reasoning": ai_result.get("reasoning", ""),
            "ai_error": ai_result.get("error", None),
        })
        print(f"H={h_score} AI={ai_score} Final={final_score}")

    return results


def save_results(variation, prompt_key, model, results, metrics):
    """Save results to JSON."""
    output = {
        "variation": variation,
        "prompt_key": prompt_key,
        "model": model,
        "timestamp": datetime.now().isoformat(),
        "metrics": metrics,
        "sample_count": len(results),
        "results": results,
    }
    filename = f"variation_{variation}_{prompt_key}_{model}_{datetime.now().strftime('%H%M%S')}.json"
    filepath = RESULTS_DIR / filename
    with open(filepath, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nResults saved to: {filepath}")
    return filepath


def compare_all():
    """Compare all result files and produce summary."""
    result_files = sorted(RESULTS_DIR.glob("variation_*.json"))
    if not result_files:
        print("No results found. Run variations first.")
        return

    print("\n" + "=" * 80)
    print("COMPARISON OF ALL PIPELINE VARIATIONS")
    print("=" * 80)
    print(f"{'Variation':<12} {'Prompt':<8} {'Model':<8} {'Acc%':<7} {'F1%':<7} {'Prec%':<7} {'Rec%':<7} {'AI Avg':<8} {'Hum Avg':<8} {'Sep':<6} {'FP':<4} {'FN':<4}")
    print("-" * 100)

    all_results = []
    for fp in result_files:
        with open(fp) as f:
            data = json.load(f)
        m = data["metrics"]
        row = {
            "file": fp.name,
            "variation": data["variation"],
            "prompt": data["prompt_key"],
            "model": data["model"],
            **m,
        }
        all_results.append(row)
        print(f"{data['variation']:<12} {data['prompt_key']:<8} {data['model']:<8} {m['accuracy']:<7} {m['f1']:<7} {m['precision']:<7} {m['recall']:<7} {m['ai_avg']:<8} {m['human_avg']:<8} {m['separation']:<6} {m['fp']:<4} {m['fn']:<4}")

    # Find best
    if all_results:
        best = max(all_results, key=lambda x: x["f1"])
        print(f"\nBEST: Variation {best['variation']} / {best['prompt']} / {best['model']}")
        print(f"  Accuracy: {best['accuracy']}% | F1: {best['f1']}% | Separation: {best['separation']}")

    # Save comparison
    comp_path = RESULTS_DIR / "comparison_summary.json"
    with open(comp_path, "w") as f:
        json.dump(all_results, f, indent=2)
    print(f"\nComparison saved to: {comp_path}")


def run_subset(samples, n=20):
    """Get a representative subset for quick iteration."""
    ai_samples = [s for s in samples if classify_label(s["label"]) == "ai"]
    human_samples = [s for s in samples if classify_label(s["label"]) == "human"]
    mixed_samples = [s for s in samples if classify_label(s["label"]) == "mixed"]

    # Take proportional subset
    n_ai = min(n // 3, len(ai_samples))
    n_human = min(n - n_ai, len(human_samples))

    import random
    random.seed(42)
    subset = random.sample(ai_samples, n_ai) + random.sample(human_samples, n_human) + mixed_samples[:2]
    random.shuffle(subset)
    return subset


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test AI+Heuristic detection pipeline combinations")
    parser.add_argument("--variation", choices=["A", "B", "C", "D"], help="Pipeline variation to test")
    parser.add_argument("--prompt-version", type=int, default=1, help="Prompt version (1, 2, 3)")
    parser.add_argument("--model", default="sonnet", help="Claude model (haiku, sonnet, opus)")
    parser.add_argument("--subset", type=int, default=0, help="Use N-sample subset for quick iteration (0=full corpus)")
    parser.add_argument("--compare", action="store_true", help="Compare all existing results")
    args = parser.parse_args()

    if args.compare:
        compare_all()
        sys.exit(0)

    if not args.variation:
        parser.print_help()
        sys.exit(1)

    # Load corpus
    samples = load_corpus()
    if args.subset > 0:
        samples = run_subset(samples, args.subset)
        print(f"Using {len(samples)}-sample subset")
    else:
        print(f"Using full corpus: {len(samples)} samples")

    prompt_key = f"{args.variation}_v{args.prompt_version}"
    if prompt_key not in PROMPTS:
        print(f"ERROR: No prompt '{prompt_key}'. Available: {[k for k in PROMPTS if k.startswith(args.variation)]}")
        sys.exit(1)

    print(f"\nRunning Variation {args.variation} | Prompt: {prompt_key} | Model: {args.model}")
    print("=" * 60)

    # Run the appropriate variation
    run_fn = {"A": run_variation_a, "B": run_variation_b, "C": run_variation_c, "D": run_variation_d}[args.variation]
    results = run_fn(samples, prompt_key, model=args.model)

    # Compute metrics at multiple thresholds
    for threshold in [20, 25, 30, 35]:
        metrics = compute_metrics(results, threshold=threshold)
        print(f"\n  Threshold={threshold}: Acc={metrics['accuracy']}% F1={metrics['f1']}% Prec={metrics['precision']}% Rec={metrics['recall']}% Sep={metrics['separation']} FP={metrics['fp']} FN={metrics['fn']}")

    # Save with default threshold
    metrics = compute_metrics(results, threshold=25)
    save_results(args.variation, prompt_key, args.model, results, metrics)
