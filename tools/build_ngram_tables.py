#!/usr/bin/env python3
"""Build n-gram frequency tables from NLTK corpora.

Computes word trigram log-probabilities for AI detection signals.
Ships pre-computed in the repo; users can rebuild or extend.

Usage:
    python build_ngram_tables.py [--min-count 2] [--output-dir ../backend/utils/heuristics/data]
"""
import argparse
import gzip
import json
import math
import os
import sys
from collections import Counter
from pathlib import Path


def ensure_nltk_corpora():
    """Download required NLTK corpora if missing."""
    import nltk
    corpora = ["brown", "gutenberg", "reuters", "webtext"]
    for corpus in corpora:
        try:
            nltk.data.find(f"corpora/{corpus}")
        except LookupError:
            print(f"Downloading NLTK corpus: {corpus}")
            nltk.download(corpus, quiet=True)
    try:
        nltk.data.find("tokenizers/punkt_tab")
    except LookupError:
        print("Downloading NLTK punkt_tab tokenizer")
        nltk.download("punkt_tab", quiet=True)


def get_corpus_words(name):
    """Get word list from named NLTK corpus."""
    if name == "brown":
        from nltk.corpus import brown
        return [w.lower() for w in brown.words()]
    elif name == "gutenberg":
        from nltk.corpus import gutenberg
        return [w.lower() for w in gutenberg.words()]
    elif name == "reuters":
        from nltk.corpus import reuters
        return [w.lower() for w in reuters.words()]
    elif name == "webtext":
        from nltk.corpus import webtext
        return [w.lower() for w in webtext.words()]
    else:
        raise ValueError(f"Unknown corpus: {name}")


def compute_trigrams(words, min_count=2):
    """Compute trigram frequencies from word list.

    Returns:
        trigrams: dict mapping "w1 w2 w3" -> log_probability
        floor_logprob: float, log-probability for unseen trigrams
        stats: dict with corpus statistics
    """
    trigram_counts = Counter()
    for i in range(len(words) - 2):
        tri = f"{words[i]} {words[i+1]} {words[i+2]}"
        trigram_counts[tri] += 1

    total_trigrams = sum(trigram_counts.values())
    unique_before_prune = len(trigram_counts)

    if min_count > 1:
        trigram_counts = {k: v for k, v in trigram_counts.items() if v >= min_count}

    unique_after_prune = len(trigram_counts)
    pruned_total = sum(trigram_counts.values())

    vocab_size = unique_after_prune + 1
    smoothed_total = pruned_total + vocab_size

    trigrams = {}
    for tri, count in trigram_counts.items():
        trigrams[tri] = math.log((count + 1) / smoothed_total)

    floor_logprob = math.log(1 / smoothed_total)

    stats = {
        "total_trigrams": total_trigrams,
        "unique_before_prune": unique_before_prune,
        "unique_after_prune": unique_after_prune,
        "min_count": min_count,
        "floor_logprob": floor_logprob,
    }

    return trigrams, floor_logprob, stats


def compute_genre_baselines(words_by_genre):
    """Compute per-genre MATTR and TTR baselines."""
    import numpy as np

    baselines = {}
    for genre, words in words_by_genre.items():
        if len(words) < 100:
            continue

        window = 50
        mattrs = []
        for i in range(len(words) - window + 1):
            chunk = words[i:i + window]
            ttr = len(set(chunk)) / len(chunk)
            mattrs.append(ttr)

        ttrs = []
        for i in range(0, len(words) - 99, 100):
            chunk = words[i:i + 100]
            ttr = len(set(chunk)) / len(chunk)
            ttrs.append(ttr)

        baselines[genre] = {
            "mattr_mean": float(np.mean(mattrs)) if mattrs else 0.7,
            "mattr_std": float(np.std(mattrs)) if mattrs else 0.05,
            "ttr_mean": float(np.mean(ttrs)) if ttrs else 0.6,
            "ttr_std": float(np.std(ttrs)) if ttrs else 0.08,
        }

    return baselines


def save_gzipped_json(data, path):
    """Save data as gzipped JSON."""
    json_bytes = json.dumps(data, separators=(",", ":")).encode("utf-8")
    with gzip.open(path, "wb") as f:
        f.write(json_bytes)
    size_mb = os.path.getsize(path) / (1024 * 1024)
    entry_count = len(data.get("trigrams", data))
    print(f"  Saved: {path} ({size_mb:.1f} MB, {entry_count} entries)")


def main():
    parser = argparse.ArgumentParser(description="Build n-gram tables from NLTK corpora")
    parser.add_argument("--min-count", type=int, default=2,
                        help="Minimum trigram count to retain (default: 2)")
    parser.add_argument("--output-dir", type=str,
                        default=str(Path(__file__).parent / ".." / "backend" / "utils" / "heuristics" / "data"),
                        help="Output directory for data files")
    args = parser.parse_args()

    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=== Build N-gram Tables ===")
    print(f"Min count: {args.min_count}")
    print(f"Output: {output_dir}")
    print()

    ensure_nltk_corpora()

    corpus_names = ["brown", "gutenberg", "reuters", "webtext"]
    all_words = []
    genre_words = {}

    for name in corpus_names:
        print(f"Processing {name}...")
        words = get_corpus_words(name)
        all_words.extend(words)
        print(f"  {len(words):,} words")

        trigrams, floor_logprob, stats = compute_trigrams(words, args.min_count)
        save_gzipped_json(
            {"trigrams": trigrams, "floor_logprob": floor_logprob, "stats": stats},
            output_dir / f"{name}_trigrams.json.gz"
        )

        if name == "brown":
            from nltk.corpus import brown
            for cat in brown.categories():
                genre_words[f"brown_{cat}"] = [w.lower() for w in brown.words(categories=cat)]
        else:
            genre_words[name] = words

    print(f"\nProcessing combined ({len(all_words):,} words)...")
    trigrams, floor_logprob, stats = compute_trigrams(all_words, args.min_count)
    save_gzipped_json(
        {"trigrams": trigrams, "floor_logprob": floor_logprob, "stats": stats},
        output_dir / "combined_trigrams.json.gz"
    )

    print("\nComputing genre baselines...")
    genre_mapping = {
        "academic": ["brown_learned", "brown_government"],
        "news": ["brown_news", "brown_editorial", "reuters"],
        "fiction": ["brown_fiction", "brown_romance", "brown_mystery", "brown_science_fiction",
                     "brown_adventure", "gutenberg"],
        "casual": ["brown_humor", "brown_hobbies", "webtext"],
        "business": ["brown_government", "brown_news"],
        "general": list(genre_words.keys()),
    }

    mapped_genre_words = {}
    for genre_name, source_keys in genre_mapping.items():
        combined = []
        for key in source_keys:
            if key in genre_words:
                combined.extend(genre_words[key])
        if combined:
            mapped_genre_words[genre_name] = combined

    baselines = compute_genre_baselines(mapped_genre_words)
    with open(output_dir / "genre_baselines.json", "w") as f:
        json.dump(baselines, f, indent=2)
    print(f"  Saved: {output_dir / 'genre_baselines.json'} ({len(baselines)} genres)")

    print("\n=== Done ===")
    print(f"Files in {output_dir}:")
    for p in sorted(output_dir.iterdir()):
        size = p.stat().st_size
        if size > 1024 * 1024:
            print(f"  {p.name} ({size / (1024*1024):.1f} MB)")
        else:
            print(f"  {p.name} ({size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
