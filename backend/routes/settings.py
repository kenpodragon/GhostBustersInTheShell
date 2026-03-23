"""Settings endpoints - AI provider config and preferences."""
from flask import Blueprint, request, jsonify

settings_bp = Blueprint("settings", __name__)


@settings_bp.route("/settings", methods=["GET"])
def get_settings():
    """Get current settings including AI status."""
    from db import query_one
    from ai_providers.router import get_ai_status

    row = query_one("SELECT ai_enabled, ai_provider, preferences, updated_at FROM settings WHERE id = 1")
    if not row:
        return jsonify({"error": "Settings not initialized"}), 500

    settings = dict(row)
    settings["updated_at"] = settings["updated_at"].isoformat() if settings["updated_at"] else None
    # Merge in runtime AI status
    settings.update(get_ai_status())
    return jsonify(settings)


@settings_bp.route("/settings", methods=["PATCH"])
def update_settings():
    """Update settings. Allowed fields: ai_enabled, ai_provider."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    allowed = {"ai_enabled", "ai_provider"}
    updates = {k: v for k, v in data.items() if k in allowed}
    if not updates:
        return jsonify({"error": f"No valid fields. Allowed: {allowed}"}), 400

    from db import execute, query_one

    set_clauses = []
    params = []
    for key, value in updates.items():
        set_clauses.append(f"{key} = %s")
        params.append(value)
    set_clauses.append("updated_at = CURRENT_TIMESTAMP")

    sql = f"UPDATE settings SET {', '.join(set_clauses)} WHERE id = 1"
    execute(sql, params)

    # If ai_enabled changed, re-run health check
    if "ai_enabled" in updates:
        from ai_providers.router import startup_health_check
        startup_health_check()

    # Return updated settings
    return get_settings()


@settings_bp.route("/settings/test-ai", methods=["POST"])
def test_ai():
    """Test AI provider connection and return health info."""
    from ai_providers.router import _get_provider, _get_settings

    settings = _get_settings()
    provider = _get_provider(settings.get("ai_provider"))
    if not provider:
        return jsonify({
            "available": False,
            "error": f"Provider '{settings.get('ai_provider')}' not found or CLI not installed",
        })

    health = provider.health_check()
    return jsonify(health)
