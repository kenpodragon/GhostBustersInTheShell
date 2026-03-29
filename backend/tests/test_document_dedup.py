"""Tests for document deduplication logic."""
import pytest
from utils.document_dedup import compute_content_hash, check_exact_duplicate, check_near_duplicate, count_same_filename


@pytest.fixture
def db_conn():
    """Set up a clean test DB state and tear down after each test."""
    import db as db_module
    from config import config

    # Initialize pool if not already done
    if db_module._pool is None:
        db_module.init_pool()

    # Clean up voice_corpus docs for test profiles (1, 17) before each test
    db_module.execute(
        "DELETE FROM documents WHERE voice_profile_id IN (1, 17) AND purpose = 'voice_corpus'"
    )
    yield db_module
    # Teardown: clean up after test
    db_module.execute(
        "DELETE FROM documents WHERE voice_profile_id IN (1, 17) AND purpose = 'voice_corpus'"
    )


class TestComputeContentHash:
    def test_basic_hash(self):
        h = compute_content_hash("Hello world")
        assert isinstance(h, str)
        assert len(h) == 64  # SHA-256 hex

    def test_normalizes_whitespace(self):
        h1 = compute_content_hash("Hello   world")
        h2 = compute_content_hash("Hello world")
        assert h1 == h2

    def test_normalizes_case(self):
        h1 = compute_content_hash("Hello World")
        h2 = compute_content_hash("hello world")
        assert h1 == h2

    def test_strips_leading_trailing(self):
        h1 = compute_content_hash("  Hello world  \n\n")
        h2 = compute_content_hash("Hello world")
        assert h1 == h2

    def test_different_content_different_hash(self):
        h1 = compute_content_hash("Hello world")
        h2 = compute_content_hash("Goodbye world")
        assert h1 != h2


class TestCheckExactDuplicate:
    def test_finds_exact_match(self, db_conn):
        """Insert a voice_corpus document, then check for its hash."""
        from db import execute
        content_hash = compute_content_hash("This is a test document for voice parsing.")
        execute(
            """INSERT INTO documents (filename, file_type, original_text, voice_profile_id, purpose, content_hash)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            ("test.txt", "text", "This is a test document for voice parsing.", 1, "voice_corpus", content_hash),
        )
        result = check_exact_duplicate(content_hash, profile_id=1)
        assert result is not None
        assert result["filename"] == "test.txt"

    def test_no_match_returns_none(self, db_conn):
        result = check_exact_duplicate("0000000000000000000000000000000000000000000000000000000000000000", profile_id=1)
        assert result is None

    def test_ignores_different_profile(self, db_conn):
        """Same hash but different profile should not match."""
        from db import execute
        content_hash = compute_content_hash("Unique text for profile isolation test.")
        execute(
            """INSERT INTO documents (filename, file_type, original_text, voice_profile_id, purpose, content_hash)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            ("other.txt", "text", "Unique text for profile isolation test.", 17, "voice_corpus", content_hash),
        )
        result = check_exact_duplicate(content_hash, profile_id=1)
        assert result is None


class TestCheckNearDuplicate:
    def test_finds_near_duplicate(self, db_conn):
        """Insert a doc, then check a slightly modified version."""
        from db import execute
        original = "A" * 500 + " some unique content here"
        execute(
            """INSERT INTO documents (filename, file_type, original_text, voice_profile_id, purpose, content_hash)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            ("essay.txt", "text", original, 1, "voice_corpus", compute_content_hash(original)),
        )
        # Near duplicate: same prefix, slightly different ending, similar length
        near_dup = "A" * 500 + " some unique content here!"
        result = check_near_duplicate(near_dup, profile_id=1)
        assert result is not None
        assert result["filename"] == "essay.txt"

    def test_no_near_duplicate(self, db_conn):
        result = check_near_duplicate("Completely different text that matches nothing.", profile_id=1)
        assert result is None


class TestCountSameFilename:
    def test_counts_matching_filenames(self, db_conn):
        from db import execute
        execute(
            """INSERT INTO documents (filename, file_type, original_text, voice_profile_id, purpose, content_hash)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            ("essay.txt", "text", "First version.", 1, "voice_corpus", compute_content_hash("First version.")),
        )
        execute(
            """INSERT INTO documents (filename, file_type, original_text, voice_profile_id, purpose, content_hash)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            ("essay.txt", "text", "Second version.", 1, "voice_corpus", compute_content_hash("Second version.")),
        )
        assert count_same_filename("essay.txt", 1) == 2

    def test_zero_when_no_match(self, db_conn):
        assert count_same_filename("nonexistent.txt", 1) == 0
