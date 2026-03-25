"""Tests for documents route — section splitter integration and POST /documents."""
import pytest
from unittest.mock import patch, MagicMock
from utils.section_splitter import split_sections


class TestSectionSplitterIntegration:
    """Verify split_sections output matches what documents route expects."""

    def test_markdown_text_produces_sections(self):
        text = "# Introduction\nThis is the intro.\n\n# Methods\nThis is methods."
        sections = split_sections(text)
        assert len(sections) == 2
        assert sections[0]["heading"] == "Introduction"
        assert sections[1]["heading"] == "Methods"
        assert all("section_order" in s for s in sections)
        assert all("text" in s for s in sections)

    def test_plain_text_splits_by_paragraphs(self):
        text = "First paragraph text here.\n\nSecond paragraph text here."
        sections = split_sections(text)
        assert len(sections) == 2
        assert sections[0]["section_order"] == 0
        assert sections[1]["section_order"] == 1

    def test_section_order_is_zero_based_sequential(self):
        text = "# A\nContent A.\n\n# B\nContent B.\n\n# C\nContent C."
        sections = split_sections(text)
        orders = [s["section_order"] for s in sections]
        assert orders == list(range(len(sections)))

    def test_empty_text_returns_empty_list(self):
        assert split_sections("") == []
        assert split_sections("   ") == []

    def test_section_text_is_not_empty(self):
        text = "# Section One\nHere is some actual content.\n\n# Section Two\nMore content."
        sections = split_sections(text)
        for s in sections:
            assert s["text"].strip(), f"Section '{s['heading']}' has empty text"

    def test_heading_field_is_string(self):
        text = "Some plain paragraph.\n\nAnother paragraph."
        sections = split_sections(text)
        for s in sections:
            assert isinstance(s["heading"], str)


class TestCreateDocumentRoute:
    """Tests for POST /documents using mocked DB."""

    @pytest.fixture
    def app(self):
        """Create a minimal Flask test app with the documents blueprint."""
        from flask import Flask
        from routes.documents import documents_bp
        app = Flask(__name__)
        app.register_blueprint(documents_bp)
        app.config["TESTING"] = True
        return app

    @pytest.fixture
    def client(self, app):
        return app.test_client()

    def _mock_db(self, doc_id=1):
        """Return a mock for db functions that simulates a successful insert."""
        mock_row = {
            "id": doc_id,
            "filename": "Untitled",
            "file_type": "text",
            "original_text": "Test text.",
            "overall_score": 0.0,
            "voice_profile_id": None,
            "created_at": "2026-01-01T00:00:00",
            "updated_at": "2026-01-01T00:00:00",
        }
        mock_section = {
            "id": 1,
            "document_id": doc_id,
            "section_order": 0,
            "heading": "Section 1",
            "original_text": "Test text.",
            "rewritten_text": None,
            "ai_score": None,
            "status": None,
        }
        return mock_row, [mock_section]

    def test_post_json_text_returns_201(self, client):
        mock_row, mock_sections = self._mock_db()
        with patch("routes.documents._db") as mock_db:
            mock_db.query_one.return_value = mock_row
            mock_db.execute.return_value = 1
            mock_db.query_all.return_value = mock_sections
            resp = client.post(
                "/documents",
                json={"text": "First paragraph.\n\nSecond paragraph."},
            )
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["id"] == 1
        assert "sections" in data

    def test_post_missing_text_returns_400(self, client):
        resp = client.post("/documents", json={"title": "No text here"})
        assert resp.status_code == 400
        assert "error" in resp.get_json()

    def test_post_empty_text_returns_400(self, client):
        resp = client.post("/documents", json={"text": "   "})
        assert resp.status_code == 400

    def test_post_no_body_returns_400(self, client):
        resp = client.post("/documents", content_type="application/json", data="")
        assert resp.status_code == 400

    def test_sections_stored_match_split_sections_count(self, client):
        """Confirm execute is called once per section from split_sections."""
        text = "# Part One\nContent one.\n\n# Part Two\nContent two."
        expected_sections = split_sections(text)
        mock_row, _ = self._mock_db()
        mock_row["original_text"] = text
        stored_sections = [
            {"id": i + 1, "document_id": 1, "section_order": s["section_order"],
             "heading": s["heading"], "original_text": s["text"],
             "rewritten_text": None, "ai_score": None, "status": None}
            for i, s in enumerate(expected_sections)
        ]
        with patch("routes.documents._db") as mock_db:
            mock_db.query_one.return_value = mock_row
            mock_db.execute.return_value = 1
            mock_db.query_all.return_value = stored_sections
            resp = client.post("/documents", json={"text": text})
        assert resp.status_code == 201
        assert mock_db.execute.call_count == len(expected_sections)
