import json
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify
from db import query_one, query_all, execute, get_conn

analysis_history_bp = Blueprint("analysis_history", __name__)


def _purge_expired():
    """Delete entries older than TTL and trim to max count."""
    settings = query_one("SELECT analysis_history_max_count, analysis_history_ttl_hours FROM settings WHERE id = 1")
    if not settings:
        return

    ttl_hours = settings["analysis_history_ttl_hours"] or 24
    max_count = settings["analysis_history_max_count"] or 50

    # TTL purge
    cutoff = datetime.utcnow() - timedelta(hours=ttl_hours)
    execute("DELETE FROM extension_analysis_history WHERE created_at < %s", (cutoff,))

    # Max count purge
    total = query_one("SELECT COUNT(*) as cnt FROM extension_analysis_history")
    if total and total["cnt"] > max_count:
        excess = total["cnt"] - max_count
        execute(
            "DELETE FROM extension_analysis_history WHERE id IN "
            "(SELECT id FROM extension_analysis_history ORDER BY created_at ASC LIMIT %s)",
            (excess,)
        )


@analysis_history_bp.route("/analysis-history", methods=["POST"])
def store_analysis():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body required"}), 400

    text = data.get("text")
    result = data.get("result")
    if not text or result is None:
        return jsonify({"error": "text and result are required"}), 400

    source = data.get("source", "manual")
    if source not in ("manual", "page_scan", "generate"):
        source = "manual"

    page_url = data.get("page_url")

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO extension_analysis_history (text, result, source, page_url) "
                "VALUES (%s, %s, %s, %s) RETURNING id",
                (text, json.dumps(result), source, page_url)
            )
            row = cur.fetchone()
            new_id = row[0] if isinstance(row, tuple) else row["id"]

    # Purge after insert
    _purge_expired()

    return jsonify({"id": new_id}), 201


@analysis_history_bp.route("/analysis-history/<int:history_id>", methods=["GET"])
def get_analysis(history_id):
    row = query_one("SELECT * FROM extension_analysis_history WHERE id = %s", (history_id,))
    if not row:
        return jsonify({"error": "Not found"}), 404

    return jsonify({
        "id": row["id"],
        "text": row["text"],
        "result": row["result"],
        "source": row["source"],
        "page_url": row["page_url"],
        "created_at": row["created_at"].isoformat() if row["created_at"] else None
    })


@analysis_history_bp.route("/analysis-history", methods=["GET"])
def list_analyses():
    limit = request.args.get("limit", 50, type=int)
    rows = query_all(
        "SELECT id, source, page_url, result->>'overall_score' as score, "
        "result->'classification'->>'label' as classification, created_at "
        "FROM extension_analysis_history ORDER BY created_at DESC LIMIT %s",
        (limit,)
    )
    return jsonify([{
        "id": r["id"],
        "source": r["source"],
        "page_url": r["page_url"],
        "score": float(r["score"]) if r["score"] else None,
        "classification": r["classification"],
        "created_at": r["created_at"].isoformat() if r["created_at"] else None
    } for r in rows])


@analysis_history_bp.route("/analysis-history", methods=["DELETE"])
def purge_analyses():
    if request.args.get("all") == "true":
        deleted = execute("DELETE FROM extension_analysis_history")
        return jsonify({"deleted": deleted})

    older_than = request.args.get("older_than", type=int)
    if older_than:
        cutoff = datetime.utcnow() - timedelta(hours=older_than)
        deleted = execute("DELETE FROM extension_analysis_history WHERE created_at < %s", (cutoff,))
        return jsonify({"deleted": deleted})

    return jsonify({"error": "Provide ?all=true or ?older_than=<hours>"}), 400
