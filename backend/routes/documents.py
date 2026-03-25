"""Document management endpoints - upload, store, retrieve."""
from flask import Blueprint, request, jsonify
import db as _db

documents_bp = Blueprint("documents", __name__)


@documents_bp.route("/documents", methods=["GET"])
def list_documents():
    """List all stored documents."""
    docs = _db.query_all(
        "SELECT id, filename, file_type, created_at, overall_score FROM documents ORDER BY created_at DESC"
    )
    return jsonify(docs)


@documents_bp.route("/documents/<int:doc_id>", methods=["GET"])
def get_document(doc_id):
    """Get a specific document with its sections."""
    doc = _db.query_one("SELECT * FROM documents WHERE id = %s", (doc_id,))
    if not doc:
        return jsonify({"error": "Document not found"}), 404

    sections = _db.query_all(
        "SELECT * FROM document_sections WHERE document_id = %s ORDER BY section_order",
        (doc_id,)
    )
    doc["sections"] = sections
    return jsonify(doc)


@documents_bp.route("/documents", methods=["POST"])
def create_document():
    """Create a new document by uploading text or a file.

    JSON body: {"text": "...", "title": "...", "voice_profile_id": 1}
    Multipart: file field (PDF/DOCX/TXT) + optional title, voice_profile_id fields.

    Returns the created document with its sections (HTTP 201).
    """
    from utils.section_splitter import split_sections

    # --- Extract text ---
    if request.files:
        file = request.files.get("file")
        if not file:
            return jsonify({"error": "No file provided"}), 400

        try:
            from utils.file_extractor import extract_text_from_file
            text, filename, file_type = extract_text_from_file(file)
        except ValueError as e:
            return jsonify({"error": str(e)}), 400

        title = request.form.get("title") or filename
        voice_profile_id = request.form.get("voice_profile_id")
        if voice_profile_id is not None:
            try:
                voice_profile_id = int(voice_profile_id)
            except (TypeError, ValueError):
                voice_profile_id = None
    else:
        data = request.get_json()
        if not data or "text" not in data:
            return jsonify({"error": "Provide 'text' in JSON body or upload a file"}), 400

        text = data["text"]
        title = data.get("title") or "Untitled"
        file_type = "text"
        filename = title
        voice_profile_id = data.get("voice_profile_id")

    if not text or not text.strip():
        return jsonify({"error": "Empty text provided"}), 400

    # --- Insert document ---
    row = _db.query_one(
        """
        INSERT INTO documents (filename, file_type, original_text, voice_profile_id)
        VALUES (%s, %s, %s, %s)
        RETURNING id, filename, file_type, original_text, overall_score,
                  voice_profile_id, created_at, updated_at
        """,
        (filename, file_type, text, voice_profile_id),
    )
    doc_id = row["id"]

    # --- Split and insert sections ---
    sections = split_sections(text)
    for sec in sections:
        _db.execute(
            """
            INSERT INTO document_sections
                (document_id, section_order, heading, original_text)
            VALUES (%s, %s, %s, %s)
            """,
            (doc_id, sec["section_order"], sec["heading"], sec["text"]),
        )

    # --- Return document with sections ---
    stored_sections = _db.query_all(
        "SELECT * FROM document_sections WHERE document_id = %s ORDER BY section_order",
        (doc_id,),
    )
    doc = dict(row)
    doc["sections"] = stored_sections
    return jsonify(doc), 201
