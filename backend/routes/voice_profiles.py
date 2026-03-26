"""Voice profile management endpoints."""
from flask import Blueprint, request, jsonify

voice_profiles_bp = Blueprint("voice_profiles", __name__)


# ---------------------------------------------------------------------------
# Profile CRUD
# ---------------------------------------------------------------------------

@voice_profiles_bp.route("/voice-profiles", methods=["GET"])
def list_profiles():
    """List all voice profiles."""
    try:
        from db import get_conn
        from utils.voice_profile_service import VoiceProfileService
        with get_conn() as conn:
            svc = VoiceProfileService(conn)
            profiles = svc.list_profiles()
        return jsonify(profiles)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@voice_profiles_bp.route("/voice-profiles", methods=["POST"])
def create_profile():
    """Create a new voice profile."""
    data = request.get_json()
    if not data or "name" not in data:
        return jsonify({"error": "name is required"}), 400
    try:
        from db import get_conn
        from utils.voice_profile_service import VoiceProfileService
        with get_conn() as conn:
            svc = VoiceProfileService(conn)
            profile = svc.create_profile(
                name=data["name"],
                description=data.get("description", ""),
                profile_type=data.get("profile_type", "overlay"),
            )
        return jsonify(profile), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@voice_profiles_bp.route("/voice-profiles/<int:profile_id>", methods=["GET"])
def get_profile(profile_id):
    """Get a specific voice profile with elements and prompts."""
    try:
        from db import get_conn
        from utils.voice_profile_service import VoiceProfileService
        with get_conn() as conn:
            svc = VoiceProfileService(conn)
            profile = svc.get_profile(profile_id)
        if profile is None:
            return jsonify({"error": "Profile not found"}), 404
        return jsonify(profile)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@voice_profiles_bp.route("/voice-profiles/<int:profile_id>", methods=["PUT"])
