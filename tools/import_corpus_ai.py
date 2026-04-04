#!/usr/bin/env python3
"""Import Stephen's corpus with AI extraction enabled.

Reads .txt files from local_data/corpus/personal/, calls the parse API
with use_ai=true and filename for each file. Skips files <200 words.
Files over 6K words are chunked on paragraph boundaries (not truncated).

Resumable: tracks progress in a state file. Re-run to retry failures.
Ctrl+C: saves state and exits gracefully.

Usage: python tools/import_corpus_ai.py [--reset]
  --reset  Clear state file and start fresh
Requires: backend running on localhost:8066 with AI enabled
"""
import json
import os
import signal
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

API_BASE = "http://localhost:8066"
PROFILE_ID = 1295
CORPUS_DIR = Path(__file__).resolve().parent.parent.parent / "local_data" / "corpus" / "personal"
EXPORT_PATH = Path(__file__).resolve().parent.parent.parent / "docs" / "voice_profiles" / f"stephen_voice_baseline_export_{datetime.now().strftime('%m%d%Y')}_65_ai.json"
STATE_FILE = Path(__file__).resolve().parent / "import_state.json"
MIN_WORDS = 200
CHUNK_TARGET = 6000  # words per chunk — keeps AI calls under timeout
RUNT_THRESHOLD = 2000  # merge last chunk into previous if below this
REQUEST_TIMEOUT = 600  # seconds — Claude CLI can be slow under load
COOLDOWN = 5  # seconds between API calls to avoid rate limiting

# Graceful shutdown flag
_shutdown = False


def _handle_signal(signum, frame):
    global _shutdown
    _shutdown = True
    print("\n  >>> Ctrl+C received — finishing current item, then saving state...")


def _split_lines(text: str, target_words: int) -> list[tuple[list[str], int]]:
    """Split text on single newlines into chunks of ~target_words.

    Fallback for paragraphs that exceed target_words on their own.
    """
    lines = text.split("\n")
    chunks = []
    current_parts = []
    current_wc = 0

    for line in lines:
        line_wc = len(line.split())
        if current_wc + line_wc > target_words and current_parts:
            chunks.append((current_parts, current_wc))
            current_parts = []
            current_wc = 0
        current_parts.append(line)
        current_wc += line_wc

    if current_parts:
        chunks.append((current_parts, current_wc))

    return chunks


def chunk_text(text: str, target_words: int, runt_threshold: int = RUNT_THRESHOLD) -> list[tuple[str, int]]:
    """Split text into chunks of ~target_words, breaking on paragraph boundaries.

    Falls back to single-newline splits for oversized paragraphs.
    If the last chunk is below runt_threshold, merges it into the previous chunk.
    Returns list of (chunk_text, word_count) tuples.
    """
    paragraphs = text.split("\n\n")
    chunks = []
    current_parts = []
    current_wc = 0

    for para in paragraphs:
        para_wc = len(para.split())

        # Oversized paragraph — break it down on single newlines
        if para_wc > target_words:
            # Flush current accumulator first
            if current_parts:
                chunks.append((current_parts, current_wc, "\n\n"))
                current_parts = []
                current_wc = 0
            for sub_parts, sub_wc in _split_lines(para, target_words):
                chunks.append((sub_parts, sub_wc, "\n"))
            continue

        if current_wc + para_wc > target_words and current_parts:
            chunks.append((current_parts, current_wc, "\n\n"))
            current_parts = []
            current_wc = 0
        current_parts.append(para)
        current_wc += para_wc

    if current_parts:
        chunks.append((current_parts, current_wc, "\n\n"))

    # Merge runt last chunk into previous
    if len(chunks) > 1 and chunks[-1][1] < runt_threshold:
        last_parts, last_wc, _ = chunks.pop()
        prev_parts, prev_wc, prev_sep = chunks.pop()
        chunks.append((prev_parts + last_parts, prev_wc + last_wc, prev_sep))

    return [(sep.join(parts), wc) for parts, wc, sep in chunks]


