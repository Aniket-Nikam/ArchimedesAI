import json
import time

from conftest import register

import config
from api import api_utils
from api import retraction_checker as retractions
from db.database import get_connection
from services import job_service
from services import research_pipeline as research
from services.paper_utils import unique_papers


def events(response):
    return [
        json.loads(line[5:].strip())
        for line in response.text.splitlines()
        if line.startswith("data:")
    ]


def mock_pipeline(monkeypatch):
    monkeypatch.setattr(config, "GROQ_API_KEY", "test-only-not-a-real-key")
    monkeypatch.setattr(research, "extract_topics", lambda _: "test topic")
    monkeypatch.setattr(
        research,
        "search_semantic_scholar",
        lambda *_: [{"id": "root", "title": "Evidence A", "source": "Semantic Scholar"}],
    )
    monkeypatch.setattr(
        research,
        "search_arxiv",
        lambda *_: [
            {"title": "Evidence A", "source": "arXiv"},
            {"title": "Evidence B", "source": "arXiv"},
        ],
    )
    monkeypatch.setattr(research, "search_pubmed", lambda *_: [])
    monkeypatch.setattr(research, "get_citations", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(
        research,
        "generate_structured_synthesis",
        lambda *_args, **_kwargs: {"overview": "Test synthesis", "key_findings": []},
    )


def test_unconfigured_ai_returns_actionable_failure(client):
    register(client)
    result = client.post("/api/research/", json={"query": "quantum computing"})
    assert result.status_code == 503
    assert "unavailable" in result.json()["detail"]
    assert client.get("/api/history/").json() == []


def test_research_stream_saves_deduplicated_report_and_real_id(client, monkeypatch):
    user = register(client)
    mock_pipeline(monkeypatch)
    response = client.post("/api/research/", json={"query": "test evidence", "user_id": 999999})
    assert response.status_code == 200
    payload = next(e["data"] for e in events(response) if e["type"] == "complete")
    assert payload["total_crawled"] == 2
    assert any(s["status"] == "empty_or_unavailable" for s in payload["source_status"])
    assert all(p["retraction_status"]["is_retracted"] is None for p in payload["seminal"])
    saved = client.get(f"/api/history/{payload['session_id']}").json()
    assert saved["user_id"] == user["id"]
    assert saved["report"]["session_id"] == payload["session_id"]


def test_empty_sources_and_failed_synthesis_never_save_fake_success(client, monkeypatch):
    register(client)
    mock_pipeline(monkeypatch)
    monkeypatch.setattr(research, "search_semantic_scholar", lambda *_: [])
    monkeypatch.setattr(research, "search_arxiv", lambda *_: [])
    response = client.post("/api/research/", json={"query": "test evidence"})
    assert any(e["type"] == "error" for e in events(response))
    assert client.get("/api/history/").json() == []


def test_only_one_research_job_per_account(client, monkeypatch):
    user = register(client)
    mock_pipeline(monkeypatch)
    job_service.enqueue(user["id"], {"query": "test evidence"})
    assert client.post("/api/research/", json={"query": "test evidence"}).status_code == 409


def test_invalid_synthesis_never_becomes_saved_success(client, monkeypatch):
    register(client)
    mock_pipeline(monkeypatch)
    monkeypatch.setattr(
        research,
        "generate_structured_synthesis",
        lambda *_args, **_kwargs: "Failed to generate initial draft.",
    )
    response = client.post("/api/research/", json={"query": "test evidence"})
    assert not any(e["type"] == "complete" for e in events(response))
    assert any(e["type"] == "error" for e in events(response))
    assert client.get("/api/history/").json() == []


def test_global_research_capacity_returns_retryable_error(client, monkeypatch):
    register(client)
    mock_pipeline(monkeypatch)
    monkeypatch.setattr(config, "MAX_CONCURRENT_RESEARCH", 0)
    result = client.post("/api/research/", json={"query": "test evidence"})
    assert result.status_code == 429
    assert result.headers["retry-after"] == "10"


def test_timeout_stops_pipeline_before_sources_or_save(client, monkeypatch):
    register(client)
    mock_pipeline(monkeypatch)
    monkeypatch.setattr(config, "RESEARCH_TIMEOUT_SECONDS", 0.03)
    monkeypatch.setattr(research, "extract_topics", lambda _: (time.sleep(0.1), "topic")[1])
    result = client.post("/api/research/", json={"query": "test evidence"})
    assert any(e["type"] == "error" for e in events(result))
    until = time.monotonic() + 2
    while (
        get_connection()
        .execute("SELECT 1 FROM research_jobs WHERE status IN ('queued','running')")
        .fetchone()
        and time.monotonic() < until
    ):
        time.sleep(0.01)
    assert (
        not get_connection()
        .execute("SELECT 1 FROM research_jobs WHERE status IN ('queued','running')")
        .fetchone()
    )
    assert get_connection().execute("SELECT COUNT(*) FROM research_sessions").fetchone()[0] == 0


def test_retraction_failures_and_unchecked_papers_remain_unknown(monkeypatch):
    monkeypatch.setattr(retractions, "resilient_request", lambda *_args, **_kwargs: None)
    papers = [{"title": "One", "doi": "10.1/test"}, {"title": "Two", "doi": "10.2/test"}]
    retractions.check_papers_retraction(papers, max_checks=1)
    assert all(p["retraction_status"]["is_retracted"] is None for p in papers)


def test_dedup_normalizes_title_and_doi():
    papers = [
        {"title": "A: Study", "doi": "10.1/ABC"},
        {"title": "a study"},
        {"title": "Alternate title", "doi": "https://doi.org/10.1/abc"},
        {"title": "Another"},
    ]
    assert len(unique_papers(papers)) == 2


def test_http_retry_after_is_capped_and_no_final_sleep(monkeypatch):
    class Response:
        status_code = 429
        headers = {"Retry-After": "99999999"}

        def close(self):
            pass

    sleeps = []
    monkeypatch.setattr(api_utils.requests, "get", lambda *_args, **_kwargs: Response())
    monkeypatch.setattr(api_utils.time, "sleep", sleeps.append)
    assert api_utils.resilient_request("https://example.com", max_retries=2) is None
    assert sleeps == [5.0]
