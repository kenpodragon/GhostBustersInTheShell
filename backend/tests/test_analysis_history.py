import json
import pytest
from app import app


@pytest.fixture
def client():
    from db import init_pool
    init_pool()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def test_store_and_retrieve_analysis(client):
    """POST stores analysis, GET retrieves it."""
    payload = {
        "text": "This is a test text for analysis.",
        "result": {"overall_score": 42.3, "classification": {"category": "ghost_touched", "label": "Ghost Touched", "confidence": "medium"}},
        "source": "manual"
    }
    resp = client.post("/api/analysis-history", json=payload)
    assert resp.status_code == 201
    data = resp.get_json()
    assert "id" in data

    resp2 = client.get(f"/api/analysis-history/{data['id']}")
    assert resp2.status_code == 200
    retrieved = resp2.get_json()
    assert retrieved["text"] == "This is a test text for analysis."
    assert retrieved["result"]["overall_score"] == 42.3
    assert retrieved["source"] == "manual"


def test_store_page_scan_with_url(client):
    """Page scans include page_url."""
    payload = {
        "text": "Article content here.",
        "result": {"overall_score": 15.0},
        "source": "page_scan",
        "page_url": "https://example.com/article"
    }
    resp = client.post("/api/analysis-history", json=payload)
    assert resp.status_code == 201
    data = resp.get_json()

    resp2 = client.get(f"/api/analysis-history/{data['id']}")
    retrieved = resp2.get_json()
    assert retrieved["page_url"] == "https://example.com/article"


def test_list_recent_analyses(client):
    """GET /api/analysis-history returns recent entries."""
    for i in range(3):
        client.post("/api/analysis-history", json={
            "text": f"Text {i}",
            "result": {"overall_score": i * 10},
            "source": "manual"
        })

    resp = client.get("/api/analysis-history")
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data) >= 3


def test_retrieve_nonexistent_returns_404(client):
    """GET with bad ID returns 404."""
    resp = client.get("/api/analysis-history/99999")
    assert resp.status_code == 404


def test_purge_all(client):
    """DELETE with all=true clears everything."""
    client.post("/api/analysis-history", json={
        "text": "To be purged",
        "result": {"overall_score": 50},
        "source": "manual"
    })

    resp = client.delete("/api/analysis-history?all=true")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["deleted"] >= 1


def test_store_requires_text_and_result(client):
    """POST without required fields returns 400."""
    resp = client.post("/api/analysis-history", json={"text": "missing result"})
    assert resp.status_code == 400

    resp2 = client.post("/api/analysis-history", json={"result": {}})
    assert resp2.status_code == 400
