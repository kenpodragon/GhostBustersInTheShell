"""Tests for section_splitter — splits documents into logical sections."""
import pytest
from utils.section_splitter import split_sections


class TestMarkdownSplitting:
    def test_splits_on_h1(self):
        text = "# Introduction\nFirst paragraph.\n\n# Methods\nSecond paragraph."
        sections = split_sections(text)
        assert len(sections) == 2
        assert sections[0]["heading"] == "Introduction"
        assert "First paragraph" in sections[0]["text"]
        assert sections[1]["heading"] == "Methods"

    def test_splits_on_h2_h3(self):
        text = "## Part A\nContent A.\n\n### Sub-part\nContent B.\n\n## Part C\nContent C."
        sections = split_sections(text)
        assert len(sections) == 3

    def test_preserves_heading_hierarchy(self):
        text = "# Title\nIntro.\n\n## Section 1\nBody 1.\n\n## Section 2\nBody 2."
        sections = split_sections(text)
        assert sections[0]["heading"] == "Title"
        assert sections[1]["heading"] == "Section 1"

    def test_content_before_first_heading(self):
        text = "Preamble text.\n\n# First Section\nBody."
        sections = split_sections(text)
        assert len(sections) == 2
        assert sections[0]["heading"] == "Section 1"
        assert "Preamble" in sections[0]["text"]


class TestParagraphFallback:
    def test_no_headings_splits_on_double_newline(self):
        text = "First paragraph here.\n\nSecond paragraph here.\n\nThird paragraph here."
        sections = split_sections(text)
        assert len(sections) == 3
        assert sections[0]["heading"] == "Section 1"

    def test_single_paragraph_is_one_section(self):
        text = "Just a single block of text with no breaks."
        sections = split_sections(text)
        assert len(sections) == 1

    def test_empty_text(self):
        sections = split_sections("")
        assert len(sections) == 0

    def test_whitespace_only(self):
        sections = split_sections("   \n\n   ")
        assert len(sections) == 0


class TestSectionStructure:
    def test_section_has_required_fields(self):
        text = "# Test\nSome content."
        sections = split_sections(text)
        section = sections[0]
        assert "heading" in section
        assert "text" in section
        assert "section_order" in section
        assert section["section_order"] == 0

    def test_section_order_is_sequential(self):
        text = "# A\nOne.\n\n# B\nTwo.\n\n# C\nThree."
        sections = split_sections(text)
        orders = [s["section_order"] for s in sections]
        assert orders == [0, 1, 2]