def update_profile(profile_id):
    """Update profile metadata (name, description)."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No JSON body provided"}), 400
    try:
        from db import get_conn
        from utils.voice_profile_service import VoiceProfileService
        with get_conn() as conn:
            svc = VoiceProfileService(conn)
            profile = svc.get_profile_summary(profile_id)
            if profile is None:
                return jsonify({"error": "Profile not found"}), 404
            kwargs = {k: v for k, v in data.items() if k in ("name", "description", "profile_type", "is_active", "stack_order")}
            if not kwargs:
                return jsonify({"error": "No valid fields to update"}), 400
            svc.update_profile(profile_id, **kwargs)
            updated = svc.get_profile_summary(profile_id)
        return jsonify(updated)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@voice_profiles_bp.route("/voice-profiles/<int:profile_id>", methods=["DELETE"])
def delete_profile(profile_id):
    """Delete a voice profile."""
    try:
        from db import get_conn
        from utils.voice_profile_service import VoiceProfileService
        with get_conn() as conn:
            svc = VoiceProfileService(conn)
            profile = svc.get_profile_summary(profile_id)
            if profile is None:
                return jsonify({"error": "Profile not found"}), 404
            svc.delete_profile(profile_id)
        return jsonify({"status": "deleted", "id": profile_id})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ---------------------------------------------------------------------------
# Elements & Prompts
# ---------------------------------------------------------------------------

@voice_profiles_bp.route("/voice-profiles/<int:profile_id>/elements", methods=["GET"])
def get_elements(profile_id):
    """Get elements for a profile."""
    try:
        from db import get_conn
        from utils.voice_profile_service import VoiceProfileService
        with get_conn() as conn:
            svc = VoiceProfileService(conn)
            profile = svc.get_profile_summary(profile_id)
            if profile is None:
                return jsonify({"error": "Profile not found"}), 404
            elements = svc.get_elements(profile_id)
        return jsonify(elements)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@voice_profiles_bp.route("/voice-profiles/<int:profile_id>/elements", methods=["PUT"])
def update_elements(profile_id):
    """Update elements for a profile (JSON array)."""
    data = request.get_json()
    if data is None or not isinstance(data, list):
        return jsonify({"error": "Body must be a JSON array of elements"}), 400
    try:
        from db import get_conn
        from utils.voice_profile_service import VoiceProfileService
        with get_conn() as conn:
            svc = VoiceProfileService(conn)
            profile = svc.get_profile_summary(profile_id)
            if profile is None:
                return jsonify({"error": "Profile not found"}), 404
            svc.update_elements(profile_id, data)
            elements = svc.get_elements(profile_id)
        return jsonify(elements)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@voice_profiles_bp.route("/voice-profiles/<int:profile_id>/prompts", methods=["GET"])
def get_prompts(profile_id):
    """Get prompts for a profile."""
    try:
        from db import get_conn
        from utils.voice_profile_service import VoiceProfileService
        with get_conn() as conn:
            svc = VoiceProfileService(conn)
            profile = svc.get_profile_summary(profile_id)
            if profile is None:
                return jsonify({"error": "Profile not found"}), 404
            prompts = svc.get_prompts(profile_id)
        return jsonify(prompts)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@voice_profiles_bp.route("/voice-profiles/<int:profile_id>/prompts", methods=["PUT"])
def update_prompts(profile_id):
    """Update prompts for a profile (JSON array)."""
    data = request.get_json()
    if data is None or not isinstance(data, list):
        return jsonify({"error": "Body must be a JSON array of prompts"}), 400
    try:
        from db import get_conn
        from utils.voice_profile_service import VoiceProfileService
        with get_conn() as conn:
            svc = VoiceProfileService(conn)
            profile = svc.get_profile_summary(profile_id)
            if profile is None:
                return jsonify({"error": "Profile not found"}), 404
            svc.update_prompts(profile_id, data)
            prompts = svc.get_prompts(profile_id)
        return jsonify(prompts)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ---------------------------------------------------------------------------
# Parsing & Reset
# ---------------------------------------------------------------------------

@voice_profiles_bp.route("/voice-profiles/<int:profile_id>/parse", methods=["POST"])
def parse_text(profile_id):
    """Parse text into voice profile elements."""
    data = request.get_json()
    if not data or "text" not in data:
        return jsonify({"error": "text is required"}), 400
    try:
        from db import get_conn
        from utils.voice_profile_service import VoiceProfileService
        from utils.voice_generator import generate_voice_profile
        try:
            parse_result = generate_voice_profile(data["text"])
        except ValueError as ve:
            return jsonify({"error": str(ve)}), 400
        with get_conn() as conn:
            svc = VoiceProfileService(conn)
            profile = svc.get_profile_summary(profile_id)
            if profile is None:
                return jsonify({"error": "Profile not found"}), 404
            svc.apply_parse_results(profile_id, parse_result)
            elements = svc.get_elements(profile_id)
            updated = svc.get_profile_summary(profile_id)
        return jsonify({
            "elements": elements,
            "findings": list(parse_result.keys()),
            "parse_count": updated.get("parse_count", 0),
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@voice_profiles_bp.route("/voice-profiles/<int:profile_id>/reset", methods=["POST"])
def reset_corpus(profile_id):
    """Reset the corpus for a profile."""
    try:
        from db import get_conn
        from utils.voice_profile_service import VoiceProfileService
        with get_conn() as conn:
            svc = VoiceProfileService(conn)
            profile = svc.get_profile_summary(profile_id)
            if profile is None:
                return jsonify({"error": "Profile not found"}), 404
            svc.reset_corpus(profile_id)
        return jsonify({"status": "reset", "id": profile_id})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ---------------------------------------------------------------------------
# Snapshots
# ---------------------------------------------------------------------------

@voice_profiles_bp.route("/voice-profiles/<int:profile_id>/snapshots", methods=["GET"])
def list_snapshots(profile_id):
    """List snapshots for a profile."""
    try:
        from db import get_conn
        from utils.voice_profile_service import VoiceProfileService
        with get_conn() as conn:
            svc = VoiceProfileService(conn)
            profile = svc.get_profile_summary(profile_id)
            if profile is None:
                return jsonify({"error": "Profile not found"}), 404
            snapshots = svc.list_snapshots(profile_id)
        return jsonify(snapshots)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@voice_profiles_bp.route("/voice-profiles/<int:profile_id>/snapshots", methods=["POST"])
def save_snapshot(profile_id):
    """Save current profile state as a named snapshot."""
    data = request.get_json()
    if not data or not data.get("name"):
        return jsonify({"error": "name is required"}), 400
    try:
        from db import get_conn
        from utils.voice_profile_service import VoiceProfileService
        with get_conn() as conn:
            svc = VoiceProfileService(conn)
            profile = svc.get_profile_summary(profile_id)
            if profile is None:
                return jsonify({"error": "Profile not found"}), 404
            snap_id = svc.save_snapshot(profile_id, data["name"])
            snapshots = svc.list_snapshots(profile_id)
            snapshot = next((s for s in snapshots if s["id"] == snap_id), {"id": snap_id, "snapshot_name": data["name"]})
        return jsonify(snapshot), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@voice_profiles_bp.route("/voice-profiles/<int:profile_id>/snapshots/<int:snapshot_id>/load", methods=["POST"])
def load_snapshot(profile_id, snapshot_id):
    """Restore a snapshot."""
    try:
        from db import get_conn
        from utils.voice_profile_service import VoiceProfileService
        with get_conn() as conn:
            svc = VoiceProfileService(conn)
            profile = svc.get_profile_summary(profile_id)
            if profile is None:
                return jsonify({"error": "Profile not found"}), 404
            snapshots = svc.list_snapshots(profile_id)
            snap_ids = [s["id"] for s in snapshots]
            if snapshot_id not in snap_ids:
                return jsonify({"error": "Snapshot not found"}), 404
            svc.load_snapshot(profile_id, snapshot_id)
        return jsonify({"status": "loaded", "snapshot_id": snapshot_id})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@voice_profiles_bp.route("/voice-profiles/<int:profile_id>/snapshots/<int:snapshot_id>", methods=["DELETE"])
def delete_snapshot(profile_id, snapshot_id):
    """Delete a snapshot."""
    try:
        from db import get_conn
        from utils.voice_profile_service import VoiceProfileService
        with get_conn() as conn:
            svc = VoiceProfileService(conn)
            profile = svc.get_profile_summary(profile_id)
            if profile is None:
                return jsonify({"error": "Profile not found"}), 404
            snapshots = svc.list_snapshots(profile_id)
            snap_ids = [s["id"] for s in snapshots]
            if snapshot_id not in snap_ids:
                return jsonify({"error": "Snapshot not found"}), 404
            svc.delete_snapshot(snapshot_id)
        return jsonify({"status": "deleted", "snapshot_id": snapshot_id})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ---------------------------------------------------------------------------
# Export / Import
# ---------------------------------------------------------------------------

@voice_profiles_bp.route("/voice-profiles/<int:profile_id>/export", methods=["GET"])
def export_profile(profile_id):
    """Export a profile as JSON."""
    try:
        from db import get_conn
        from utils.voice_profile_service import VoiceProfileService
        with get_conn() as conn:
            svc = VoiceProfileService(conn)
            data = svc.export_profile(profile_id)
        return jsonify(data)
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@voice_profiles_bp.route("/voice-profiles/import", methods=["POST"])
def import_profile():
    """Import a profile from JSON body."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No JSON body provided"}), 400
    try:
        from db import get_conn
        from utils.voice_profile_service import VoiceProfileService
        with get_conn() as conn:
            svc = VoiceProfileService(conn)
            profile = svc.import_profile(data)
        return jsonify(profile), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ---------------------------------------------------------------------------
