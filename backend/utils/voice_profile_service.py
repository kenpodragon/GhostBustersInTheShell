"""VoiceProfileService — CRUD for voice profiles, elements, and prompts."""
import json
from datetime import datetime


class VoiceProfileService:
    STARTER_ELEMENTS = [
        {"name": "contraction_rate", "category": "lexical", "element_type": "directional", "direction": "more", "weight": 0.5, "tags": ["python-extractable"], "source": "manual"},
        {"name": "avg_sentence_length", "category": "syntactic", "element_type": "metric", "target_value": 15.0, "weight": 0.5, "tags": ["python-extractable"], "source": "manual"},
        {"name": "em_dash_usage", "category": "idiosyncratic", "element_type": "directional", "direction": "more", "weight": 0.5, "tags": ["python-extractable", "punctuation"], "source": "manual"},
        {"name": "flesch_kincaid_grade", "category": "idiosyncratic", "element_type": "metric", "target_value": 8.0, "weight": 0.5, "tags": ["python-extractable", "readability"], "source": "manual"},
        {"name": "passive_voice_rate", "category": "syntactic", "element_type": "directional", "direction": "less", "weight": 0.5, "tags": ["python-extractable"], "source": "manual"},
    ]

    def __init__(self, conn):
        self.conn = conn

    def list_profiles(self) -> list[dict]:
        """Return summary info for all profiles, ordered baseline first then by name."""
        with self.conn.cursor() as cur:
            cur.execute("""
                SELECT id, name, description, profile_type, parse_count,
                       is_active, stack_order, created_at, updated_at
                FROM voice_profiles
                ORDER BY
                    CASE profile_type WHEN 'baseline' THEN 0 ELSE 1 END,
                    name
            """)
            cols = [d[0] for d in cur.description]
            rows = cur.fetchall()
        return [self._row_to_dict(cols, row) for row in rows]

    def create_profile(self, name: str, description: str = "", profile_type: str = "overlay") -> dict:
        """Create a profile with starter elements. Returns summary dict."""
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO voice_profiles (name, description, profile_type)
                VALUES (%s, %s, %s)
                RETURNING id, name, description, profile_type, parse_count,
                          is_active, stack_order, created_at, updated_at
            """, (name, description, profile_type))
            cols = [d[0] for d in cur.description]
            row = cur.fetchone()
            profile = self._row_to_dict(cols, row)
            profile_id = profile["id"]

            for elem in self.STARTER_ELEMENTS:
                cur.execute("""
                    INSERT INTO profile_elements
                        (voice_profile_id, name, category, element_type, direction,
                         weight, target_value, tags, source)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s)
                """, (
                    profile_id,
                    elem["name"],
                    elem["category"],
                    elem["element_type"],
                    elem.get("direction"),
                    elem.get("weight", 0.5),
                    elem.get("target_value"),
                    json.dumps(elem.get("tags", [])),
                    elem.get("source", "manual"),
                ))

        self.conn.commit()
        return profile

    def get_profile_summary(self, profile_id: int) -> dict | None:
        """Return metadata only (no elements/prompts)."""
        with self.conn.cursor() as cur:
            cur.execute("""
                SELECT id, name, description, profile_type, parse_count,
                       is_active, stack_order, created_at, updated_at
                FROM voice_profiles
                WHERE id = %s
            """, (profile_id,))
            cols = [d[0] for d in cur.description]
            row = cur.fetchone()
        if row is None:
            return None
        return self._row_to_dict(cols, row)

    def get_profile(self, profile_id: int) -> dict | None:
        """Return full profile with elements and prompts."""
        summary = self.get_profile_summary(profile_id)
        if summary is None:
            return None
        summary["elements"] = self._get_elements(profile_id)
        summary["prompts"] = self._get_prompts(profile_id)
        return summary

    def update_profile(self, profile_id: int, **kwargs):
        """Update allowed fields: name, description, profile_type, is_active, stack_order."""
        allowed = {"name", "description", "profile_type", "is_active", "stack_order"}
        fields = {k: v for k, v in kwargs.items() if k in allowed}
        if not fields:
            return
        set_clause = ", ".join(f"{k} = %s" for k in fields)
        values = list(fields.values()) + [profile_id]
        with self.conn.cursor() as cur:
            cur.execute(
                f"UPDATE voice_profiles SET {set_clause}, updated_at = NOW() WHERE id = %s",
                values,
            )
        self.conn.commit()

    def delete_profile(self, profile_id: int):
        """Delete profile. CASCADE handles elements, prompts, and snapshots."""
        with self.conn.cursor() as cur:
            cur.execute("DELETE FROM voice_profiles WHERE id = %s", (profile_id,))
        self.conn.commit()

    def _get_elements(self, profile_id: int) -> list[dict]:
        with self.conn.cursor() as cur:
            cur.execute("""
                SELECT id, voice_profile_id, name, category, element_type,
                       direction, weight, target_value, tags, source, created_at, updated_at
                FROM profile_elements
                WHERE voice_profile_id = %s
                ORDER BY name
            """, (profile_id,))
            cols = [d[0] for d in cur.description]
            rows = cur.fetchall()
        return [self._row_to_dict(cols, row) for row in rows]

    def _get_prompts(self, profile_id: int) -> list[dict]:
        with self.conn.cursor() as cur:
            cur.execute("""
                SELECT id, voice_profile_id, prompt_text, sort_order, created_at, updated_at
                FROM profile_prompts
                WHERE voice_profile_id = %s
                ORDER BY sort_order, id
            """, (profile_id,))
            cols = [d[0] for d in cur.description]
            rows = cur.fetchall()
        return [self._row_to_dict(cols, row) for row in rows]

    @staticmethod
    def _row_to_dict(cols: list, row: tuple) -> dict:
        result = {}
        for col, val in zip(cols, row):
            if isinstance(val, datetime):
                result[col] = val.isoformat()
            else:
                result[col] = val
        return result
