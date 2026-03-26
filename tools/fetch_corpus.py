#!/usr/bin/env python3
"""Fetch diverse public domain texts from Project Gutenberg for voice profile testing.

Downloads 12 diverse texts + 8 Shakespeare texts, strips Gutenberg boilerplate,
saves as plain .txt files. Skips files that already exist.
"""

import os
import re
import sys
import urllib.request
import urllib.error

# Base URL pattern for Project Gutenberg plain text
PG_URL = "https://www.gutenberg.org/cache/epub/{id}/pg{id}.txt"

# Project root (two levels up from code/tools/)
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

DIVERSE_DIR = os.path.join(PROJECT_ROOT, "local_data", "corpus", "diverse")
SHAKESPEARE_DIR = os.path.join(PROJECT_ROOT, "local_data", "corpus", "shakespeare")

DIVERSE_TEXTS = [
    (74,    "tom_sawyer.txt",           "Tom Sawyer - Mark Twain"),
    (1342,  "pride_and_prejudice.txt",  "Pride & Prejudice - Jane Austen"),
    (1400,  "great_expectations.txt",   "Great Expectations - Charles Dickens"),
    (2147,  "poe_tales.txt",            "Tales - Edgar Allan Poe"),
    (1661,  "sherlock_holmes.txt",       "Sherlock Holmes - Arthur Conan Doyle"),
    (205,   "walden.txt",               "Walden - Henry David Thoreau"),
    (1228,  "origin_of_species.txt",    "Origin of Species - Charles Darwin"),
    (1497,  "republic.txt",             "The Republic - Plato"),
    (35,    "time_machine.txt",         "The Time Machine - H.G. Wells"),
    (84,    "frankenstein.txt",         "Frankenstein - Mary Shelley"),
    (1232,  "the_prince.txt",           "The Prince - Machiavelli"),
    (11,    "alice_in_wonderland.txt",  "Alice in Wonderland - Lewis Carroll"),
]

SHAKESPEARE_TEXTS = [
    (1524,  "hamlet.txt",               "Hamlet"),
    (1533,  "macbeth.txt",              "Macbeth"),
    (1513,  "romeo_and_juliet.txt",     "Romeo & Juliet"),
    (1514,  "midsummer_night.txt",      "A Midsummer Night's Dream"),
    (1041,  "sonnets.txt",              "Sonnets"),
    (23042, "tempest.txt",              "The Tempest"),
    (1532,  "king_lear.txt",            "King Lear"),
    (1531,  "othello.txt",             "Othello"),
]


def strip_gutenberg_boilerplate(text: str) -> str:
    """Remove Project Gutenberg header and footer."""
    # Find start marker
    start_match = re.search(r"\*\*\* ?START OF (?:THE |THIS )?PROJECT GUTENBERG", text, re.IGNORECASE)
    if start_match:
        # Skip to end of line after the marker
        newline_pos = text.find("\n", start_match.end())
        if newline_pos != -1:
            text = text[newline_pos + 1:]

    # Find end marker
    end_match = re.search(r"\*\*\* ?END OF (?:THE |THIS )?PROJECT GUTENBERG", text, re.IGNORECASE)
    if end_match:
        text = text[:end_match.start()]

    return text.strip()


def download_text(pg_id: int, filename: str, label: str, output_dir: str) -> dict | None:
    """Download a single text from Project Gutenberg.

    Returns dict with stats or None if skipped/failed.
    """
    filepath = os.path.join(output_dir, filename)

    if os.path.exists(filepath):
        size = os.path.getsize(filepath)
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            word_count = len(f.read().split())
        print(f"  SKIP  {label} (already exists: {word_count:,} words, {size:,} bytes)")
        return {"label": label, "words": word_count, "bytes": size, "status": "skipped"}

    url = PG_URL.format(id=pg_id)
    print(f"  FETCH {label} (PG #{pg_id})...", end=" ", flush=True)

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (corpus-fetch)"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read()
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
        print(f"FAILED: {e}")
        return None

    # Try UTF-8 first, fall back to latin-1
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("latin-1")

    text = strip_gutenberg_boilerplate(text)
    word_count = len(text.split())
    byte_size = len(text.encode("utf-8"))

    os.makedirs(output_dir, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(text)

    print(f"OK ({word_count:,} words, {byte_size:,} bytes)")
    return {"label": label, "words": word_count, "bytes": byte_size, "status": "downloaded"}


def main():
    print("=" * 60)
    print("Project Gutenberg Corpus Fetcher")
    print("=" * 60)

    results = []

    print(f"\n--- Diverse Texts ({len(DIVERSE_TEXTS)}) ---")
    print(f"    Output: {DIVERSE_DIR}\n")
    os.makedirs(DIVERSE_DIR, exist_ok=True)
    for pg_id, filename, label in DIVERSE_TEXTS:
        result = download_text(pg_id, filename, label, DIVERSE_DIR)
        if result:
            results.append(result)

    print(f"\n--- Shakespeare Texts ({len(SHAKESPEARE_TEXTS)}) ---")
    print(f"    Output: {SHAKESPEARE_DIR}\n")
    os.makedirs(SHAKESPEARE_DIR, exist_ok=True)
    for pg_id, filename, label in SHAKESPEARE_TEXTS:
        result = download_text(pg_id, filename, label, SHAKESPEARE_DIR)
        if result:
            results.append(result)

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    downloaded = [r for r in results if r["status"] == "downloaded"]
    skipped = [r for r in results if r["status"] == "skipped"]
    total_words = sum(r["words"] for r in results)
    total_bytes = sum(r["bytes"] for r in results)
    expected = len(DIVERSE_TEXTS) + len(SHAKESPEARE_TEXTS)
    failed = expected - len(results)

    print(f"  Downloaded: {len(downloaded)}")
    print(f"  Skipped:    {len(skipped)}")
    print(f"  Failed:     {failed}")
    print(f"  Total:      {total_words:,} words, {total_bytes:,} bytes")

    # Check minimum word count
    under_500 = [r for r in results if r["words"] < 500]
    if under_500:
        print(f"\n  WARNING: {len(under_500)} texts under 500 words:")
        for r in under_500:
            print(f"    - {r['label']}: {r['words']} words")

    if failed:
        print(f"\n  WARNING: {failed} downloads failed!")
        sys.exit(1)

    print("\nDone.")


if __name__ == "__main__":
    main()
