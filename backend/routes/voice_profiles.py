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
    """Parse text into voice profile elements with optional AI extraction.

    Creates a document row (purpose='voice_corpus'), runs dedup check,
    parses with Python, optionally runs AI extraction, auto-consolidates.
    """
    data = request.get_json()
    if not data or "text" not in data:
        return jsonify({"error": "text is required"}), 400

    text = data["text"]
    filename = data.get("filename", "Untitled")
    use_ai = data.get("use_ai")
    force_near_duplicate = data.get("force_near_duplicate", False)

    try:
        from db import get_conn, execute, query_one
        from utils.voice_profile_service import VoiceProfileService
        from utils.voice_generator import generate_voice_profile
        from utils.document_dedup import compute_content_hash, check_exact_duplicate, check_near_duplicate, count_same_filename

        # --- Dedup check ---
        content_hash = compute_content_hash(text)

        exact = check_exact_duplicate(content_hash, profile_id)
        if exact:
            return jsonify({
                "error": f"This exact text was already parsed on {exact['created_at']} as '{exact['filename']}'.",
                "duplicate_type": "exact",
                "existing_document": {"id": exact["id"], "filename": exact["filename"], "created_at": str(exact["created_at"])},
            }), 409

        if not force_near_duplicate:
            near = check_near_duplicate(text, profile_id)
            if near:
                return jsonify({
                    "error": f"This appears very similar to '{near['filename']}' ({near['created_at']}). Set force_near_duplicate=true to parse anyway.",
                    "duplicate_type": "near",
                    "existing_document": {"id": near["id"], "filename": near["filename"], "created_at": str(near["created_at"])},
                    "similarity": near.get("similarity"),
                }), 409

        # --- Check same filename ---
        same_name_count = count_same_filename(filename, profile_id)
        same_name_warning = None
        if same_name_count > 0:
            same_name_warning = f"You have {same_name_count} other document(s) named '{filename}' in this corpus."

        # --- Create document row ---
        doc_row = query_one(
            """INSERT INTO documents (filename, file_type, original_text, voice_profile_id, purpose, content_hash)
               VALUES (%s, %s, %s, %s, %s, %s)
               RETURNING id, filename, created_at""",
            (filename, "text", text, profile_id, "voice_corpus", content_hash),
        )
        document_id = doc_row["id"]

        # --- Python parsing ---
        try:
            parse_result = generate_voice_profile(text)
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

        # --- AI extraction (optional) ---
        ai_extraction = {"status": "skipped"}
        from ai_providers.router import should_use_ai
        if should_use_ai(use_ai):
            from utils.ai_voice_extractor import extract_voice_with_ai
            ai_extraction = extract_voice_with_ai(text, parse_result)

            if ai_extraction["status"] == "success":
                import json as _json
                execute(
                    """INSERT INTO ai_parse_observations (profile_id, document_id, qualitative_prompts, metric_descriptions, discovered_patterns, raw_ai_response)
                       VALUES (%s, %s, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb)""",
                    (profile_id, document_id,
                     _json.dumps(ai_extraction["qualitative_prompts"]),
                     _json.dumps(ai_extraction["metric_descriptions"]),
                     _json.dumps(ai_extraction["discovered_patterns"]),
                     _json.dumps(ai_extraction["raw_ai_response"])),
                )

                # Auto-consolidate for single doc parse
                from utils.ai_consolidator import consolidate_observations
                consolidate_observations(profile_id)

        response = {
            "elements": elements,
            "findings": list(parse_result.keys()),
            "parse_count": updated.get("parse_count", 0),
            "document_id": document_id,
            "ai_extraction": {
                "status": ai_extraction["status"],
                "qualitative_prompts": ai_extraction.get("qualitative_prompts", []),
                "metric_descriptions": ai_extraction.get("metric_descriptions", []),
                "discovered_patterns": ai_extraction.get("discovered_patterns", []),
            },
        }
        if same_name_warning:
            response["same_name_warning"] = same_name_warning

        return jsonify(response)

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


@voice_profiles_bp.route("/voice-profiles/<int:profile_id>/samples", methods=["GET"])
def get_samples(profile_id):
    """Get sample texts from a profile's voice corpus documents."""
    limit = request.args.get("limit", 10, type=int)
    try:
        from db import query_all
        docs = query_all(
            """SELECT id AS document_id, filename,
                      LEFT(original_text, 5000) AS text_excerpt,
                      length(original_text) AS word_count,
                      created_at
               FROM documents
               WHERE voice_profile_id = %s AND purpose = 'voice_corpus'
               ORDER BY created_at DESC
               LIMIT %s""",
            (profile_id, limit),
        )
        return jsonify(docs)
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


# ---------------------------------------------------------------------------
# Reparse & Consolidate
# ---------------------------------------------------------------------------

