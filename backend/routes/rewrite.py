"""Rewriting endpoints - humanize AI-detected text."""
from flask import Blueprint, request, jsonify

rewrite_bp = Blueprint("rewrite", __name__)


@rewrite_bp.route("/rewrite", methods=["POST"])
def rewrite_text():
    """Rewrite text to sound more human.

    Accepts: text, optional voice_profile_id, optional baseline_id, optional overlay_ids,
             optional target_sentences (indices), optional use_ai, optional comment.
    """
    data = request.get_json()
    if not data or "text" not in data:
        return jsonify({"error": "Provide 'text' in JSON body"}), 400

    text = data["text"]
    voice_profile_id = data.get("voice_profile_id")
    baseline_id = data.get("baseline_id")          # New: explicit baseline profile id
    overlay_ids = data.get("overlay_ids")          # New: explicit overlay profile ids
    target_sentences = data.get("target_sentences")  # List of sentence indices to rewrite
    use_ai = data.get("use_ai")  # Per-request AI toggle
    comment = data.get("comment")  # Optional user instructions for the rewriter

    from ai_providers.router import route_rewrite
    result = route_rewrite(
        text,
        voice_profile_id,
        use_ai=use_ai if "use_ai" in data else None,
        comment=comment,
        baseline_id=baseline_id,
        overlay_ids=overlay_ids,
    )

    return jsonify(result)


@rewrite_bp.route("/rewrite/auto-optimize", methods=["POST"])
def auto_optimize():
    """Iterative rewrite loop — up to max_iterations, stopping if target_score met.

    Request: { text, voice_profile_id?, target_score: 20, max_iterations: 3, comment? }
    Response: { iterations: [{iteration, rewritten_text, score, classification, patterns}],
                final_score, target_met }
    """
    data = request.get_json()
    if not data or "text" not in data:
        return jsonify({"error": "Provide 'text' in JSON body"}), 400

    text = data["text"]
    voice_profile_id = data.get("voice_profile_id")
    target_score = data.get("target_score", 20)
    max_iterations = min(data.get("max_iterations", 3), 3)  # Cap at 3
    comment = data.get("comment")
    use_ai = data.get("use_ai")

    from ai_providers.router import route_rewrite

    iterations = []
    current_text = text

    for i in range(max_iterations):
        result = route_rewrite(
            current_text, voice_profile_id,
            use_ai=use_ai if "use_ai" in data else None,
            comment=comment,
        )

        score = result.get("score") or result.get("_after_score", 100)
        iteration_result = {
            "iteration": i + 1,
            "rewritten_text": result.get("rewritten_text", current_text),
            "score": score,
            "classification": result.get("classification"),
            "patterns": result.get("patterns", []),
        }
        iterations.append(iteration_result)
        current_text = iteration_result["rewritten_text"]

        if score <= target_score:
            break

    final_score = iterations[-1]["score"] if iterations else None
    return jsonify({
        "iterations": iterations,
        "final_score": final_score,
        "target_met": final_score is not None and final_score <= target_score,
    })
