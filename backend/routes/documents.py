"""Document management endpoints - upload, store, retrieve, export."""
from flask import Blueprint, request, jsonify

documents_bp = Blueprint("documents", __name__)


@documents_bp.route("/documents", methods=["GET"])
def list_documents():
    """List all stored documents."""
    from db import query_all
    docs = query_all(
        "SELECT id, filename, file_type, created_at, overall_score FROM documents ORDER BY created_at DESC"
    )
    return jsonify(docs)


@documents_bp.route("/documents/<int:doc_id>", methods=["GET"])
def get_document(doc_id):
    """Get a specific document with its analysis."""
    from db import query_one, query_all
    doc = query_one("SELECT * FROM documents WHERE id = %s", (doc_id,))
    if not doc:
        return jsonify({"error": "Document not found"}), 404

    sections = query_all(
        "SELECT * FROM document_sections WHERE document_id = %s ORDER BY section_order",
        (doc_id,)
    )
    doc["sections"] = sections
    return jsonify(doc)


@documents_bp.route("/documents/<int:doc_id>/export", methods=["GET"])
def export_document(doc_id):
    """Export the rewritten document as DOCX or PDF."""
    format = request.args.get("format", "docx")
    from db import query_one, query_all

    doc = query_one("SELECT * FROM documents WHERE id = %s", (doc_id,))
    if not doc:
        return jsonify({"error": "Document not found"}), 404

    sections = query_all(
        "SELECT rewritten_text FROM document_sections WHERE document_id = %s ORDER BY section_order",
        (doc_id,)
    )

    # TODO: Implement DOCX/PDF export
    return jsonify({"error": "Export not yet implemented"}), 501