@voice_profiles_bp.route("/voice-profiles/<int:profile_id>/reparse", methods=["POST"])
def reparse_corpus(profile_id):
    """Re-parse all corpus documents into a new profile version."""
    data = request.get_json() or {}
    use_ai = data.get("use_ai")
    try:
        from db import get_conn, query_all, query_one, execute
        from utils.voice_profile_service import VoiceProfileService
        from utils.voice_generator import generate_voice_profile
        import datetime

        with get_conn() as conn:
            svc = VoiceProfileService(conn)
            profile = svc.get_profile_summary(profile_id)
            if not profile:
                return jsonify({"error": "Profile not found"}), 404
            snapshot_name = f"Pre-reparse backup {datetime.date.today().isoformat()}"
            svc.save_snapshot(profile_id, snapshot_name)
            new_name = f"{profile['name']} (reparsed {datetime.date.today().isoformat()})"
            new_profile = svc.clone_profile(profile_id, new_name)
            new_id = new_profile["id"]

        corpus_docs = query_all(
            "SELECT id, original_text, filename FROM documents WHERE voice_profile_id = %s AND purpose = 'voice_corpus' ORDER BY created_at",
            (profile_id,),
        )

        parsed_count = 0
        errors = []
        for doc in corpus_docs:
            try:
                parse_result = generate_voice_profile(doc["original_text"])
                with get_conn() as conn:
                    svc = VoiceProfileService(conn)
                    svc.apply_parse_results(new_id, parse_result)
                parsed_count += 1

                from ai_providers.router import should_use_ai
                if should_use_ai(use_ai):
                    from utils.ai_voice_extractor import extract_voice_with_ai
                    import json as _json
                    ai_result = extract_voice_with_ai(doc["original_text"], parse_result)
                    if ai_result["status"] == "success":
                        execute(
                            """INSERT INTO ai_parse_observations (profile_id, document_id, qualitative_prompts, metric_descriptions, discovered_patterns, raw_ai_response)
                               VALUES (%s, %s, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb)""",
                            (new_id, doc["id"],
                             _json.dumps(ai_result["qualitative_prompts"]),
                             _json.dumps(ai_result["metric_descriptions"]),
                             _json.dumps(ai_result["discovered_patterns"]),
                             _json.dumps(ai_result["raw_ai_response"])),
                        )
            except Exception as e:
                errors.append({"document_id": doc["id"], "filename": doc["filename"], "error": str(e)})

        obs_count = query_one("SELECT COUNT(*) AS cnt FROM ai_parse_observations WHERE profile_id = %s", (new_id,))
        if obs_count and obs_count["cnt"] > 0:
            from utils.ai_consolidator import consolidate_observations
            consolidate_observations(new_id)

        with get_conn() as conn:
            svc = VoiceProfileService(conn)
            old_elements = svc.get_elements(profile_id)
            new_elements = svc.get_elements(new_id)

        return jsonify({
            "old_profile_id": profile_id,
            "new_profile_id": new_id,
            "parsed_count": parsed_count,
            "total_documents": len(corpus_docs),
            "errors": errors,
            "old_elements": old_elements,
            "new_elements": new_elements,
            "snapshot_name": snapshot_name,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@voice_profiles_bp.route("/voice-profiles/<int:profile_id>/reparse/accept", methods=["POST"])
def accept_reparse(profile_id):
    """Accept a reparsed profile, making it the active version."""
    data = request.get_json()
    if not data or "new_profile_id" not in data:
        return jsonify({"error": "new_profile_id is required"}), 400
    try:
        from db import get_conn
        from utils.voice_profile_service import VoiceProfileService
        with get_conn() as conn:
            svc = VoiceProfileService(conn)
            svc.accept_reparse(profile_id, data["new_profile_id"])
            new_profile = svc.get_profile(data["new_profile_id"])
        return jsonify(new_profile)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@voice_profiles_bp.route("/voice-profiles/<int:profile_id>/reparse/reject", methods=["POST"])
def reject_reparse(profile_id):
    """Reject a reparsed profile, deleting the new version."""
    data = request.get_json()
    if not data or "new_profile_id" not in data:
        return jsonify({"error": "new_profile_id is required"}), 400
    try:
        from db import get_conn
        from utils.voice_profile_service import VoiceProfileService
        with get_conn() as conn:
            svc = VoiceProfileService(conn)
            svc.reject_reparse(data["new_profile_id"])
        return jsonify({"status": "rejected", "deleted_profile_id": data["new_profile_id"]})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@voice_profiles_bp.route("/voice-profiles/<int:profile_id>/consolidate", methods=["POST"])
def consolidate(profile_id):
    """Consolidate AI observations for a profile."""
    try:
        from utils.ai_consolidator import consolidate_observations
        result = consolidate_observations(profile_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
