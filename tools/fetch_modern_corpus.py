"""Fetch modern human-written text corpus from diverse web sources.

Sources:
- Wikipedia API (random articles, plain text)
- RSS feeds (news, tech, opinion)
- trafilatura for clean article extraction

Outputs raw .txt files to local_data/modern_human_td/
Target: ~500K words from diverse modern US sources.
"""

import os
import re
import sys
import json
import time
import hashlib
import argparse
from urllib.parse import urlparse

import requests
import feedparser
import trafilatura

OUTPUT_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "local_data", "modern_human_td"
)

# Browser-like User-Agent to avoid 403s
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
}

# --- Source definitions ---

RSS_FEEDS = {
    # News
    "npr": "https://feeds.npr.org/1001/rss.xml",
    "pbs": "https://www.pbs.org/newshour/feeds/rss/headlines",
    "ap_top": "https://feedx.net/rss/ap.xml",
    "reuters": "https://feedx.net/rss/reuters.xml",
    "bbc": "https://feeds.bbci.co.uk/news/rss.xml",
    # Tech
    "arstechnica": "https://feeds.arstechnica.com/arstechnica/features",
    "theverge": "https://www.theverge.com/rss/index.xml",
    "wired": "https://www.wired.com/feed/rss",
    # Opinion / culture
    "theatlantic": "https://www.theatlantic.com/feed/all/",
    "salon": "https://www.salon.com/feed/",
    # Dev / tech blogs
    "devto": "https://dev.to/feed",
    "hackernoon": "https://hackernoon.com/feed",
}

# Wikipedia categories for diverse topics
WIKI_CATEGORIES = [
    "Science", "Technology", "History", "Philosophy", "Psychology",
    "Economics", "Literature", "Music", "Sports", "Politics",
    "Medicine", "Education", "Geography", "Art", "Law",
]


def _safe_filename(text: str, max_len: int = 80) -> str:
    """Create a safe filename from text."""
    clean = re.sub(r"[^\w\s-]", "", text)
    clean = re.sub(r"\s+", "_", clean.strip())
    return clean[:max_len]


def _word_count(text: str) -> int:
    return len(text.split())


def _save_article(source: str, title: str, text: str, stats: dict) -> bool:
    """Save article text to file. Returns True if saved."""
    wc = _word_count(text)
    if wc < 200:
        stats["skipped_short"] += 1
        return False

    # Deduplicate by content hash
    content_hash = hashlib.md5(text[:500].encode()).hexdigest()[:10]
    safe_title = _safe_filename(title)
    filename = f"{source}_{safe_title}_{content_hash}.txt"
    filepath = os.path.join(OUTPUT_DIR, filename)

    if os.path.exists(filepath):
        stats["skipped_dupe"] += 1
        return False

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(text)

    stats["saved"] += 1
    stats["total_words"] += wc
    return True


def fetch_wikipedia(target_words: int = 200000, stats: dict = None):
    """Fetch random Wikipedia articles via API."""
    print(f"\n=== WIKIPEDIA (target: {target_words:,} words) ===")
    api_url = "https://en.wikipedia.org/w/api.php"
    words_collected = 0
    articles_fetched = 0
    batch_size = 20  # articles per API call

    consecutive_errors = 0
    max_errors = 5

    while words_collected < target_words:
        # Get random article titles
        try:
            resp = requests.get(api_url, params={
                "action": "query",
                "list": "random",
                "rnlimit": batch_size,
                "rnnamespace": 0,
                "format": "json",
            }, headers=HEADERS, timeout=15)
            if resp.status_code == 429:
                wait = min(60, 5 * (consecutive_errors + 1))
                print(f"  Rate limited, waiting {wait}s...")
                time.sleep(wait)
                consecutive_errors += 1
                if consecutive_errors >= max_errors:
                    print(f"  Too many rate limits, stopping Wikipedia at {words_collected:,} words")
                    break
                continue
            resp.raise_for_status()
            titles = [r["title"] for r in resp.json()["query"]["random"]]
            consecutive_errors = 0
        except Exception as e:
            print(f"  Error fetching random titles: {e}")
            consecutive_errors += 1
            if consecutive_errors >= max_errors:
                print(f"  Too many errors, stopping Wikipedia at {words_collected:,} words")
                break
            time.sleep(5)
            continue

        # Fetch plain text for each
        for title in titles:
            if words_collected >= target_words:
                break
            try:
                resp = requests.get(api_url, params={
                    "action": "query",
                    "titles": title,
                    "prop": "extracts",
                    "explaintext": True,
                    "exsectionformat": "plain",
                    "format": "json",
                }, headers=HEADERS, timeout=15)
                resp.raise_for_status()
                pages = resp.json()["query"]["pages"]
                for page_id, page in pages.items():
                    text = page.get("extract", "")
                    if not text or _word_count(text) < 200:
                        continue

                    # Clean up Wikipedia formatting artifacts
                    text = re.sub(r"\n{3,}", "\n\n", text)
                    text = re.sub(r"== .+ ==", "", text)  # section headers
                    text = text.strip()

                    if _save_article("wiki", title, text, stats):
                        wc = _word_count(text)
                        words_collected += wc
                        articles_fetched += 1
                        if articles_fetched % 10 == 0:
                            print(f"  {articles_fetched} articles, {words_collected:,} words")

            except Exception as e:
                continue

            time.sleep(0.2)  # Be polite to Wikipedia API

    print(f"  Done: {articles_fetched} articles, {words_collected:,} words")


