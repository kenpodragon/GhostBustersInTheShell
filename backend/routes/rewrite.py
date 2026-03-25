"""Rewriting endpoints - humanize AI-detected text."""
from flask import Blueprint, request, jsonify

rewrite_bp = Blueprint("rewrite", __name__)


@rewrite_bp.route("/rewrite", methods=["POST"])
def rewrite_text():
    """Rewrite text to sound more human.

    Accepts: text, optional voice_profile_id, optional target_sentences (indices).
    """
    data = request.get_json()
    if not data or "text" not in data:
        return jsonify({"error": "Provide 'text' in JSON body"}), 400

    text = data["text"]
    voice_profile_id = data.get("voice_profile_id")
    target_sentences = data.get("target_sentences")  # List of sentence indices to rewrite
    use_ai = data.get("use_ai")  # Per-request AI toggle
    comment = data.get("comment")  # Optional user instructions for the rewriter

    from ai_providers.router import route_rewrite
    result = route_rewrite(text, voice_profile_id, use_ai=use_ai if "use_ai" in data else None, comment=comment)

    return jsonify(result)


@rewrite_bp.route("/rewrite/iterate", methods=["POST"])
def iterate_rewrite():
    """Iterate on a specific section of previously rewritten text."""
    data = request.get_json()
    if not data or "text" not in data or "section_index" not in data:
        return jsonify({"error": "Provide 'text' and 'section_index'"}), 400

    from ai_providers.router import route_rewrite
    use_ai = data.get("use_ai")
    result = route_rewrite(data["text"], data.get("voice_profile_id"), use_ai=use_ai if "use_ai" in data else None)

    return jsonify(result)
