"""API-level checks for the research tools, using explicit provider stubs."""

import pymupdf
from conftest import register

import config
from routers import draft_router, extract_router, litreview_router, upload_router
from services import ai_jobs
from services.history_service import save_research_session

PAPER = {"title": "Fixture paper", "authors": ["Test Author"], "abstract": "Test evidence."}


def test_bookmark_notes_and_removal_roundtrip(client):
    register(client)
    assert client.post("/api/bookmarks/", json={"paper": PAPER}).status_code == 200
    assert (
        client.put(
            "/api/bookmarks/notes", json={"paper_title": PAPER["title"], "notes": "Read methods"}
        ).status_code
        == 200
    )
    saved = client.get("/api/bookmarks/").json()
    assert saved[0]["paper"] == PAPER
    assert saved[0]["notes"] == "Read methods"
    assert (
        client.request(
            "DELETE", "/api/bookmarks/", json={"paper_title": PAPER["title"]}
        ).status_code
        == 200
    )
    assert client.get("/api/bookmarks/").json() == []


def test_health_does_not_expose_provider_secret(client, monkeypatch):
    monkeypatch.setattr(config, "GROQ_API_KEY", "test-secret-never-return")
    result = client.get("/api/health")
    assert result.status_code == 200
    assert result.json()["ai_configured"] is True
    assert "test-secret-never-return" not in result.text


def test_draft_receives_selected_papers_and_notes(client, monkeypatch):
    register(client)
    monkeypatch.setattr(config, "GROQ_API_KEY", "test-key")
    received = []

    def draft(section, notes, papers):
        received.append((section, notes, papers))
        return "# Test draft"

    monkeypatch.setattr(draft_router, "generate_manuscript_draft", draft)
    result = client.post(
        "/api/draft/",
        json={"section": "Introduction", "notes": "Compare methods", "papers": [PAPER]},
    )
    assert result.json() == {"draft": "# Test draft"}
    assert received == [("Introduction", "Compare methods", [PAPER])]


def test_extraction_returns_provider_rows(client, monkeypatch):
    register(client)
    monkeypatch.setattr(config, "GROQ_API_KEY", "test-key")
    rows = [{"title": PAPER["title"], "sample_size": "Not stated"}]
    monkeypatch.setattr(
        extract_router, "extract_paper_data", lambda papers: rows if papers == [PAPER] else []
    )
    result = client.post("/api/extract/", json={"papers": [PAPER]})
    assert result.status_code == 200
    assert result.json() == {"extracted_data": rows}


def test_literature_review_download_uses_saved_evidence(client, monkeypatch):
    user = register(client)
    monkeypatch.setattr(config, "GROQ_API_KEY", "test-key")
    session = save_research_session(user["id"], "test question", {"seminal": [PAPER]})
    received = []

    def review(papers, query, synthesis):
        received.append((papers, query))
        return "# Test literature review"

    monkeypatch.setattr(litreview_router, "generate_literature_review", review)
    result = client.post("/api/litreview/", json={"session_id": session})
    assert result.status_code == 200
    assert result.text == "# Test literature review"
    assert "attachment;" in result.headers["content-disposition"]
    assert received == [([PAPER], "test question")]


def test_unconfigured_utility_tools_return_503(client):
    register(client)
    assert (
        client.post(
            "/api/draft/", json={"section": "Introduction", "notes": "Notes", "papers": [PAPER]}
        ).status_code
        == 503
    )
    assert client.post("/api/extract/", json={"papers": [PAPER]}).status_code == 503


def test_utility_provider_failure_returns_502_and_recovers(client, monkeypatch):
    register(client)
    monkeypatch.setattr(config, "GROQ_API_KEY", "test-key")

    def fail(_papers):
        raise RuntimeError("private-provider-diagnostic")

    monkeypatch.setattr(extract_router, "extract_paper_data", fail)
    for _ in range(3):
        result = client.post("/api/extract/", json={"papers": [PAPER]})
        assert result.status_code == 502
        assert "private-provider-diagnostic" not in result.text
    monkeypatch.setattr(extract_router, "extract_paper_data", lambda _: [])
    assert client.post("/api/extract/", json={"papers": [PAPER]}).status_code == 200


def test_utility_capacity_rejects_then_recovers(client, monkeypatch):
    register(client)
    monkeypatch.setattr(config, "GROQ_API_KEY", "test-key")
    monkeypatch.setattr(extract_router, "extract_paper_data", lambda _: [])
    held = 0
    try:
        while ai_jobs._slots.acquire(blocking=False):
            held += 1
        assert client.post("/api/extract/", json={"papers": [PAPER]}).status_code == 429
    finally:
        for _ in range(held):
            ai_jobs._slots.release()
    assert client.post("/api/extract/", json={"papers": [PAPER]}).status_code == 200


def pdf_bytes(pages=1):
    with pymupdf.open() as doc:
        for _ in range(pages):
            page = doc.new_page()
            page.insert_textbox(
                (40, 40, 500, 700), "Synthetic paper text for API verification. " * 10
            )
        return doc.tobytes()


def test_malformed_pdf_rejected(client):
    register(client)
    assert (
        client.post(
            "/api/upload/", files={"file": ("paper.pdf", b"not a PDF", "application/pdf")}
        ).status_code
        == 400
    )


def test_non_pdf_extension_rejected(client):
    register(client)
    assert (
        client.post(
            "/api/upload/", files={"file": ("paper.txt", b"text", "text/plain")}
        ).status_code
        == 400
    )


def test_pdf_page_limit_enforced(client):
    register(client)
    result = client.post(
        "/api/upload/", files={"file": ("paper.pdf", pdf_bytes(101), "application/pdf")}
    )
    assert result.status_code == 400
    assert "100 pages" in result.json()["detail"]


def test_pdf_read_limit_enforced(client, monkeypatch):
    register(client)
    monkeypatch.setattr(upload_router, "MAX_FILE_SIZE", 1024)
    result = client.post(
        "/api/upload/", files={"file": ("paper.pdf", b"x" * 1025, "application/pdf")}
    )
    assert result.status_code == 400
    assert "too large" in result.json()["detail"]


def test_pdf_analysis_returns_page_count_and_stubbed_analysis(client, monkeypatch):
    register(client)
    monkeypatch.setattr(config, "GROQ_API_KEY", "test-key")
    monkeypatch.setattr(
        upload_router, "extract_paper_metadata", lambda _: {"title": "Fixture", "keywords": []}
    )
    monkeypatch.setattr(upload_router, "search_semantic_scholar", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(upload_router, "search_arxiv", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(upload_router, "analyze_paper_claims", lambda *_: "Synthetic test analysis")
    result = client.post(
        "/api/upload/", files={"file": ("paper.pdf", pdf_bytes(), "application/pdf")}
    )
    assert result.status_code == 200
    assert result.json()["pages"] == 1
    assert result.json()["text_length"] >= 100
    assert result.json()["claim_analysis"] == "Synthetic test analysis"
