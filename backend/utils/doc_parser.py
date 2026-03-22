"""Document parsing utilities - extract text from DOCX and PDF files."""


def parse_pdf(file_obj) -> str:
    """Extract text from a PDF file."""
    import pdfplumber
    text_parts = []
    with pdfplumber.open(file_obj) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
    return "\n\n".join(text_parts)


def parse_docx(file_obj) -> str:
    """Extract text from a DOCX file."""
    from docx import Document
    doc = Document(file_obj)
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n\n".join(paragraphs)
