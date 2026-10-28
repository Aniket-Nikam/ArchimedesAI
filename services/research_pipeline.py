import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from concurrent.futures import TimeoutError as FutureTimeout

import config
from ai.groq_service import (
    answer_followup,
    classify_followup,
    extract_topics,
    generate_structured_synthesis,
)
from api.api_utils import begin_observation, observations
from api.arxiv_client import get_arxiv_id, search_arxiv
from api.crossref_client import search_crossref_title
from api.pubmed_client import search_pubmed
from api.retraction_checker import check_papers_retraction
from api.semantic_scholar_client import get_citations, search_semantic_scholar
from db.database import close_connection
from services.evidence import attach_evidence_ids, validate_findings
from services.paper_utils import unique_papers
from services.search_intent import named_title, title_score

_providers = ThreadPoolExecutor(max_workers=6, thread_name_prefix="academic-source")
_provider_slots = threading.BoundedSemaphore(8)


class PaperResults(list):
    def __init__(self, papers, requests):
        super().__init__(papers)
        self.requests = requests


def _submit_provider(function, *args):
    if not _provider_slots.acquire(blocking=False):
        raise RuntimeError("Academic sources are busy. Please retry shortly.")

    def run():
        try:
            begin_observation()
            return PaperResults(function(*args), observations())
        finally:
            close_connection()

    try:
        future = _providers.submit(run)
    except Exception:
        _provider_slots.release()
        raise
    future.add_done_callback(lambda _: _provider_slots.release())
    return future


