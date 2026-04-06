"""VoiceProfileService — CRUD for voice profiles, elements, and prompts."""
import json
from datetime import datetime

import psycopg2.extras

from utils.style_brief import generate_style_brief


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
                       is_active, stack_order, consolidated_ai_analysis,
                       created_at, updated_at
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
        """Delete profile and all dependent data."""
        with self.conn.cursor() as cur:
            cur.execute("DELETE FROM document_elements WHERE document_id IN (SELECT id FROM documents WHERE voice_profile_id = %s)", (profile_id,))
            cur.execute("DELETE FROM ai_parse_observations WHERE document_id IN (SELECT id FROM documents WHERE voice_profile_id = %s)", (profile_id,))
            cur.execute("DELETE FROM documents WHERE voice_profile_id = %s", (profile_id,))
            cur.execute("DELETE FROM element_convergence WHERE profile_id = %s", (profile_id,))
            cur.execute("DELETE FROM profile_snapshots WHERE voice_profile_id = %s", (profile_id,))
            cur.execute("DELETE FROM profile_prompts WHERE voice_profile_id = %s", (profile_id,))
            cur.execute("DELETE FROM profile_elements WHERE voice_profile_id = %s", (profile_id,))
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
    # Convergence tracking
    # -------------------------------------------------------------------------

    def update_convergence(self, profile_id: int, document_id: int,
                           parse_result: dict, word_count: int):
        """Update convergence tracking after a document is parsed."""
        from utils.convergence_tracker import ElementTracker, COMPLETENESS_TIERS

        cur = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # 1. Get current total_words_parsed
        cur.execute("SELECT total_words_parsed FROM voice_profiles WHERE id = %s", (profile_id,))
        row = cur.fetchone()
        total_words = (row["total_words_parsed"] or 0) + word_count if row else word_count

        # 2. Store per-document element values + update convergence
        newly_converged = []

        for el_name, el_data in parse_result.items():
            weight = el_data.get("weight", 0)

            # Insert into document_elements
            cur.execute(
                """INSERT INTO document_elements (profile_id, document_id, element_name, value)
                   VALUES (%s, %s, %s, %s)
                   ON CONFLICT (profile_id, document_id, element_name)
                   DO UPDATE SET value = EXCLUDED.value""",
                (profile_id, document_id, el_name, float(weight)),
            )

            # Load or create tracker
            cur.execute(
                """SELECT element_name, running_mean, running_count, rolling_delta,
                          cv, m2, consecutive_stable, converged, converged_at_words
                   FROM element_convergence
                   WHERE profile_id = %s AND element_name = %s""",
                (profile_id, el_name),
            )
            existing = cur.fetchone()

            if existing:
                # Map DB column names to ElementTracker.from_dict keys
                tracker_data = {
                    "name": existing["element_name"],
                    "count": existing["running_count"],
                    "mean": existing["running_mean"],
                    "m2": existing["m2"],
                    "rolling_delta": existing["rolling_delta"],
                    "consecutive_stable": existing["consecutive_stable"],
                    "converged": existing["converged"],
                    "converged_at_words": existing["converged_at_words"],
                }
                tracker = ElementTracker.from_dict(tracker_data)
                was_converged = tracker.converged
            else:
                tracker = ElementTracker(el_name)
                was_converged = False

            tracker.update(float(weight), total_words)

            if tracker.converged and not was_converged:
                newly_converged.append(el_name)

            # Upsert convergence state
            state = tracker.to_dict()
            cur.execute(
                """INSERT INTO element_convergence
                   (profile_id, element_name, running_mean, running_count,
                    rolling_delta, cv, m2, consecutive_stable, converged, converged_at_words)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                   ON CONFLICT (profile_id, element_name)
                   DO UPDATE SET
                    running_mean = EXCLUDED.running_mean,
                    running_count = EXCLUDED.running_count,
                    rolling_delta = EXCLUDED.rolling_delta,
                    cv = EXCLUDED.cv,
                    m2 = EXCLUDED.m2,
                    consecutive_stable = EXCLUDED.consecutive_stable,
                    converged = EXCLUDED.converged,
                    converged_at_words = EXCLUDED.converged_at_words""",
                (profile_id, state["name"], state["mean"],
                 state["count"], state["rolling_delta"], tracker.cv,
                 state["m2"], state["consecutive_stable"], state["converged"],
                 state["converged_at_words"]),
            )

        # 3. Recompute completeness
        cur.execute(
            "SELECT element_name, converged FROM element_convergence WHERE profile_id = %s",
            (profile_id,),
        )
        rows = cur.fetchall()
        total_el = len(rows)
        converged_el = sum(1 for r in rows if r["converged"])
        pct = round(converged_el / total_el * 100) if total_el > 0 else 0

        tier = None
        for tier_name in ("gold", "silver", "bronze"):
            if pct >= COMPLETENESS_TIERS[tier_name]:
                tier = tier_name
                break

        cur.execute(
            """UPDATE voice_profiles
               SET total_words_parsed = %s, completeness_pct = %s, completeness_tier = %s
               WHERE id = %s""",
            (total_words, pct, tier, profile_id),
        )

        self.conn.commit()
        cur.close()
        return {
            "newly_converged": newly_converged,
            "completeness_pct": pct,
            "completeness_tier": tier,
            "total_words": total_words,
            "elements_converged": converged_el,
            "elements_total": total_el,
        }

    def get_completeness(self, profile_id: int) -> dict:
        """Get full completeness data for a profile."""
        from utils.convergence_tracker import (
            ElementTracker, ConvergenceComputer,
            STARTER_WORD_GATE, get_starter_guidance, TIER_GUIDANCE,
        )

        cur = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        cur.execute(
            "SELECT total_words_parsed, completeness_pct, completeness_tier FROM voice_profiles WHERE id = %s",
            (profile_id,),
        )
        profile = cur.fetchone()
        if not profile:
            cur.close()
            return {"error": "Profile not found"}

        total_words = profile["total_words_parsed"] or 0

        cur.execute(
            """SELECT element_name, running_mean, running_count, rolling_delta,
                      cv, m2, consecutive_stable, converged, converged_at_words
               FROM element_convergence WHERE profile_id = %s""",
            (profile_id,),
        )
        rows = cur.fetchall()
        cur.close()

        if not rows:
            from utils.convergence_tracker import get_starter_milestone
            starter_progress = get_starter_milestone(total_words)
            guidance = get_starter_guidance(starter_progress["milestone"])
            return {
                "tier": "starter",
                "tier_label": f"Starter {starter_progress['milestone_label']}" if starter_progress["milestone_label"] else "Starter",
                "pct": 0,
                "total_words": total_words,
                "elements_converged": 0,
                "elements_total": 0,
                "categories": {},
                "starter_progress": starter_progress,
                "guidance": guidance,
                "words_to_next_tier": f"~{max(0, STARTER_WORD_GATE - total_words):,}",
                "next_tier": "bronze",
                "next_tier_label": "Bronze",
            }

        cc = ConvergenceComputer()
        for row in rows:
            tracker_data = {
                "name": row["element_name"],
                "count": row["running_count"],
                "mean": row["running_mean"],
                "m2": row["m2"],
                "rolling_delta": row["rolling_delta"],
                "consecutive_stable": row["consecutive_stable"],
                "converged": row["converged"],
                "converged_at_words": row["converged_at_words"],
            }
            tracker = ElementTracker.from_dict(tracker_data)
            cc.add_tracker(tracker)

        result = cc.compute_completeness(total_words=total_words)
        result["total_words"] = total_words

        # Guidance text
        if result["tier"] == "starter":
            milestone = result.get("starter_progress", {}).get("milestone", 0)
            result["guidance"] = get_starter_guidance(milestone)
        else:
            result["guidance"] = TIER_GUIDANCE.get(result["tier"], "")

        # Word estimates for next tier (research-derived)
        TIER_WORD_ESTIMATES = {"bronze": 20000, "silver": 175000, "gold": 350000}
        next_tier = result.get("next_tier")
        if next_tier and next_tier in TIER_WORD_ESTIMATES:
            target = TIER_WORD_ESTIMATES[next_tier]
            result["words_to_next_tier"] = f"~{max(0, target - total_words):,}"
        else:
            result["words_to_next_tier"] = None

        return result

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
            consolidated = data.get("consolidated_ai_analysis")
            if parse_count or consolidated:
                sets = []
                vals = []
                if parse_count:
                    sets.append("parse_count = %s")
                    vals.append(parse_count)
                if consolidated:
                    sets.append("consolidated_ai_analysis = %s::jsonb")
                    vals.append(json.dumps(consolidated))
                vals.append(profile_id)
                cur.execute(
                    f"UPDATE voice_profiles SET {', '.join(sets)} WHERE id = %s",
                    vals,
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

    def get_voice_style_prompt(self, baseline_id: int = None, overlay_ids: list[int] = None) -> dict:
        """Return the voice style prompt string for injection into other tools."""
        if baseline_id is not None:
            profile = self.get_profile_summary(baseline_id)
            if not profile:
                raise ValueError(f"Voice profile not found: {baseline_id}")
            elements = self._get_elements(baseline_id)
            prompts = self._get_prompts(baseline_id)
            profile_name = profile.get("name", f"Profile {baseline_id}")

            if overlay_ids:
                for oid in overlay_ids:
                    overlay_elements = self._get_elements(oid)
                    overlay_prompts = self._get_prompts(oid)
                    overlay_names = {e["name"] for e in overlay_elements}
                    elements = [e for e in elements if e["name"] not in overlay_names] + overlay_elements
                    prompts = prompts + overlay_prompts
        else:
            stack = self.get_active_stack()
            if not stack.get("baseline"):
                raise ValueError("No active voice profile. Provide baseline_id or set an active profile.")
            elements = stack["resolved_elements"]
            prompts = stack["prompts"]
            profile_name = stack["baseline"].get("name", "Unknown")

        brief = generate_style_brief(
            mode="voice",
            voice_elements=elements,
            voice_prompts=prompts,
        )

        clean_prompt = brief.replace("{text}", "").strip()
        while "\n\n\n" in clean_prompt:
            clean_prompt = clean_prompt.replace("\n\n\n", "\n\n")

        prompt_count = sum(1 for p in prompts if p.get("prompt_text"))
        return {
            "prompt": clean_prompt,
            "profile_name": profile_name,
            "element_count": len(elements),
            "prompt_count": prompt_count,
        }

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

    # -------------------------------------------------------------------------
    # Task 8: Reparse helpers
    # -------------------------------------------------------------------------

    def clone_profile(self, profile_id: int, new_name: str) -> dict:
        """Clone a profile with fresh elements (parse_count=0). Returns the new profile summary."""
        original = self.get_profile_summary(profile_id)
        if not original:
            raise ValueError(f"Profile {profile_id} not found")
        new_profile = self.create_profile(
            name=new_name,
            description=original.get("description", ""),
            profile_type=original.get("profile_type", "baseline"),
        )
        return new_profile

    def accept_reparse(self, old_profile_id: int, new_profile_id: int):
        """Accept a reparsed profile: make new active, archive old, transfer corpus doc links."""
        with self.conn.cursor() as cur:
            cur.execute(
                "UPDATE documents SET voice_profile_id = %s WHERE voice_profile_id = %s AND purpose = 'voice_corpus'",
                (new_profile_id, old_profile_id),
            )
            cur.execute(
                "UPDATE ai_parse_observations SET profile_id = %s WHERE profile_id = %s",
                (new_profile_id, old_profile_id),
            )
            cur.execute(
                "UPDATE voice_profiles SET is_active = FALSE WHERE id = %s",
                (old_profile_id,),
            )
            cur.execute(
                "UPDATE voice_profiles SET is_active = TRUE WHERE id = %s",
                (new_profile_id,),
            )
        self.conn.commit()

    def reject_reparse(self, new_profile_id: int):
        """Reject a reparsed profile: delete the new profile and all its data."""
        with self.conn.cursor() as cur:
            cur.execute("DELETE FROM ai_parse_observations WHERE profile_id = %s", (new_profile_id,))
            cur.execute("DELETE FROM profile_prompts WHERE voice_profile_id = %s", (new_profile_id,))
            cur.execute("DELETE FROM profile_elements WHERE voice_profile_id = %s", (new_profile_id,))
            cur.execute("DELETE FROM voice_profiles WHERE id = %s", (new_profile_id,))
        self.conn.commit()

    # -------------------------------------------------------------------------
    # Private helpers
    # -------------------------------------------------------------------------

    @staticmethod
    def _row_to_dict(cols: list, row: tuple) -> dict:
        result = {}
        for col, val in zip(cols, row):
            if isinstance(val, datetime):
                result[col] = val.isoformat()
            else:
                result[col] = val
        return result
