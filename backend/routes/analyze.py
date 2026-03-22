"""Analysis endpoints - detect AI patterns in text."""
from flask import Blueprint, request, jsonify

analyze_bp = Blueprint("analyze", __name__)


@analyze_bp.route("/analyze", methods=["POST"])
def analyze_text():
    """Analyze text or document for AI-generated content.

    Accepts JSON body with 'text' field, or file upload (DOCX/PDF).
    Returns sentence-level AI scores and detected patterns.
    """
    # Handle file upload
    if request.files:
        file = request.files.get("file")
        if not file:
            return jsonify({"error": "No file provided"}), 400

        filename = file.filename.lower()
        if filename.endswith(".pdf"):
            from utils.doc_parser import parse_pdf
            text = parse_pdf(file)
        elif filename.endswith(".docx"):
            from utils.doc_parser import parse_docx
            text = parse_docx(file)
        elif filename.endswith(".txt"):
            text = file.read().decode("utf-8")
        else:
            return jsonify({"error": "Unsupported file type. Use .pdf, .docx, or .txt"}), 400
    else:
        data = request.get_json()
        if not data or "text" not in data:
            return jsonify({"error": "Provide 'text' in JSON body or upload a file"}), 400
        text = data["text"]

    if not text or not text.strip():
        return jsonify({"error": "Empty text provided"}), 400

    from ai_providers.router import route_analysis
    result = route_analysis(text)
    return jsonify(result)


@analyze_bp.route("/score", methods=["POST"])
def quick_score():
    """Quick AI detection score (Python heuristics only, no AI provider)."""
    data = request.get_json()
    if not data or "text" not in data:
        return jsonify({"error": "Provide 'text' in JSON body"}), 400

    from utils.detector import detect_ai_patterns
    result = detect_ai_patterns(data["text"])
    return jsonify(result)
