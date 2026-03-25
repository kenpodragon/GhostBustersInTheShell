"""RulesConfig singleton — central config for all heuristic code.

Usage:
    from utils.rules_config import rules_config
    rules_config.load()
    weight = rules_config.weights["sentence_opener_pos"]
"""

import gzip
import json
import os
import threading

SECTIONS = [
    "heuristic_weights", "buzzwords", "ai_phrases", "word_lists",
    "thresholds", "classification", "severity", "pipeline", "ai_prompt",
]

_GZ_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "rules_defaults.json.gz")


class RulesConfig:
    """Singleton holding all detection rule configuration."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._loaded = False
        self._is_read_only = False
        self.weights: dict = {}
        self.buzzwords: dict = {}
        self.ai_phrases: dict = {}
        self.word_lists: dict = {}
        self.thresholds: dict = {}
        self.classification: dict = {}
        self.severity: dict = {}
        self.pipeline: dict = {}
        self.ai_prompt: str = ""

    # -- properties --

    @property
    def all_buzzwords(self) -> set:
        """Flat set of all buzzword categories combined (verbs + adj + filler, NOT phrases)."""
        result: set = set()
        for cat in ("hard_ban_verbs", "hard_ban_adj", "hard_ban_filler"):
            result.update(self.buzzwords.get(cat, []))
        return result

    @property
    def hard_ban_filler_phrases(self) -> list:
        """Convenience accessor for the phrases list."""
        return self.buzzwords.get("hard_ban_filler_phrases", [])

    @property
    def is_read_only(self) -> bool:
        return self._is_read_only

    # -- loading --

    def load(self):
        """Try DB first, fall back to gz file."""
        try:
            self.load_from_db()
            return
        except Exception:
            pass

        self.load_from_file()

    def load_from_db(self):
        """Read all is_default=false rows from rule_configs table."""
        from db import query_all  # late import to avoid circular deps

        rows = query_all(
            "SELECT section, config_data FROM rule_configs WHERE is_default = false"
        )
        if not rows:
            raise ValueError("No custom config rows in DB")

        sections_data = {row["section"]: row["config_data"] for row in rows}
        with self._lock:
            self._apply_sections(sections_data)
        self._is_read_only = False
        self._loaded = True

    def load_from_file(self):
        """Read from backend/data/rules_defaults.json.gz."""
        gz_path = os.path.normpath(_GZ_PATH)
        with gzip.open(gz_path, "rt", encoding="utf-8") as f:
            data = json.load(f)

        sections_data = data.get("sections", data)
        with self._lock:
            self._apply_sections(sections_data)
        self._is_read_only = True
        self._loaded = True

    def reload(self):
        """Re-read from DB (no-op if read-only)."""
        if self._is_read_only:
            return
        self.load_from_db()

    def seed_db(self):
        """If rule_configs table is empty, load gz file and insert rows.

        Each section is inserted twice: once as is_default=true and once as
        is_default=false.  Also updates the settings table with version info.
        """
        from db import query_one, get_cursor  # late import

        count_row = query_one("SELECT count(*) AS cnt FROM rule_configs")
        if count_row and count_row["cnt"] > 0:
            return  # already seeded

        gz_path = os.path.normpath(_GZ_PATH)
        with gzip.open(gz_path, "rt", encoding="utf-8") as f:
            data = json.load(f)

        version = data.get("version", "unknown")
        sections_data = data.get("sections", data)

        with get_cursor() as cur:
            for section_name in SECTIONS:
                config_data = sections_data.get(section_name, {})
                json_str = json.dumps(config_data)
                for is_default in (True, False):
                    cur.execute(
                        """INSERT INTO rule_configs (section, config_data, is_default, version)
                           VALUES (%s, %s::jsonb, %s, %s)
                           ON CONFLICT (section, is_default) DO UPDATE
                           SET config_data = EXCLUDED.config_data,
                               version = EXCLUDED.version,
                               updated_at = CURRENT_TIMESTAMP""",
                        (section_name, json_str, is_default, version),
                    )

            # Update settings table with version info
            cur.execute(
                """UPDATE settings
                   SET rules_version = %s,
                       rules_version_date = %s,
                       updated_at = CURRENT_TIMESTAMP
                   WHERE id = 1""",
                (version, data.get("date", "2026-03-25")),
            )

    # -- internals --

    def _apply_sections(self, sections: dict):
        """Apply a dict of section_name -> config_data to attributes."""
        self.weights = sections.get("heuristic_weights", {})
        self.buzzwords = sections.get("buzzwords", {})
        self.ai_phrases = sections.get("ai_phrases", {})
        self.word_lists = sections.get("word_lists", {})
        self.thresholds = sections.get("thresholds", {})
        self.classification = sections.get("classification", {})
        self.severity = sections.get("severity", {})
        self.pipeline = sections.get("pipeline", {})
        self.ai_prompt = sections.get("ai_prompt", "")

    def _reset_for_testing(self):
        """Reset singleton state for testing. Not for production use."""
        self._loaded = False
        self._is_read_only = False
        self.weights = {}
        self.buzzwords = {}
        self.ai_phrases = {}
        self.word_lists = {}
        self.thresholds = {}
        self.classification = {}
        self.severity = {}
        self.pipeline = {}
        self.ai_prompt = ""


# Module-level singleton
rules_config = RulesConfig()
