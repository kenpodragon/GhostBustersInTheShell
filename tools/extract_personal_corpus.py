"""Extract article body content from HTML files and prepare personal corpus.

Handles:
- LinkedIn article HTML exports (extracts <p>, <h2> text from <div> blocks)
- Plain .txt files (passed through with optional Gutenberg header stripping)

Outputs cleaned .txt files to local_data/corpus/personal/ ready for voice parsing.
"""

import os
import re
import sys
from html.parser import HTMLParser


PERSONAL_SRC = os.path.join(
    os.path.dirname(__file__), "..", "..", "local_data", "test_corpus", "personal"
)
PERSONAL_OUT = os.path.join(
    os.path.dirname(__file__), "..", "..", "local_data", "corpus", "personal"
)


class LinkedInArticleExtractor(HTMLParser):
    """Extract article body text from LinkedIn HTML exports.

    Collects text from <p>, <h2>, <h3> tags inside <div> blocks,
    skipping metadata (series-title, series-description, created, published).
    """

    SKIP_CLASSES = {"created", "published", "series-title", "series-description"}
    CONTENT_TAGS = {"p", "h2", "h3", "li", "blockquote"}

    def __init__(self):
        super().__init__()
        self.title = ""
        self.paragraphs = []
        self._current_tag = None
        self._current_class = ""
        self._in_title = False
        self._in_content_tag = False
        self._buffer = ""
        self._past_metadata = False  # Skip everything before first <div>
        self._in_div = False
        self._div_depth = 0

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        cls = attrs_dict.get("class", "")

        if tag == "h1":
            self._in_title = True
            self._buffer = ""

        if tag == "div":
            self._in_div = True
            self._div_depth += 1
            self._past_metadata = True

        if self._in_div and tag in self.CONTENT_TAGS and cls not in self.SKIP_CLASSES:
            self._in_content_tag = True
            self._buffer = ""
            self._current_tag = tag

    def handle_endtag(self, tag):
        if tag == "h1" and self._in_title:
            self._in_title = False
            self.title = self._buffer.strip()

        if tag == "div":
            self._div_depth -= 1
            if self._div_depth <= 0:
                self._in_div = False
                self._div_depth = 0

        if self._in_content_tag and tag == self._current_tag:
            self._in_content_tag = False
            text = self._buffer.strip()
            if text and not self._is_url_only(text):
                if tag == "h2":
                    self.paragraphs.append(f"\n{text}\n")
                else:
                    self.paragraphs.append(text)

    def handle_data(self, data):
        if self._in_title:
            self._buffer += data
        if self._in_content_tag:
            self._buffer += data

    def _is_url_only(self, text: str) -> bool:
        """Skip paragraphs that are just URLs."""
        return bool(re.match(r"^https?://\S+$", text.strip()))

    def get_article_text(self) -> str:
        """Return cleaned article text."""
        return "\n\n".join(self.paragraphs)


def extract_html(filepath: str) -> tuple[str, str]:
    """Extract title and body text from a LinkedIn HTML article.

    Returns:
        (title, body_text)
    """
    with open(filepath, "r", encoding="utf-8") as f:
        html = f.read()

    parser = LinkedInArticleExtractor()
    parser.feed(html)
    return parser.title, parser.get_article_text()


def extract_txt(filepath: str) -> tuple[str, str]:
    """Read a plain text file, using filename as title.

    Returns:
        (title, body_text)
    """
    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        text = f.read()

    title = os.path.splitext(os.path.basename(filepath))[0]
    return title, text.strip()


def process_all():
    """Process all files in the personal source directory."""
    os.makedirs(PERSONAL_OUT, exist_ok=True)

    if not os.path.isdir(PERSONAL_SRC):
        print(f"ERROR: Source directory not found: {PERSONAL_SRC}")
        return

    files = sorted(os.listdir(PERSONAL_SRC))
    html_count = 0
    txt_count = 0
    total_words = 0
    results = []

    for filename in files:
        filepath = os.path.join(PERSONAL_SRC, filename)
        if not os.path.isfile(filepath):
            continue

        ext = os.path.splitext(filename)[1].lower()

        if ext in (".html", ".htm"):
            title, body = extract_html(filepath)
            html_count += 1
        elif ext == ".txt":
            title, body = extract_txt(filepath)
            txt_count += 1
        else:
            print(f"  Skipping: {filename} (unsupported type)")
            continue

        if not body or len(body.split()) < 50:
            print(f"  Skipping: {filename} (too short: {len(body.split())} words)")
            continue

        # Write cleaned text
        out_name = re.sub(r"[^\w\s-]", "", os.path.splitext(filename)[0])
        out_name = re.sub(r"\s+", "_", out_name.strip()) + ".txt"
        out_path = os.path.join(PERSONAL_OUT, out_name)

        with open(out_path, "w", encoding="utf-8") as f:
            if title:
                f.write(f"{title}\n\n")
            f.write(body)

        word_count = len(body.split())
        total_words += word_count
        results.append({
            "source": filename,
            "output": out_name,
            "title": title[:60] if title else "(no title)",
            "words": word_count,
        })
        print(f"  {filename} -> {out_name} ({word_count:,} words)")

    print(f"\n{'='*60}")
    print(f"EXTRACTION SUMMARY")
    print(f"{'='*60}")
    print(f"HTML articles extracted: {html_count}")
    print(f"TXT files copied:       {txt_count}")
    print(f"Total files output:     {len(results)}")
    print(f"Total words:            {total_words:,}")
    print(f"Output directory:       {PERSONAL_OUT}")

    return results


if __name__ == "__main__":
    print("Extracting personal corpus...\n")
    process_all()