def fetch_rss_feeds(target_words: int = 200000, stats: dict = None):
    """Fetch articles from RSS feeds using trafilatura for extraction."""
    print(f"\n=== RSS FEEDS (target: {target_words:,} words) ===")
    words_collected = 0
    articles_fetched = 0

    for source_name, feed_url in RSS_FEEDS.items():
        if words_collected >= target_words:
            break

        print(f"\n  [{source_name}] Fetching feed...")
        try:
            feed = feedparser.parse(feed_url)
            entries = feed.entries[:30]  # Max 30 per feed
            print(f"  [{source_name}] Found {len(entries)} entries")
        except Exception as e:
            print(f"  [{source_name}] Feed error: {e}")
            continue

        for entry in entries:
            if words_collected >= target_words:
                break

            url = entry.get("link", "")
            title = entry.get("title", "untitled")

            if not url:
                continue

            try:
                # Use trafilatura for clean article extraction
                downloaded = trafilatura.fetch_url(url)
                if not downloaded:
                    continue

                text = trafilatura.extract(
                    downloaded,
                    include_comments=False,
                    include_tables=False,
                    no_fallback=False,
                )

                if not text:
                    continue

                if _save_article(source_name, title, text, stats):
                    wc = _word_count(text)
                    words_collected += wc
                    articles_fetched += 1

            except Exception as e:
                continue

            time.sleep(0.5)  # Be polite

        print(f"  [{source_name}] Total so far: {articles_fetched} articles, {words_collected:,} words")

    print(f"\n  RSS Done: {articles_fetched} articles, {words_collected:,} words")


def fetch_devto_api(target_words: int = 50000, stats: dict = None):
    """Fetch articles from dev.to API (no scraping needed)."""
    print(f"\n=== DEV.TO API (target: {target_words:,} words) ===")
    words_collected = 0
    articles_fetched = 0
    page = 1

    while words_collected < target_words and page <= 10:
        try:
            resp = requests.get(
                "https://dev.to/api/articles",
                params={"per_page": 30, "page": page, "top": 30},
                headers=HEADERS,
                timeout=15,
            )
            resp.raise_for_status()
            articles = resp.json()
        except Exception as e:
            print(f"  Error: {e}")
            break

        for article in articles:
            if words_collected >= target_words:
                break

            article_id = article.get("id")
            title = article.get("title", "untitled")

            try:
                # Get full article with body
                detail_resp = requests.get(
                    f"https://dev.to/api/articles/{article_id}",
                    headers=HEADERS,
                    timeout=15,
                )
                detail_resp.raise_for_status()
                body_html = detail_resp.json().get("body_html", "")

                if not body_html:
                    continue

                # Extract text from HTML
                text = trafilatura.extract(
                    body_html,
                    include_comments=False,
                    include_tables=False,
                )

                if not text:
                    # Fallback: strip HTML tags
                    from bs4 import BeautifulSoup
                    text = BeautifulSoup(body_html, "html.parser").get_text(separator="\n")

                if text and _save_article("devto", title, text.strip(), stats):
                    wc = _word_count(text)
                    words_collected += wc
                    articles_fetched += 1

            except Exception:
                continue

            time.sleep(0.3)

        page += 1

    print(f"  Done: {articles_fetched} articles, {words_collected:,} words")


def get_current_stats() -> tuple[int, int]:
    """Count existing files and words in output directory."""
    if not os.path.isdir(OUTPUT_DIR):
        return 0, 0
    files = [f for f in os.listdir(OUTPUT_DIR) if f.endswith(".txt")]
    total_words = 0
    for f in files:
        with open(os.path.join(OUTPUT_DIR, f), "r", encoding="utf-8", errors="replace") as fh:
            total_words += _word_count(fh.read())
    return len(files), total_words


def main():
    parser = argparse.ArgumentParser(description="Fetch modern human text corpus")
    parser.add_argument("--target", type=int, default=500000, help="Target word count")
    parser.add_argument("--wiki-only", action="store_true", help="Only fetch Wikipedia")
    parser.add_argument("--rss-only", action="store_true", help="Only fetch RSS feeds")
    parser.add_argument("--devto-only", action="store_true", help="Only fetch dev.to")
    args = parser.parse_args()

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    existing_files, existing_words = get_current_stats()
    print(f"Existing corpus: {existing_files} files, {existing_words:,} words")
    print(f"Target: {args.target:,} words")

    remaining = max(0, args.target - existing_words)
    if remaining == 0:
        print("Target already met!")
        return

    print(f"Need: {remaining:,} more words\n")

    stats = {"saved": 0, "skipped_short": 0, "skipped_dupe": 0, "total_words": 0}

    run_all = not (args.wiki_only or args.rss_only or args.devto_only)

    # Allocate words across sources
    if run_all:
        wiki_target = int(remaining * 0.50)  # 50% Wikipedia
        rss_target = int(remaining * 0.35)   # 35% RSS/news
        devto_target = int(remaining * 0.15) # 15% dev blogs
    else:
        wiki_target = rss_target = devto_target = remaining

    if run_all or args.wiki_only:
        fetch_wikipedia(wiki_target, stats)

    if run_all or args.rss_only:
        fetch_rss_feeds(rss_target, stats)

    if run_all or args.devto_only:
        fetch_devto_api(devto_target, stats)

    # Final stats
    final_files, final_words = get_current_stats()
    print(f"\n{'='*60}")
    print("CORPUS COLLECTION SUMMARY")
    print(f"{'='*60}")
    print(f"Articles saved this run: {stats['saved']}")
    print(f"Words collected this run: {stats['total_words']:,}")
    print(f"Skipped (too short): {stats['skipped_short']}")
    print(f"Skipped (duplicate): {stats['skipped_dupe']}")
    print(f"\nTotal corpus: {final_files} files, {final_words:,} words")
    print(f"Target: {args.target:,} words")
    print(f"{'REACHED' if final_words >= args.target else f'SHORT by {args.target - final_words:,} words'}")
    print(f"Output: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
