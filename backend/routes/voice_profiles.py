"""Voice profile management endpoints."""
from flask import Blueprint, request, jsonify

voice_profiles_bp = Blueprint("voice_profiles", __name__)


@voice_profiles_bp.route("/voice-profiles", methods=["GET"])
def list_profiles():
    """List all voice profiles."""
    from db import query_all
    profiles = query_all(
        "SELECT id, name, description, created_at FROM voice_profiles ORDER BY name"
    )
    return jsonify(profiles)


@voice_profiles_bp.route("/voice-profiles", methods=["POST"])
def create_profile():
    """Create a voice profile manually or from sample content."""
    data = request.get_json()
    if not data or "name" not in data:
        return jsonify({"error": "Provide 'name'"}), 400

    # If sample_content provided, generate voice rules from it
    if "sample_content" in data:
        from utils.voice_generator import generate_voice_profile
        rules = generate_voice_profile(data["sample_content"])
    else:
        rules = data.get("rules_json", "{}")

    from db import query_one
    profile = query_one(
        """INSERT INTO voice_profiles (name, description, rules_json, sample_content)
        VALUES (%s, %s, %s, %s) RETURNING id, name, description, created_at""",
        (data["name"], data.get("description", ""), rules, data.get("sample_content", ""))
    )
    return jsonify(profile), 201


@voice_profiles_bp.route("/voice-profiles/<int:profile_id>", methods=["GET"])
def get_profile(profile_id):
    """Get a specific voice profile with full rules."""
    from db import query_one
    profile = query_one("SELECT * FROM voice_profiles WHERE id = %s", (profile_id,))
    if not profile:
        return jsonify({"error": "Profile not found"}), 404
    return jsonify(profile)


@voice_profiles_bp.route("/voice-profiles/<int:profile_id>", methods=["PUT"])
def update_profile(profile_id):
    """Update a voice profile."""
    data = request.get_json()
    from db import query_one

    profile = query_one("SELECT id FROM voice_profiles WHERE id = %s", (profile_id,))
    if not profile:
        return jsonify({"error": "Profile not found"}), 404

    fields = []
    values = []
    for field in ["name", "description", "rules_json"]:
        if field in data:
            fields.append(f"{field} = %s")
            values.append(data[field])

    if not fields:
        return jsonify({"error": "No fields to update"}), 400

    values.append(profile_id)
    from db import execute
    execute(f"UPDATE voice_profiles SET {', '.join(fields)} WHERE id = %s", values)

    updated = query_one("SELECT * FROM voice_profiles WHERE id = %s", (profile_id,))
    return jsonify(updated)


@voice_profiles_bp.route("/voice-profiles/onboard", methods=["POST"])
def onboard_voice():
    """Generate a voice profile from writing samples.
    If preview_only=true, returns proposed rules without saving.
    """
    data = request.get_json()
    if not data or "sample_content" not in data:
        return jsonify({"error": "Provide 'sample_content'"}), 400

    content = data["sample_content"]
    word_count = len(content.split())
    if word_count < 500:
        return jsonify({
            "error": f"Need at least 500 words for voice profiling. Got {word_count}.",
            "recommendation": "Provide 2000+ words for best results."
        }), 400

    from utils.voice_generator import generate_voice_profile
    import json
    rules = generate_voice_profile(content)

    # Preview mode: return rules without saving
    if data.get("preview_only"):
        return jsonify({
            "rules": json.loads(rules) if isinstance(rules, str) else rules,
            "word_count": word_count,
        })

    # Normal mode: save to DB
    name = data.get("name", "Auto-generated Profile")
    from db import query_one
    profile = query_one(
        """INSERT INTO voice_profiles (name, description, rules_json, sample_content)
        VALUES (%s, %s, %s, %s) RETURNING id, name, description, created_at""",
        (name, f"Auto-generated from {word_count} words of sample content", rules, content)
    )
    return jsonify(profile), 201


@voice_profiles_bp.route("/voice-profiles/defaults", methods=["GET"])
def get_defaults():
    """Return the default voice guide rules for comparison."""
    from db import query_all
    rules = query_all(
        "SELECT * FROM voice_rules WHERE voice_profile_id = 1 ORDER BY part, id"
    )
    return jsonify({"rules": rules, "profile_name": "Default - Anti-AI Voice Guide"})


@voice_profiles_bp.route("/voice-profiles/<int:profile_id>/preview", methods=["POST"])
def preview_profile(profile_id):
    """Run sample AI text through a profile's rules, return before/after."""
    data = request.get_json()
    if not data or "text" not in data:
        return jsonify({"error": "Provide 'text' to preview"}), 400

    from db import query_one
    profile = query_one("SELECT * FROM voice_profiles WHERE id = %s", (profile_id,))
    if not profile:
        return jsonify({"error": "Profile not found"}), 404

    from utils.detector import detect_ai_patterns
    from utils.voice_checker import check_voice_compliance

    analysis = detect_ai_patterns(data["text"])
    voice_check = check_voice_compliance(data["text"], profile_id)

    return jsonify({
        "score": analysis.get("overall_score", 0),
        "classification": analysis.get("classification"),
        "patterns": analysis.get("patterns", []),
        "voice_violations": voice_check.get("violations", []),
    })