def load_state() -> dict:
    """Load import state from disk. Returns empty state if no file."""
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"completed": {}, "failed": {}, "duplicates": []}


def save_state(state: dict):
    """Save import state to disk."""
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def main():
    global _shutdown

    # Handle --reset flag
    if "--reset" in sys.argv:
        if STATE_FILE.exists():
            STATE_FILE.unlink()
            print("State file cleared.")
        else:
            print("No state file to clear.")

    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    # Load existing state
    state = load_state()
    completed = state.get("completed", {})
    failed = state.get("failed", {})

    if completed:
        print(f"Resuming: {len(completed)} already completed, {len(failed)} previously failed")

    # 1. Verify AI is available
    print("Checking AI status...")
    try:
        r = requests.get(f"{API_BASE}/api/settings", timeout=10)
        if r.status_code == 200:
            settings = r.json()
            ai_enabled = settings.get("ai_enabled") or settings.get("enabled")
            ai_provider = settings.get("ai_provider") or settings.get("provider")
            print(f"  AI enabled: {ai_enabled}, provider: {ai_provider}")
            if not ai_enabled:
                print("  WARNING: AI is not enabled. Observations will not be generated.")
                resp = input("  Continue anyway? (y/n): ")
                if resp.lower() != "y":
                    sys.exit(0)
    except Exception as e:
        print(f"  Could not check AI status: {e}")

    # 2. Gather corpus files and chunk oversized ones
    txt_files = sorted(CORPUS_DIR.glob("*.txt"))
    print(f"\nFound {len(txt_files)} .txt files in {CORPUS_DIR}")

    eligible = []  # list of (filename, text, word_count)
    skipped = 0
    for fpath in txt_files:
        text = fpath.read_text(encoding="utf-8", errors="replace")
        wc = len(text.split())
        if wc < MIN_WORDS:
            print(f"  SKIP {fpath.name} ({wc} words < {MIN_WORDS})")
            skipped += 1
            continue
        if wc <= CHUNK_TARGET:
            eligible.append((fpath.stem, text, wc))
        else:
            chunks = chunk_text(text, CHUNK_TARGET)
            print(f"  CHUNK {fpath.name} ({wc:,} words -> {len(chunks)} chunks)")
            for ci, (chunk_text_str, chunk_wc) in enumerate(chunks, 1):
                if chunk_wc < MIN_WORDS:
                    print(f"    skip chunk {ci} ({chunk_wc} words < {MIN_WORDS})")
                    continue
                suffix = f"_part{ci}" if len(chunks) > 1 else ""
                eligible.append((f"{fpath.stem}{suffix}", chunk_text_str, chunk_wc))

    # Filter out already-completed items
    todo = [(f, t, w) for f, t, w in eligible if f not in completed]
    print(f"\n{len(eligible)} total chunks, {len(completed)} already done, {len(todo)} remaining\n")

    if not todo:
        print("Nothing to import — all chunks already completed.")
    else:
        parsed = 0
        ai_success = 0
        errors = 0
        total_words = 0

        for i, (fname, text, wc) in enumerate(todo, 1):
            if _shutdown:
                print(f"\n  >>> Stopped at {i}/{len(todo)}. Run again to resume.")
                break

            print(f"  [{i:3d}/{len(todo)}] {fname} ({wc:,} words)...", end=" ", flush=True)
            t0 = time.time()
            try:
                r = requests.post(
                    f"{API_BASE}/api/voice-profiles/{PROFILE_ID}/parse",
                    json={
                        "text": text,
                        "filename": fname,
                        "use_ai": True,
                    },
                    timeout=REQUEST_TIMEOUT,
                )
                elapsed = time.time() - t0
                if r.status_code == 200:
                    data = r.json()
                    ai_status = data.get("ai_extraction", {}).get("status", "unknown")
                    parsed += 1
                    total_words += wc
                    prompts = len(data.get("ai_extraction", {}).get("qualitative_prompts", []))
                    print(f"OK ({elapsed:.1f}s) AI:{ai_status} ({prompts} prompts)")
                    completed[fname] = {"status": "ok", "ai": ai_status, "prompts": prompts, "elapsed": round(elapsed, 1)}
                    failed.pop(fname, None)
                elif r.status_code == 409:
                    data = r.json()
                    print(f"DUP ({elapsed:.1f}s)")
                    completed[fname] = {"status": "dup", "elapsed": round(elapsed, 1)}
                    failed.pop(fname, None)
                else:
                    errors += 1
                    print(f"FAIL {r.status_code} ({elapsed:.1f}s): {r.text[:200]}")
                    failed[fname] = {"status": f"http_{r.status_code}", "elapsed": round(elapsed, 1), "error": r.text[:300]}
            except requests.exceptions.Timeout:
                errors += 1
                elapsed = time.time() - t0
                print(f"TIMEOUT ({elapsed:.1f}s)")
                failed[fname] = {"status": "timeout", "elapsed": round(elapsed, 1)}
            except Exception as e:
                errors += 1
                elapsed = time.time() - t0
                print(f"ERROR ({elapsed:.1f}s): {e}")
                failed[fname] = {"status": "error", "elapsed": round(elapsed, 1), "error": str(e)}

            # Save state after every item
            state["completed"] = completed
            state["failed"] = failed
            save_state(state)

            # Cooldown between calls to avoid rate limiting
            if not _shutdown and i < len(todo):
                time.sleep(COOLDOWN)

        print(f"\n{'='*60}")
        print(f"This run:")
        print(f"  Parsed: {parsed}/{len(todo)}")
        print(f"  AI extractions: {ai_success}/{parsed}" if parsed else "  AI extractions: 0")
        print(f"  Errors: {errors}")
        print(f"  Total words: {total_words:,}")
        print(f"Overall: {len(completed)}/{len(eligible)} completed, {len(failed)} failed")
        print(f"{'='*60}")

    if failed:
        print(f"\nFailed items ({len(failed)}):")
        for fname, info in failed.items():
            print(f"  {fname}: {info.get('status')} — {info.get('error', '')[:80]}")
        print(f"\nRe-run the script to retry failed items.")

    # 3. Export profile if fully complete
    if len(completed) >= len(eligible):
        print("\nAll chunks imported. Fetching final profile...")
        r = requests.get(f"{API_BASE}/api/voice-profiles/{PROFILE_ID}")
        if r.status_code != 200:
            print(f"FAILED to fetch profile: {r.status_code}")
            sys.exit(1)

        profile_data = r.json()
        elements = profile_data.get("elements", [])
        ai_count = sum(1 for info in completed.values() if info.get("ai") == "success")
        consolidated = profile_data.get("consolidated_ai_analysis")
        print(f"Total elements: {len(elements)}, parse_count: {profile_data.get('parse_count')}")
        print(f"Consolidated AI analysis: {'yes' if consolidated else 'no'}")

        prompts = profile_data.get("prompts", [])
        print(f"Prompts: {len(prompts)}")

        # Full round-trip export — everything needed to recreate the profile
        export = {
            "export_date": datetime.now(timezone.utc).isoformat(),
            "name": profile_data.get("name", ""),
            "description": profile_data.get("description", ""),
            "profile_type": profile_data.get("profile_type", ""),
            "parse_count": profile_data.get("parse_count", 0),
            "element_count": len(elements),
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
            "prompts": [
                {
                    "prompt_text": p.get("prompt_text", ""),
                    "sort_order": p.get("sort_order", i),
                }
                for i, p in enumerate(prompts)
            ],
        }

        # Include consolidated AI analysis if available
        if consolidated:
            export["consolidated_ai_analysis"] = consolidated

        EXPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(EXPORT_PATH, "w", encoding="utf-8") as f:
            json.dump(export, f, indent=4)
        print(f"Exported to {EXPORT_PATH}")

        # Clean up state file on full completion
        if STATE_FILE.exists():
            STATE_FILE.unlink()
            print("State file cleaned up.")
    else:
        remaining = len(eligible) - len(completed)
        print(f"\n{remaining} chunks remaining. Run again to continue.")

    save_state(state)


if __name__ == "__main__":
    main()
