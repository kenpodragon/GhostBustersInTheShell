"""Split documents into logical sections by headings or paragraph breaks."""
import re


def split_sections(text: str) -> list[dict]:
    """Split text into sections based on markdown headings or paragraph breaks.

    Returns list of {"heading": str, "text": str, "section_order": int}.
    """
    if not text or not text.strip():
        return []

    # Try markdown heading splitting first
    sections = _split_by_headings(text)
    if sections:
        return sections

    # Fallback: split on double newlines (paragraph breaks)
    return _split_by_paragraphs(text)


def _split_by_headings(text: str) -> list[dict]:
    """Split on markdown headings (# through ####)."""
    heading_pattern = re.compile(r'^(#{1,4})\s+(.+)$', re.MULTILINE)
    matches = list(heading_pattern.finditer(text))

    if not matches:
        return []

    sections = []

    # Content before first heading becomes its own section
    pre_heading = text[:matches[0].start()].strip()
    if pre_heading:
        sections.append({
            "heading": f"Section {len(sections) + 1}",
            "text": pre_heading,
            "section_order": len(sections),
        })

    for i, match in enumerate(matches):
        heading = match.group(2).strip()
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end].strip()

        sections.append({
            "heading": heading,
            "text": body,
            "section_order": len(sections),
        })

    return sections


def _split_by_paragraphs(text: str) -> list[dict]:
    """Split on double newlines as fallback."""
    paragraphs = re.split(r'\n\s*\n', text.strip())
    sections = []
    for para in paragraphs:
        para = para.strip()
        if para:
            sections.append({
                "heading": f"Section {len(sections) + 1}",
                "text": para,
                "section_order": len(sections),
            })
    return sections
