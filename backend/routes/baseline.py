"""Baseline voice profile update check and apply endpoints."""
import json
import urllib.request
from flask import Blueprint, jsonify

from db import query_one, execute
from utils.voice_profile_service import VoiceProfileService

baseline_bp = Blueprint("baseline", __name__)

_GITHUB_BASE = (
    "https://raw.githubusercontent.com/kenpodragon/GhostBustersInTheShell/"
    "main/backend/data/"
)


def _fetch_github_json(filename: str) -> dict:
    """Fetch a JSON file from the GitHub repo."""
    url = _GITHUB_BASE + filename
    req = urllib.request.Request(url, headers={"User-Agent": "GhostBusters/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


@baseline_bp.route("/baseline/updates/check", methods=["GET"])
def check_for_updates():
    """Check GitHub for a newer baseline voice profile version."""
    row = query_one("SELECT baseline_version FROM settings WHERE id = 1")
    current = row["baseline_version"] if row and row["baseline_version"] else "0.0.0"

    try:
        remote = _fetch_github_json("baseline_voice_version.json")
    except Exception as e:
        return jsonify({"error": f"Failed to check for updates: {e}"}), 502

    remote_version = remote.get("version", "0.0.0")

    if current >= remote_version:
        return jsonify({
            "status": "up_to_date",
            "current_version": current,
            "remote_version": remote_version,
        })

    from version import APP_VERSION
    min_app = remote.get("min_app_version", "0.0.0")
    app_update_required = APP_VERSION < min_app

    return jsonify({
        "status": "update_available",
        "current_version": current,
        "remote_version": remote_version,
        "remote_date": remote.get("date"),
        "changelog": remote.get("changelog", ""),
        "min_app_version": min_app,
        "app_version": APP_VERSION,
        "app_update_required": app_update_required,
    })


@baseline_bp.route("/baseline/updates/apply", methods=["POST"])
def apply_update():
    """Download baseline voice profile from GitHub and import it."""
    try:
        version_data = _fetch_github_json("baseline_voice_version.json")
        profile_data = _fetch_github_json("baseline_voice_profile.json")
    except Exception as e:
        return jsonify({"error": f"Failed to download update: {e}"}), 502

    # Adapt export format to import format
    import_data = {
        "name": profile_data.get("profile_name", profile_data.get("name", "Modern Human Baseline")),
        "description": "System baseline voice profile",
        "profile_type": "baseline",
        "parse_count": profile_data.get("parse_count", 0),
        "elements": profile_data.get("elements", []),
        "prompts": profile_data.get("prompts", []),
    }

    svc = VoiceProfileService()
    result = svc.import_profile(import_data)
    new_id = result["id"]

    version = version_data.get("version", "unknown")
    execute(
        """UPDATE settings
           SET active_baseline_id = %s,
               baseline_version = %s,
               baseline_version_date = %s,
               updated_at = CURRENT_TIMESTAMP
           WHERE id = 1""",
        (new_id, version, version_data.get("date", "")),
    )

    return jsonify({"success": True, "version": version, "baseline_id": new_id})
