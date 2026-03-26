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

    # -------------------------------------------------------------------------
    # Profile CRUD
    # -------------------------------------------------------------------------

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

    # -------------------------------------------------------------------------
    # Task 3: Element & Prompt CRUD
    # -------------------------------------------------------------------------

    def get_elements(self, profile_id: int) -> list[dict]:
        """Public wrapper for _get_elements."""
        return self._get_elements(profile_id)

    def update_elements(self, profile_id: int, elements: list[dict]):
        """Update existing elements (by id) or upsert new ones (by name)."""
        with self.conn.cursor() as cur:
            for elem in elements:
                if "id" in elem and elem["id"] is not None:
                    # Update by id
                    allowed = {"name", "category", "element_type", "direction",
                               "weight", "target_value", "tags", "source"}
                    fields = {k: v for k, v in elem.items() if k in allowed}
                    if not fields:
                        continue
                    set_parts = []
                    vals = []
                    for k, v in fields.items():
                        if k == "tags":
                            set_parts.append(f"{k} = %s::jsonb")
                            vals.append(json.dumps(v, default=str))
                        else:
                            set_parts.append(f"{k} = %s")
                            vals.append(v)
                    set_clause = ", ".join(set_parts)
                    vals.append(elem["id"])
                    cur.execute(
                        f"UPDATE profile_elements SET {set_clause}, updated_at = NOW() WHERE id = %s",
                        vals,
                    )
                else:
                    # Upsert by name
                    self._upsert_element(cur, profile_id, elem)
        self.conn.commit()

    def add_element(self, profile_id: int, element: dict) -> int:
        """Add a single element with ON CONFLICT upsert. Returns the element id."""
        with self.conn.cursor() as cur:
            elem_id = self._upsert_element(cur, profile_id, element)
        self.conn.commit()
        return elem_id

    def delete_element(self, element_id: int):
        """Delete element by its id."""
        with self.conn.cursor() as cur:
            cur.execute("DELETE FROM profile_elements WHERE id = %s", (element_id,))
        self.conn.commit()

    def get_prompts(self, profile_id: int) -> list[dict]:
        """Public wrapper for _get_prompts."""
        return self._get_prompts(profile_id)

    def update_prompts(self, profile_id: int, prompts: list[dict]):
        """Delete-and-replace all prompts for a profile."""
        with self.conn.cursor() as cur:
            cur.execute("DELETE FROM profile_prompts WHERE voice_profile_id = %s", (profile_id,))
            for i, p in enumerate(prompts):
                sort_order = p.get("sort_order", i)
                cur.execute("""
                    INSERT INTO profile_prompts (voice_profile_id, prompt_text, sort_order)
                    VALUES (%s, %s, %s)
                """, (profile_id, p["prompt_text"], sort_order))
        self.conn.commit()

    # -------------------------------------------------------------------------
    # Task 4: Stack Resolution & Active Config
    # -------------------------------------------------------------------------

    def get_active_stack(self) -> dict:
        """Return active stack: baseline, overlays, resolved_elements, prompts."""
        with self.conn.cursor() as cur:
            cur.execute("SELECT active_baseline_id, active_overlay_ids FROM settings LIMIT 1")
            row = cur.fetchone()

        baseline_id = None
        overlay_ids = []
        if row:
            baseline_id = row[0]
            overlay_ids = row[1] if row[1] else []

        baseline = None
        if baseline_id:
            baseline = self.get_profile_summary(baseline_id)

        overlays = []
        for oid in overlay_ids:
            p = self.get_profile_summary(oid)
            if p:
                overlays.append(p)

        resolved_elements = []
        prompts = []
        if baseline_id:
            baseline_elements = self._get_elements(baseline_id)
            overlay_element_lists = [self._get_elements(oid) for oid in overlay_ids]
            resolved_elements = self._resolve_stack(baseline_elements, overlay_element_lists)
            prompts = self._get_prompts(baseline_id)
            for oid in overlay_ids:
                prompts.extend(self._get_prompts(oid))

        return {
            "baseline": baseline,
            "overlays": overlays,
            "resolved_elements": resolved_elements,
            "prompts": prompts,
        }

    def set_active_stack(self, baseline_id: int, overlay_ids: list[int] = None):
        """Update settings table with the active baseline and overlay ids."""
        if overlay_ids is None:
            overlay_ids = []
        with self.conn.cursor() as cur:
            # Reset all is_active flags
            cur.execute("UPDATE voice_profiles SET is_active = FALSE")
            # Set active flags
            if baseline_id:
                cur.execute(
                    "UPDATE voice_profiles SET is_active = TRUE WHERE id = %s",
                    (baseline_id,)
                )
            for oid in overlay_ids:
                cur.execute(
                    "UPDATE voice_profiles SET is_active = TRUE WHERE id = %s",
                    (oid,)
                )
            # Upsert settings row (singleton id=1)
            cur.execute("""
                INSERT INTO settings (id, active_baseline_id, active_overlay_ids)
                VALUES (1, %s, %s::jsonb)
                ON CONFLICT (id) DO UPDATE
                    SET active_baseline_id = EXCLUDED.active_baseline_id,
                        active_overlay_ids = EXCLUDED.active_overlay_ids
            """, (baseline_id, json.dumps(overlay_ids)))
        self.conn.commit()

    def _resolve_stack(self, baseline_elements: list[dict], overlay_element_lists: list[list[dict]]) -> list[dict]:
        """Overlay elements override baseline by name; unmatched baseline elements fall through."""
        resolved = {e["name"]: e.copy() for e in baseline_elements}
        for overlay_elements in overlay_element_lists:
            for elem in overlay_elements:
                resolved[elem["name"]] = elem.copy()
        return list(resolved.values())

    # -------------------------------------------------------------------------
    # Task 5: Snapshots, Export/Import, Reset
    # -------------------------------------------------------------------------

    def list_snapshots(self, profile_id: int) -> list[dict]:
        """Return snapshots for a profile ordered by created_at DESC."""
        with self.conn.cursor() as cur:
            cur.execute("""
                SELECT id, voice_profile_id, snapshot_name, created_at
                FROM profile_snapshots
                WHERE voice_profile_id = %s
                ORDER BY created_at DESC
            """, (profile_id,))
            cols = [d[0] for d in cur.description]
            rows = cur.fetchall()
        return [self._row_to_dict(cols, row) for row in rows]

    def save_snapshot(self, profile_id: int, name: str) -> int:
        """Save current elements + prompts + parse_count as a named snapshot. Returns snapshot id."""
        summary = self.get_profile_summary(profile_id)
        elements = self._get_elements(profile_id)
        prompts = self._get_prompts(profile_id)
        snapshot_data = {
            "parse_count": summary["parse_count"] if summary else 0,
            "elements": elements,
            "prompts": prompts,
        }
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO profile_snapshots (voice_profile_id, snapshot_name, snapshot_data)
                VALUES (%s, %s, %s::jsonb)
                RETURNING id
            """, (profile_id, name, json.dumps(snapshot_data, default=str)))
            snapshot_id = cur.fetchone()[0]
        self.conn.commit()
        return snapshot_id

    def load_snapshot(self, profile_id: int, snapshot_id: int):
        """Replace current elements and prompts from a saved snapshot."""
        with self.conn.cursor() as cur:
            cur.execute("""
                SELECT snapshot_data FROM profile_snapshots
                WHERE id = %s AND voice_profile_id = %s
            """, (snapshot_id, profile_id))
            row = cur.fetchone()
        if row is None:
            raise ValueError(f"Snapshot {snapshot_id} not found for profile {profile_id}")

        data = row[0]  # psycopg2 returns JSONB as dict already

        # Replace elements
        with self.conn.cursor() as cur:
            cur.execute("DELETE FROM profile_elements WHERE voice_profile_id = %s", (profile_id,))
            for elem in data.get("elements", []):
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
                    elem.get("weight"),
                    elem.get("target_value"),
                    json.dumps(elem.get("tags", []), default=str),
                    elem.get("source", "manual"),
                ))

            # Replace prompts
            cur.execute("DELETE FROM profile_prompts WHERE voice_profile_id = %s", (profile_id,))
            for p in data.get("prompts", []):
                cur.execute("""
                    INSERT INTO profile_prompts (voice_profile_id, prompt_text, sort_order)
                    VALUES (%s, %s, %s)
                """, (profile_id, p["prompt_text"], p.get("sort_order", 0)))

            # Restore parse_count
            parse_count = data.get("parse_count", 0)
            cur.execute(
                "UPDATE voice_profiles SET parse_count = %s WHERE id = %s",
                (parse_count, profile_id)
            )
        self.conn.commit()

    def delete_snapshot(self, snapshot_id: int):
        """Delete a snapshot by id."""
        with self.conn.cursor() as cur:
            cur.execute("DELETE FROM profile_snapshots WHERE id = %s", (snapshot_id,))
        self.conn.commit()

    def export_profile(self, profile_id: int) -> dict:
        """Export full profile as a JSON-serializable dict."""
        profile = self.get_profile(profile_id)
        if profile is None:
            raise ValueError(f"Profile {profile_id} not found")
        return {
            "name": profile["name"],
            "description": profile["description"],
            "profile_type": profile["profile_type"],
            "parse_count": profile["parse_count"],
            "elements": [
                {k: v for k, v in e.items()
                 if k in ("name", "category", "element_type", "direction",
                           "weight", "target_value", "tags", "source")}
                for e in profile["elements"]
            ],
            "prompts": [
                {"prompt_text": p["prompt_text"], "sort_order": p["sort_order"]}
                for p in profile["prompts"]
            ],
        }

    def import_profile(self, data: dict) -> dict:
        """Create a new profile from exported data. Returns the new profile summary."""
        profile = self.create_profile(
            name=data["name"],
            description=data.get("description", ""),
            profile_type=data.get("profile_type", "overlay"),
        )
        profile_id = profile["id"]

        # create_profile inserts starter elements — replace them with exported elements
        with self.conn.cursor() as cur:
            cur.execute("DELETE FROM profile_elements WHERE voice_profile_id = %s", (profile_id,))
            for elem in data.get("elements", []):
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
                    elem.get("weight"),
                    elem.get("target_value"),
                    json.dumps(elem.get("tags", []), default=str),
                    elem.get("source", "manual"),
                ))
            for p in data.get("prompts", []):
                cur.execute("""
                    INSERT INTO profile_prompts (voice_profile_id, prompt_text, sort_order)
                    VALUES (%s, %s, %s)
                """, (profile_id, p["prompt_text"], p.get("sort_order", 0)))
            parse_count = data.get("parse_count", 0)
            if parse_count:
                cur.execute(
                    "UPDATE voice_profiles SET parse_count = %s WHERE id = %s",
                    (parse_count, profile_id)
                )
        self.conn.commit()
        return self.get_profile_summary(profile_id)

    def reset_corpus(self, profile_id: int):
        """Delete parsed elements, re-insert starters if missing, reset parse_count to 0."""
        with self.conn.cursor() as cur:
            # Remove all parsed elements
            cur.execute(
                "DELETE FROM profile_elements WHERE voice_profile_id = %s AND source = 'parsed'",
                (profile_id,)
            )
            # Re-insert starters if missing
            for elem in self.STARTER_ELEMENTS:
                cur.execute("""
                    INSERT INTO profile_elements
                        (voice_profile_id, name, category, element_type, direction,
                         weight, target_value, tags, source)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s)
                    ON CONFLICT (voice_profile_id, name) DO NOTHING
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
            cur.execute(
                "UPDATE voice_profiles SET parse_count = 0 WHERE id = %s",
                (profile_id,)
            )
        self.conn.commit()

    # -------------------------------------------------------------------------
    # Task 6: Corpus Averaging
    # -------------------------------------------------------------------------

    def apply_parse_results(self, profile_id: int, parse_result: dict):
        """Average new parse results into existing element values.

        parse_result: dict[str, dict] where each value has:
            category, element_type, direction, weight, target_value, tags
        If parse_count == 0: first parse sets values directly.
        If parse_count > 0: new_avg = (old_avg * parse_count + new_value) / (parse_count + 1)
        """
        summary = self.get_profile_summary(profile_id)
        if summary is None:
            raise ValueError(f"Profile {profile_id} not found")
        parse_count = summary["parse_count"]

        existing = {e["name"]: e for e in self._get_elements(profile_id)}

        with self.conn.cursor() as cur:
            for name, new_data in parse_result.items():
                if parse_count == 0 or name not in existing:
                    # First parse or new element — set directly
                    new_weight = new_data.get("weight", 0.5)
                    new_target = new_data.get("target_value")
                else:
                    old = existing[name]
                    old_weight = old.get("weight") or 0.0
                    old_target = old.get("target_value")
                    new_weight_raw = new_data.get("weight", 0.5)
                    new_target_raw = new_data.get("target_value")

                    new_weight = (old_weight * parse_count + new_weight_raw) / (parse_count + 1)
                    if old_target is not None and new_target_raw is not None:
                        new_target = (old_target * parse_count + new_target_raw) / (parse_count + 1)
                    elif new_target_raw is not None:
                        new_target = new_target_raw
                    else:
                        new_target = old_target

                tags = new_data.get("tags", [])
                cur.execute("""
                    INSERT INTO profile_elements
                        (voice_profile_id, name, category, element_type, direction,
                         weight, target_value, tags, source)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb, 'parsed')
                    ON CONFLICT (voice_profile_id, name) DO UPDATE SET
                        weight = EXCLUDED.weight,
                        target_value = EXCLUDED.target_value,
                        direction = EXCLUDED.direction,
                        source = 'parsed',
                        updated_at = NOW()
                """, (
                    profile_id,
                    name,
                    new_data.get("category", "lexical"),
                    new_data.get("element_type", "directional"),
                    new_data.get("direction"),
                    new_weight,
                    new_target,
                    json.dumps(tags, default=str),
                ))

            cur.execute(
                "UPDATE voice_profiles SET parse_count = parse_count + 1 WHERE id = %s",
                (profile_id,)
            )
        self.conn.commit()

    # -------------------------------------------------------------------------
    # Private helpers
    # -------------------------------------------------------------------------

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

    def _upsert_element(self, cur, profile_id: int, elem: dict) -> int:
        """Insert or update an element by (voice_profile_id, name). Returns element id."""
        tags = elem.get("tags", [])
        cur.execute("""
            INSERT INTO profile_elements
                (voice_profile_id, name, category, element_type, direction,
                 weight, target_value, tags, source)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s)
            ON CONFLICT (voice_profile_id, name) DO UPDATE SET
                category = EXCLUDED.category,
                element_type = EXCLUDED.element_type,
                direction = EXCLUDED.direction,
                weight = EXCLUDED.weight,
                target_value = EXCLUDED.target_value,
                tags = EXCLUDED.tags,
                source = EXCLUDED.source,
                updated_at = NOW()
            RETURNING id
        """, (
            profile_id,
            elem["name"],
            elem.get("category", "lexical"),
            elem.get("element_type", "directional"),
            elem.get("direction"),
            elem.get("weight", 0.5),
            elem.get("target_value"),
            json.dumps(tags, default=str),
            elem.get("source", "manual"),
        ))
        return cur.fetchone()[0]

    @staticmethod
    def _row_to_dict(cols: list, row: tuple) -> dict:
        result = {}
        for col, val in zip(cols, row):
            if isinstance(val, datetime):
                result[col] = val.isoformat()
            else:
                result[col] = val
        return result