# Active Stack Configuration
# ---------------------------------------------------------------------------

@voice_profiles_bp.route("/voice-profiles/active", methods=["GET"])
def get_active_stack():
    """Get the resolved active voice profile stack."""
    try:
        from db import get_conn
        from utils.voice_profile_service import VoiceProfileService
        with get_conn() as conn:
            svc = VoiceProfileService(conn)
            stack = svc.get_active_stack()
        return jsonify(stack)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@voice_profiles_bp.route("/voice-profiles/active", methods=["PUT"])
def set_active_stack():
    """Set the active voice profile stack {baseline_id, overlay_ids}."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No JSON body provided"}), 400
    baseline_id = data.get("baseline_id")
    overlay_ids = data.get("overlay_ids", [])
    try:
        from db import get_conn
        from utils.voice_profile_service import VoiceProfileService
        with get_conn() as conn:
            svc = VoiceProfileService(conn)
            svc.set_active_stack(baseline_id, overlay_ids)
            stack = svc.get_active_stack()
        return jsonify(stack)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ---------------------------------------------------------------------------
# Style Guide (External Consumption)
# ---------------------------------------------------------------------------

@voice_profiles_bp.route("/style-guide", methods=["GET"])
def get_style_guide():
    """Get resolved active voice profile: weights + English instructions + prompts."""
    try:
        from db import get_conn
        from utils.voice_profile_service import VoiceProfileService
        from utils.weight_translator import translate_elements_to_english
        with get_conn() as conn:
            svc = VoiceProfileService(conn)
            stack = svc.get_active_stack()
        elements = stack.get("resolved_elements", [])
        english = translate_elements_to_english(elements)
        return jsonify({
            "baseline": stack.get("baseline"),
            "overlays": stack.get("overlays", []),
            "elements": elements,
            "english_instructions": english,
            "prompts": stack.get("prompts", []),
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@voice_profiles_bp.route("/style-guide/full", methods=["GET"])
def get_style_guide_full():
    """Get voice profile + rules config combined."""
    try:
        from db import get_conn
        from utils.voice_profile_service import VoiceProfileService
        from utils.weight_translator import translate_elements_to_english
        from utils.rules_config import rules_config
        with get_conn() as conn:
            svc = VoiceProfileService(conn)
            stack = svc.get_active_stack()
        elements = stack.get("resolved_elements", [])
        english = translate_elements_to_english(elements)
        return jsonify({
            "voice_profile": {
                "baseline": stack.get("baseline"),
                "overlays": stack.get("overlays", []),
                "elements": elements,
                "english_instructions": english,
                "prompts": stack.get("prompts", []),
            },
            "rules": {
                "heuristic_weights": rules_config.weights,
                "buzzwords": rules_config.buzzwords,
                "ai_phrases": rules_config.ai_phrases,
                "word_lists": rules_config.word_lists,
                "thresholds": rules_config.thresholds,
                "classification": rules_config.classification,
                "severity": rules_config.severity,
                "pipeline": rules_config.pipeline,
                "ai_prompt": rules_config.ai_prompt,
            },
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