def execute_pipeline(req, user_id, emit, checkpoint):
    started = time.monotonic()
    deadline = started + config.RESEARCH_TIMEOUT_SECONDS
    history = [m.model_dump() for m in req.chat_history[-10:]]
    history.append({"role": "user", "content": req.query})
    if (
        req.mode == "synthesis"
        and req.existing_report
        and classify_followup(req.query, True) in {"followup", "comparison"}
    ):
        emit("log", "Comparing your question with the existing evidence...")
        answer = answer_followup(req.query, req.existing_report, history)
        emit(
            "followup_complete",
            {"answer": answer, "elapsed_seconds": round(time.monotonic() - started, 1)},
        )
        return
    emit("log", "Preparing academic search terms...")
    search = extract_topics(history) if req.mode == "synthesis" else req.query
    title = named_title(req.query)
    checkpoint()
    sources = [
        (search_semantic_scholar, 8, "Semantic Scholar"),
        (search_arxiv, 5, "arXiv"),
        (search_pubmed, 5, "PubMed"),
    ]
    if title:
        emit("log", "Looking up the named paper title without changing its wording...")
        sources.extend(
            [
                (
                    lambda _, limit: search_crossref_title(title, limit),
                    3,
                    "Crossref (title lookup)",
                ),
                (
                    lambda _, limit: search_semantic_scholar(title, limit),
                    3,
                    "Semantic Scholar (title lookup)",
                ),
                (lambda _, limit: search_arxiv(f'ti:"{title}"', limit), 3, "arXiv (title lookup)"),
                (
                    lambda _, limit: search_pubmed(f'"{title}"[Title]', limit),
                    3,
                    "PubMed (title lookup)",
                ),
            ]
        )
    if config.ENABLE_GOOGLE_SCHOLAR:
        from api.google_scholar_client import search_google_scholar

        sources.append((search_google_scholar, 4, "Google Scholar"))
    emit("log", "Searching academic sources in parallel...")
    futures = {}
    coverage = []
    for function, limit, name in sources:
        try:
            futures[_submit_provider(function, search, limit)] = name
        except RuntimeError:
            coverage.append({"source": name, "status": "busy", "count": 0})
    papers = []
    ss_papers = []
    try:
        for future in as_completed(futures, timeout=min(40, max(1, deadline - time.monotonic()))):
            checkpoint()
            name = futures[future]
            try:
                result = future.result()
                requests = getattr(result, "requests", [])
                source_state = (
                    "results"
                    if result
                    else "rate_limited"
                    if any(item.get("status") == 429 for item in requests)
                    else "unavailable"
                    if any(
                        item.get("status") != "network_error"
                        and isinstance(item.get("status"), int)
                        and item["status"] >= 400
                        for item in requests
                    )
                    else "empty_or_unavailable"
                )
                coverage.append(
                    {
                        "source": name,
                        "status": source_state,
                        "requests": requests,
                        "count": len(result),
                    }
                )
                papers.extend(result)
                if name.startswith("Semantic Scholar"):
                    ss_papers.extend(result)
                emit("log", f"{name}: {len(result)} results")
            except Exception:
                coverage.append({"source": name, "status": "unavailable", "count": 0})
                emit("log", f"{name} is unavailable for this search.")
    except FutureTimeout:
        for future, name in futures.items():
            if not any((c["source"] == name for c in coverage)):
                future.cancel()
                coverage.append({"source": name, "status": "timed_out", "count": 0})
    checkpoint()
    seen = set()
    papers.sort(key=lambda paper: title_score(paper, title), reverse=True)
    ss_papers.sort(key=lambda paper: title_score(paper, title), reverse=True)
    seminal = unique_papers(papers, seen)
    if not seminal:
        raise ValueError(
            "No papers returned. Sources may be unavailable; try a more specific question."
        )
    citations, depth2 = ([], [])
    root = seminal[0] if title else ss_papers[0] if ss_papers else None
    root_id = None
    if root:
        root_id = root.get("id") if "Semantic Scholar" in root.get("source", "") else None
        arxiv_id = get_arxiv_id(root.get("url", ""))
        if not root_id and arxiv_id:
            root_id = "ARXIV:" + arxiv_id
        if not root_id and root.get("doi"):
            root_id = "DOI:" + root["doi"]
    begin_observation()
    if root_id:
        emit("log", "Following citation links (up to two levels)...")
        parent = root.get("id") or root.get("url") or root["title"]
        raw = get_citations(root_id, limit=8)
        for paper in raw:
            paper.update(source="Semantic Scholar", cited_by=parent)
        citations = unique_papers(raw, seen)
        checkpoint()
        if citations and citations[0].get("id"):
            parent = citations[0]["id"]
            raw = get_citations(parent, limit=6)
            for paper in raw:
                paper.update(source="Semantic Scholar (D2)", cited_by=parent)
            depth2 = unique_papers(raw, seen)
    citation_requests = observations()
    citation_status = {
        "status": "results"
        if citations or depth2
        else "rate_limited"
        if any(item.get("status") == 429 for item in citation_requests)
        else "empty_or_unavailable"
        if root_id
        else "unsupported_identifier",
        "root_title": root.get("title") if root else None,
        "requests": citation_requests,
        "depth1_count": len(citations),
        "depth2_count": len(depth2),
    }
    checkpoint()
    all_papers = seminal + citations + depth2
    attach_evidence_ids(all_papers)
    emit("log", "Checking available DOI retraction metadata...")
    check_papers_retraction(all_papers, max_checks=3)
    checkpoint()
    emit("log", "Synthesizing evidence. Verify generated claims against the linked papers.")
    synthesis = (
        generate_structured_synthesis(
            all_papers, history, progress_callback=lambda msg: emit("log", msg)
        )
        if req.mode == "synthesis"
        else {
            "overview": "Paper search results only. No AI synthesis was requested.",
            "key_findings": [],
        }
    )
    checkpoint()
    if (
        not isinstance(synthesis, dict)
        or not isinstance(synthesis.get("overview"), str)
        or (not synthesis["overview"].strip())
    ):
        raise RuntimeError("The AI provider could not produce a synthesis. Please retry.")
    payload = {
        "query": req.query,
        "seminal": seminal,
        "citations": citations,
        "citations_depth2": depth2,
        "total_crawled": len(all_papers),
        "ai_synthesis": synthesis,
        "source_status": coverage,
        "citation_status": citation_status,
        "elapsed_seconds": round(time.monotonic() - started, 1),
    }
    payload["ai_synthesis"] = validate_findings(synthesis, all_papers)
    emit("complete", payload)
