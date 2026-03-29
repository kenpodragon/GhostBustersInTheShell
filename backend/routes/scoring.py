"""Voice fidelity scoring endpoints."""
from flask import Blueprint, request, jsonify

scoring_bp = Blueprint("scoring", __name__)


@scoring_bp.route("/score-fidelity", methods=["POST"])
def score_fidelity():
    """Score how closely generated text matches a voice profile.

    Request: {generated_text, profile_id, mode: quantitative|qualitative|both, sample_text?}
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "JSON body required"}), 400

    generated_text = data.get("generated_text")
    if not generated_text:
        return jsonify({"error": "generated_text is required"}), 400

    profile_id = data.get("profile_id")
    if not profile_id:
        return jsonify({"error": "profile_id is required"}), 400

    mode = data.get("mode", "quantitative")
    if mode not in ("quantitative", "qualitative", "both"):
        return jsonify({"error": f"mode must be quantitative, qualitative, or both — got '{mode}'"}), 400

    sample_text = data.get("sample_text")

    try:
        from db import get_conn, query_all
        from utils.voice_profile_service import VoiceProfileService
        from utils.voice_fidelity_scorer import score_fidelity as do_score

        with get_conn() as conn:
            svc = VoiceProfileService(conn)
            profile = svc.get_profile(profile_id)

        if not profile:
            return jsonify({"error": f"Profile {profile_id} not found"}), 404

        profile_elements = profile.get("elements", [])

        if not sample_text and mode in ("qualitative", "both"):
            corpus_doc = query_all(
                """SELECT original_text FROM documents
                   WHERE voice_profile_id = %s AND purpose = 'voice_corpus'
                   ORDER BY length(original_text) DESC LIMIT 1""",
                (profile_id,),
            )
            if corpus_doc:
                sample_text = corpus_doc[0]["original_text"][:5000]
            else:
                if mode == "qualitative":
                    return jsonify({"error": "No corpus documents available for qualitative scoring. Provide sample_text or parse documents into this profile first."}), 400
                mode = "quantitative"

        result = do_score(
            generated_text=generated_text,
            profile_elements=profile_elements,
            sample_text=sample_text,
            mode=mode,
        )
        return jsonify(result)

    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500
