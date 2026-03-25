"""Shared file text extraction utility for PDF, DOCX, and TXT uploads."""


def extract_text_from_file(file) -> tuple[str, str, str]:
    """Extract text from an uploaded file object.

    Args:
        file: werkzeug FileStorage object with a .filename attribute.

    Returns:
        Tuple of (text, filename, file_type) where file_type is 'pdf', 'docx', or 'txt'.

    Raises:
        ValueError: If the file type is unsupported or text cannot be extracted.
    """
    filename = file.filename or ""
    lower = filename.lower()

    if lower.endswith(".pdf"):
        from utils.doc_parser import parse_pdf
        text = parse_pdf(file)
        file_type = "pdf"
    elif lower.endswith(".docx"):
        from utils.doc_parser import parse_docx
        text = parse_docx(file)
        file_type = "docx"
    elif lower.endswith(".txt"):
        text = file.read().decode("utf-8")
        file_type = "txt"
    else:
        raise ValueError("Unsupported file type. Use .pdf, .docx, or .txt")

    return text, filename, file_type
