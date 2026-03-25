"""Rules configuration endpoints — config CRUD, snapshots, updates, version."""
import json
import gzip
import urllib.request
from flask import Blueprint, request, jsonify

rules_bp = Blueprint("rules", __name__)


# ---------------------------------------------------------------------------
# Config CRUD
# ---------------------------------------------------------------------------

@rules_bp.route("/rules/config", methods=["GET"])
def get_all_config():
    """Return all active (user) config sections."""
    from db import query_all

    rows = query_all(
        "SELECT section, config_data, updated_at FROM rule_configs WHERE is_default = false ORDER BY section"
    )
    result = {}
    for row in rows:
        result[row["section"]] = {
            "config_data": row["config_data"],
            "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
        }
    return jsonify(result)


@rules_bp.route("/rules/config/<section>", methods=["GET"])
def get_section_config(section):
    """Return a single section's config_data."""
    from utils.rules_config import SECTIONS

    if section not in SECTIONS:
        return jsonify({"error": f"Unknown section: {section}"}), 404

    from db import query_one

    row = query_one(
        "SELECT config_data, updated_at FROM rule_configs WHERE section = %s AND is_default = false",
        (section,),
    )
    if not row:
        return jsonify({"error": f"Section not found: {section}"}), 404

    return jsonify({
        "section": section,
        "config_data": row["config_data"],
        "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
    })


@rules_bp.route("/rules/config/<section>", methods=["PUT"])
def update_section_config(section):
    """Update a section's config_data and reload the singleton."""
    from utils.rules_config import SECTIONS, rules_config

    if section not in SECTIONS:
        return jsonify({"error": f"Unknown section: {section}"}), 404

    data = request.get_json()
    if data is None:
        return jsonify({"error": "No JSON body provided"}), 400

    config_data = data.get("config_data", data)

    from db import execute

    execute(
        """UPDATE rule_configs
           SET config_data = %s::jsonb, updated_at = CURRENT_TIMESTAMP
           WHERE section = %s AND is_default = false""",
        (json.dumps(config_data), section),
    )
    rules_config.reload()

    return jsonify({"status": "updated", "section": section})


@rules_bp.route("/rules/defaults", methods=["GET"])
def get_defaults():
    """Return all default config sections."""
    from db import query_all

    rows = query_all(
        "SELECT section, config_data, updated_at FROM rule_configs WHERE is_default = true ORDER BY section"
    )
    result = {}
    for row in rows:
        result[row["section"]] = {
            "config_data": row["config_data"],
            "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
        }
    return jsonify(result)


@rules_bp.route("/rules/revert", methods=["POST"])
def revert_to_defaults():
    """Copy all default rows into user rows, then reload config."""
    from db import execute
    from utils.rules_config import rules_config

    execute(
        """UPDATE rule_configs AS u
           SET config_data = d.config_data, updated_at = CURRENT_TIMESTAMP
           FROM rule_configs AS d
           WHERE d.section = u.section
             AND d.is_default = true
             AND u.is_default = false"""
    )
    rules_config.reload()

    return jsonify({"status": "reverted"})


# ---------------------------------------------------------------------------
# Snapshots
# ---------------------------------------------------------------------------

@rules_bp.route("/rules/snapshots", methods=["GET"])
def list_snapshots():
    """List saved snapshots."""
    from db import query_all

    rows = query_all(
        "SELECT id, name, created_at FROM config_snapshots ORDER BY created_at DESC"
    )
    result = []
    for row in rows:
        result.append({
            "id": row["id"],
            "name": row["name"],
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        })
    return jsonify(result)


@rules_bp.route("/rules/snapshots", methods=["POST"])
def save_snapshot():
    """Save current config as a named snapshot."""
    data = request.get_json()
    if not data or not data.get("name"):
        return jsonify({"error": "name is required"}), 400

    from db import query_all, get_cursor

    rows = query_all(
        "SELECT section, config_data FROM rule_configs WHERE is_default = false"
    )
    snapshot_data = {row["section"]: row["config_data"] for row in rows}

    with get_cursor() as cur:
        cur.execute(
            """INSERT INTO config_snapshots (name, snapshot_data)
               VALUES (%s, %s::jsonb) RETURNING id, created_at""",
            (data["name"], json.dumps(snapshot_data)),
        )
        new_row = cur.fetchone()

    return jsonify({
        "id": new_row["id"],
        "name": data["name"],
        "created_at": new_row["created_at"].isoformat() if new_row["created_at"] else None,
    }), 201


