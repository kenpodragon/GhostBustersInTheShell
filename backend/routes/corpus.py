"""Corpus management and document cleanup endpoints."""
from flask import Blueprint, request, jsonify

corpus_bp = Blueprint("corpus", __name__)


@corpus_bp.route("/voice-profiles/<int:profile_id>/corpus", methods=["GET"])
def get_corpus_info(profile_id):
    """Get corpus documents and stats for a voice profile."""
    try:
        from db import query_all, query_one
        docs = query_all(
            """SELECT d.id, d.filename, length(d.original_text) AS word_count, d.created_at,
                      EXISTS(SELECT 1 FROM ai_parse_observations a WHERE a.document_id = d.id) AS has_ai_observations
               FROM documents d
               WHERE d.voice_profile_id = %s AND d.purpose = 'voice_corpus'
               ORDER BY d.created_at DESC""",
            (profile_id,),
        )
        stats_row = query_one(
            """SELECT COUNT(*) AS total_documents,
                      COALESCE(SUM(length(original_text)), 0) AS total_words,
                      (SELECT COUNT(*) FROM ai_parse_observations WHERE profile_id = %s) AS ai_observations_count
               FROM documents
               WHERE voice_profile_id = %s AND purpose = 'voice_corpus'""",
            (profile_id, profile_id),
        )
        return jsonify({
            "documents": docs,
            "stats": {
                "total_documents": stats_row["total_documents"] if stats_row else 0,
                "total_words": stats_row["total_words"] if stats_row else 0,
                "ai_observations_count": stats_row["ai_observations_count"] if stats_row else 0,
            },
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@corpus_bp.route("/voice-profiles/<int:profile_id>/corpus/<int:document_id>", methods=["DELETE"])
def remove_corpus_document(profile_id, document_id):
    """Remove a document from the voice corpus."""
    try:
        from db import query_one, execute
        doc = query_one(
            "SELECT id FROM documents WHERE id = %s AND voice_profile_id = %s AND purpose = 'voice_corpus'",
            (document_id, profile_id),
        )
        if not doc:
            return jsonify({"error": "Document not found in this profile's corpus"}), 404
        execute("DELETE FROM ai_parse_observations WHERE document_id = %s", (document_id,))
        execute("DELETE FROM documents WHERE id = %s", (document_id,))
        return jsonify({"status": "deleted", "document_id": document_id,
                        "warning": "This does not undo the document's effect on current profile weights. Re-parse to recalculate."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@corpus_bp.route("/documents/management", methods=["GET"])
def list_documents_management():
    """List documents for management/cleanup. Filterable by purpose and age."""
    purpose = request.args.get("purpose", "analysis")
    older_than = request.args.get("older_than")
    try:
        from db import query_all, query_one
        conditions = ["purpose = %s"]
        params = [purpose]
        if older_than and older_than.endswith("d"):
            days = int(older_than[:-1])
            conditions.append("created_at < NOW() - make_interval(days => %s)")
            params.append(days)
        where = " AND ".join(conditions)
        docs = query_all(
            f"""SELECT id, filename, file_type, length(original_text) AS word_count, created_at, voice_profile_id
                FROM documents WHERE {where}
                ORDER BY created_at DESC""",
            tuple(params),
        )
        stats = query_one(
            f"SELECT COUNT(*) AS total_count, COALESCE(SUM(length(original_text)), 0) AS total_size_words FROM documents WHERE {where}",
            tuple(params),
        )
        return jsonify({
            "documents": docs,
            "stats": {"total_count": stats["total_count"], "total_size_words": stats["total_size_words"]},
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@corpus_bp.route("/documents/purge", methods=["DELETE"])
def purge_documents():
    """Bulk delete documents by purpose and age. Refuses to purge voice_corpus."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "JSON body required"}), 400
    purpose = data.get("purpose", "analysis")
    if purpose == "voice_corpus":
        return jsonify({"error": "Cannot bulk purge voice corpus documents. Delete individually via corpus manager."}), 400
    older_than_days = data.get("older_than_days", 30)
    try:
        from db import query_one, execute
        count_row = query_one(
            "SELECT COUNT(*) AS cnt FROM documents WHERE purpose = %s AND created_at < NOW() - make_interval(days => %s)",
            (purpose, older_than_days),
        )
        execute(
            "DELETE FROM documents WHERE purpose = %s AND created_at < NOW() - make_interval(days => %s)",
            (purpose, older_than_days),
        )
        return jsonify({"status": "purged", "deleted_count": count_row["cnt"] if count_row else 0})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
