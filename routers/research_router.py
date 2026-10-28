"""Bounded research pipeline with cancellation, honest source coverage and saved IDs."""

import asyncio
import json
import logging
import queue
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from concurrent.futures import TimeoutError as FutureTimeout
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

import config
from ai.groq_service import (
    answer_followup,
    classify_followup,
    extract_topics,
    generate_structured_synthesis,
)
from api.arxiv_client import search_arxiv
from api.pubmed_client import search_pubmed
from api.retraction_checker import check_papers_retraction
from api.semantic_scholar_client import get_citations, search_semantic_scholar
from auth.sessions import current_user_id
from db.database import close_connection
from services.history_service import save_research_session
from services.paper_utils import unique_papers

router = APIRouter()
logger = logging.getLogger(__name__)
_slots = threading.BoundedSemaphore(config.MAX_CONCURRENT_RESEARCH)
_users: set[int] = set()
_lock = threading.Lock()
_providers = ThreadPoolExecutor(max_workers=6, thread_name_prefix="academic-source")
_provider_slots = threading.BoundedSemaphore(8)


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=20000)


class ResearchRequest(BaseModel):
    query: str = Field(min_length=3, max_length=1000)
    user_id: int | None = None  # Legacy client field, never used as identity.
    chat_history: list[ChatMessage] = Field(default_factory=list, max_length=20)
    existing_report: dict | None = None


def _submit_provider(function, *args):
    if not _provider_slots.acquire(blocking=False):
        raise RuntimeError("Academic sources are busy. Please retry shortly.")

    def run():
        try:
            return function(*args)
        finally:
            close_connection()

    try:
        future = _providers.submit(run)
    except Exception:
        _provider_slots.release()
        raise
    future.add_done_callback(lambda _: _provider_slots.release())
    return future


@router.post("/")
async def start_research(
    req: ResearchRequest, request: Request, user_id: int = Depends(current_user_id)
):
    if not config.GROQ_API_KEY:
        raise HTTPException(
            503,
            "AI research is currently unavailable. Ask the workspace administrator to enable it.",
        )
    if not req.query.strip():
        raise HTTPException(422, "Enter a research question.")
    with _lock:
        if user_id in _users:
            raise HTTPException(409, "A research job is already running for your account.")
        if not _slots.acquire(blocking=False):
            raise HTTPException(
                429,
                "Research capacity is full. Please retry shortly.",
                headers={"Retry-After": "10"},
            )
        _users.add(user_id)
    events: queue.Queue = queue.Queue(maxsize=128)
    stopped = threading.Event()
    deadline = time.monotonic() + config.RESEARCH_TIMEOUT_SECONDS

    def checkpoint():
        if stopped.is_set():
            raise InterruptedError("Research stopped.")
        if time.monotonic() >= deadline:
            raise TimeoutError("Research timed out. Try a narrower question.")

    def emit(kind, data):
        checkpoint()
        try:
            events.put_nowait(
                {"event": "message", "data": json.dumps({"type": kind, "data": data})}
            )
        except queue.Full:
            raise RuntimeError("Research client is too slow. Please retry.")

    def work():
        started = time.monotonic()
        try:
            history = [m.model_dump() for m in req.chat_history[-10:]]
            history.append({"role": "user", "content": req.query})
            if req.existing_report and classify_followup(req.query, True) in {
                "followup",
                "comparison",
            }:
                emit("log", "Comparing your question with the existing evidence…")
                answer = answer_followup(req.query, req.existing_report, history)
                emit(
                    "followup_complete",
                    {"answer": answer, "elapsed_seconds": round(time.monotonic() - started, 1)},
                )
                return
            emit("log", "Preparing academic search terms…")
            search = extract_topics(history)
            checkpoint()
            sources = [
                (search_semantic_scholar, 8, "Semantic Scholar"),
                (search_arxiv, 5, "arXiv"),
                (search_pubmed, 5, "PubMed"),
            ]
            if config.ENABLE_GOOGLE_SCHOLAR:
                from api.google_scholar_client import search_google_scholar

                sources.append((search_google_scholar, 4, "Google Scholar"))
            emit("log", "Searching academic sources in parallel…")
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
                for future in as_completed(
                    futures, timeout=min(40, max(1, deadline - time.monotonic()))
                ):
                    checkpoint()
                    name = futures[future]
                    try:
                        result = future.result()
                        coverage.append(
                            {
                                "source": name,
                                "status": "results" if result else "empty_or_unavailable",
                                "count": len(result),
                            }
                        )
                        papers.extend(result)
                        if name == "Semantic Scholar":
                            ss_papers = result
                        emit("log", f"{name}: {len(result)} results")
                    except Exception:
                        coverage.append({"source": name, "status": "unavailable", "count": 0})
                        emit("log", f"{name} is unavailable for this search.")
            except FutureTimeout:
                for future, name in futures.items():
                    if not any(c["source"] == name for c in coverage):
                        future.cancel()
                        coverage.append({"source": name, "status": "timed_out", "count": 0})
            checkpoint()
            seen = set()
            seminal = unique_papers(papers, seen)
            if not seminal:
                raise ValueError(
                    "No papers returned. Sources may be unavailable; try a more specific question."
                )
            citations, depth2 = [], []
            if ss_papers and ss_papers[0].get("id"):
                emit("log", "Following citation links (up to two levels)…")
                parent = ss_papers[0]["id"]
                raw = get_citations(parent, limit=8)
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
            checkpoint()
            all_papers = seminal + citations + depth2
            emit("log", "Checking available DOI retraction metadata…")
            # A small fixed budget; unchecked and failed checks stay explicitly unknown.
            check_papers_retraction(all_papers, max_checks=3)
            checkpoint()
            emit("log", "Synthesizing evidence. Verify generated claims against the linked papers.")
            synthesis = generate_structured_synthesis(
                all_papers, history, progress_callback=lambda msg: emit("log", msg)
            )
            checkpoint()
            if (
                not isinstance(synthesis, dict)
                or not isinstance(synthesis.get("overview"), str)
                or not synthesis["overview"].strip()
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
                "elapsed_seconds": round(time.monotonic() - started, 1),
            }
            payload["session_id"] = save_research_session(user_id, req.query, payload)
            emit("complete", payload)
        except InterruptedError:
            pass
        except Exception as exc:
            logger.exception("Research job failed")
            if not stopped.is_set():
                try:
                    events.put_nowait(
                        {
                            "event": "message",
                            "data": json.dumps(
                                {
                                    "type": "error",
                                    "data": str(exc)
                                    if isinstance(exc, (ValueError, TimeoutError))
                                    else "Research could not finish. Check source availability and AI configuration, then retry.",
                                }
                            ),
                        }
                    )
                except queue.Full:
                    pass
        finally:
            close_connection()
            with _lock:
                _users.discard(user_id)
                _slots.release()
            try:
                events.put_nowait(None)
            except queue.Full:
                stopped.set()

    threading.Thread(target=work, daemon=True, name=f"research-{user_id}").start()

    async def stream():
        try:
            while not stopped.is_set():
                if await request.is_disconnected():
                    break
                if time.monotonic() >= deadline:
                    yield {
                        "event": "message",
                        "data": json.dumps(
                            {
                                "type": "error",
                                "data": "Research timed out. Try a narrower question.",
                            }
                        ),
                    }
                    break
                try:
                    item = await asyncio.to_thread(events.get, True, 0.25)
                    if item is None:
                        break
                    yield item
                except queue.Empty:
                    continue
        finally:
            # In-flight HTTP requests finish with their own timeout; no subsequent stage runs.
            stopped.set()

    return EventSourceResponse(stream(), ping=15)