@rules_bp.route("/rules/snapshots/<int:snapshot_id>/load", methods=["POST"])
def load_snapshot(snapshot_id):
    """Load a snapshot into active config, then reload."""
    from db import query_one, get_cursor
    from utils.rules_config import rules_config

    row = query_one(
        "SELECT snapshot_data FROM config_snapshots WHERE id = %s",
        (snapshot_id,),
    )
    if not row:
        return jsonify({"error": "Snapshot not found"}), 404

    snapshot_data = row["snapshot_data"]

    with get_cursor() as cur:
        for section, config_data in snapshot_data.items():
            cur.execute(
                """UPDATE rule_configs
                   SET config_data = %s::jsonb, updated_at = CURRENT_TIMESTAMP
                   WHERE section = %s AND is_default = false""",
                (json.dumps(config_data), section),
            )

    rules_config.reload()
    return jsonify({"status": "loaded", "snapshot_id": snapshot_id})


@rules_bp.route("/rules/snapshots/<int:snapshot_id>", methods=["DELETE"])
def delete_snapshot(snapshot_id):
    """Delete a snapshot."""
    from db import execute

    deleted = execute(
        "DELETE FROM config_snapshots WHERE id = %s", (snapshot_id,)
    )
    if deleted == 0:
        return jsonify({"error": "Snapshot not found"}), 404

    return jsonify({"status": "deleted"})


# ---------------------------------------------------------------------------
# Updates
# ---------------------------------------------------------------------------

_GITHUB_BASE = "https://raw.githubusercontent.com/kenpodragon/GhostBustersInTheShell/main/backend/data/"


@rules_bp.route("/rules/updates/check", methods=["GET"])
def check_updates():
    """Check GitHub for a newer rules version."""
    from db import query_one
    from version import APP_VERSION

    row = query_one("SELECT rules_version FROM settings WHERE id = 1")
    current_version = row["rules_version"] if row else "unknown"

    try:
        url = _GITHUB_BASE + "rules_version.json"
        req = urllib.request.Request(url, headers={"User-Agent": "GhostBusters/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            remote = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        return jsonify({"error": f"Failed to check for updates: {e}"}), 502

    remote_version = remote.get("version", "unknown")
    min_app_version = remote.get("min_app_version", "0.0.0")
    changelog = remote.get("changelog", "")

    update_available = remote_version > current_version
    app_update_required = APP_VERSION < min_app_version

    return jsonify({
        "update_available": update_available,
        "current_version": current_version,
        "remote_version": remote_version,
        "changelog": changelog,
        "app_update_required": app_update_required,
    })


@rules_bp.route("/rules/updates/apply", methods=["POST"])
def apply_update():
    """Download rules_defaults.json.gz from GitHub, update default rows."""
    from db import get_cursor
    from utils.rules_config import SECTIONS, rules_config

    try:
        url = _GITHUB_BASE + "rules_defaults.json.gz"
        req = urllib.request.Request(url, headers={"User-Agent": "GhostBusters/1.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            compressed = resp.read()
        raw = gzip.decompress(compressed)
        data = json.loads(raw.decode("utf-8"))
    except Exception as e:
        return jsonify({"error": f"Failed to download update: {e}"}), 502

    version = data.get("version", "unknown")
    sections_data = data.get("sections", data)

    with get_cursor() as cur:
        for section_name in SECTIONS:
            config_data = sections_data.get(section_name, {})
            json_str = json.dumps(config_data)
            cur.execute(
                """UPDATE rule_configs
                   SET config_data = %s::jsonb, version = %s, updated_at = CURRENT_TIMESTAMP
                   WHERE section = %s AND is_default = true""",
                (json_str, version, section_name),
            )

        cur.execute(
            """UPDATE settings
               SET rules_version = %s,
                   rules_version_date = %s,
                   updated_at = CURRENT_TIMESTAMP
               WHERE id = 1""",
            (version, data.get("date", "")),
        )

    rules_config.reload()
    return jsonify({"status": "updated", "version": version})


# ---------------------------------------------------------------------------
# Version
# ---------------------------------------------------------------------------

@rules_bp.route("/version", methods=["GET"])
def get_version():
    """Return app and rules version info."""
    from db import query_one
    from version import APP_VERSION

    row = query_one("SELECT rules_version, rules_version_date FROM settings WHERE id = 1")

    return jsonify({
        "app_version": APP_VERSION,
        "rules_version": row["rules_version"] if row else "unknown",
        "rules_version_date": row["rules_version_date"] if row else None,
    })
