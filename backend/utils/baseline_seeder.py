"""Seed baseline voice profile from bundled JSON on startup."""
import json
import os

from db import query_one, execute


def seed_baseline_profile():
    """Import baseline voice profile if missing or outdated."""
    data_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "data"))
    version_file = os.path.join(data_dir, "baseline_voice_version.json")
    profile_file = os.path.join(data_dir, "baseline_voice_profile.json")

    if not os.path.exists(version_file) or not os.path.exists(profile_file):
        return

    try:
        with open(version_file, encoding="utf-8") as f:
            version_data = json.load(f)

        seed_version = version_data.get("version", "1.0.0")

        row = query_one(
            "SELECT baseline_version, active_baseline_id FROM settings WHERE id = 1"
        )
        current_version = row["baseline_version"] if row and row["baseline_version"] else "0.0.0"

        if current_version >= seed_version:
            return  # Already up to date

        with open(profile_file, encoding="utf-8") as f:
            profile_data = json.load(f)

        # Adapt export format to what import_profile expects
        import_data = {
            "name": profile_data.get("profile_name", profile_data.get("name", "Modern Human Baseline")),
            "description": f"System baseline voice profile — average of {profile_data.get('parse_count', 0)} human articles",
            "profile_type": "baseline",
            "parse_count": profile_data.get("parse_count", 0),
            "elements": profile_data.get("elements", []),
            "prompts": profile_data.get("prompts", []),
        }

        from utils.voice_profile_service import VoiceProfileService
        svc = VoiceProfileService()
        result = svc.import_profile(import_data)
        new_id = result["id"]

        execute(
            """UPDATE settings
               SET active_baseline_id = %s,
                   baseline_version = %s,
                   baseline_version_date = %s,
                   updated_at = CURRENT_TIMESTAMP
               WHERE id = 1""",
            (new_id, seed_version, version_data.get("date", "")),
        )

        print(f"[startup] Seeded baseline voice profile (id={new_id}, v{seed_version})")

    except Exception as e:
        print(f"[seed_baseline_profile] Warning: {e}")
