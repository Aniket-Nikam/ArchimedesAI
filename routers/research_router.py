from fastapi import APIRouter, Request
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse
from typing import List, Optional
import json
import asyncio
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from ai.groq_service import (
    extract_topics, generate_structured_synthesis, is_academic_query,
    classify_followup, answer_followup
)
from api.arxiv_client import search_arxiv, get_arxiv_id, extract_references, search_reference_on_arxiv
from api.semantic_scholar_client import search_semantic_scholar, get_citations
from api.pubmed_client import search_pubmed
from api.google_scholar_client import search_google_scholar
from api.retraction_checker import check_papers_retraction
from services.history_service import save_research_session

router = APIRouter()


class ChatMessage(BaseModel):
    role: str
    content: str

class ResearchRequest(BaseModel):
    query: str
    user_id: int
    chat_history: Optional[List[ChatMessage]] = None
    existing_report: Optional[dict] = None

import queue
import threading

@router.post("/")
async def start_research(req: ResearchRequest, request: Request):
    print("Received research request:", req.query)
    q = queue.Queue()

    def background_task():
        def make_event(msg_type, data):
            q.put({
                "event": "message",
                "data": json.dumps({"type": msg_type, "data": data})
            })

        try:
            query = req.query
            start_time = time.time()
            
            # Build chat history
            chat_history = []
            if req.chat_history:
                chat_history = [{"role": m.role, "content": m.content} for m in req.chat_history]
            chat_history.append({"role": "user", "content": query})

            make_event("log", "Checking query intent...")
            if not is_academic_query(query):
                make_event("error", "I'm a specialized autonomous academic research agent. Please ask me a research-related question.")
                return

            # ── Check if this is a follow-up ──
            has_report = req.existing_report is not None
            intent = classify_followup(query, has_report)
            
            if intent in ("followup", "comparison") and req.existing_report:
                make_event("log", f"Processing as {intent} question...")
                make_event("log", "Analyzing existing research data...")
                
                followup_answer = answer_followup(query, req.existing_report, chat_history)
                
                elapsed_seconds = round(time.time() - start_time, 1)
                make_event("log", f"Done in {elapsed_seconds}s.")
                
                make_event("followup_complete", {
                    "answer": followup_answer,
                    "intent": intent,
                    "elapsed_seconds": elapsed_seconds,
                })
                return

            # ── Full research pipeline ──
            make_event("log", "Extracting research keywords from your query...")
            search_query = extract_topics(chat_history)
            make_event("log", f"Keywords: {search_query}")

            # Parallel search across all 4 databases
            make_event("log", "Searching Semantic Scholar, arXiv, PubMed, Google Scholar in parallel...")
            
            seminal_ss = []
            seminal_arx = []
            seminal_pubmed = []
            seminal_gs = []

            with ThreadPoolExecutor(max_workers=4) as executor:
                futures = {
                    executor.submit(search_semantic_scholar, search_query, 8): "ss",
                    executor.submit(search_arxiv, search_query, 5): "arx",
                    executor.submit(search_pubmed, search_query, 5): "pubmed",
                    executor.submit(search_google_scholar, search_query, 4): "gs",
                }
                for future in as_completed(futures):
                    source = futures[future]
                    try:
                        result = future.result()
                        if source == "ss":
                            seminal_ss = result
                        elif source == "arx":
                            seminal_arx = result
                        elif source == "pubmed":
                            seminal_pubmed = result
                        elif source == "gs":
                            seminal_gs = result
                        make_event("log", f"  ✓ {source.upper()} returned {len(result)} papers")
                    except Exception as e:
                        make_event("log", f"  ✗ {source.upper()} failed: {str(e)[:80]}")

            seminal_papers = seminal_ss + seminal_arx + seminal_pubmed + seminal_gs
            make_event("log", f"Found {len(seminal_papers)} papers across 4 databases.")

            citation_results = []
            crawled_count = len(seminal_papers)
            depth2_citations = []

            if seminal_ss:
                target_id = seminal_ss[0]["id"]
                make_event("log", f"Tracing citations for: {seminal_ss[0]['title'][:50]}...")
                ss_citations = get_citations(target_id, limit=8)
                for c in ss_citations:
                    c["source"] = "Semantic Scholar"
                    c["cited_by"] = target_id
                citation_results.extend(ss_citations)
                crawled_count += len(ss_citations)

            if seminal_arx:
                arxpath = seminal_arx[0].get("url", "")
                arx_id = get_arxiv_id(arxpath)
                if arx_id:
                    make_event("log", "Extracting PDF references from arXiv...")
                    refs = extract_references(arx_id, limit=6)
                    for ref_text in refs:
                        ref_paper = search_reference_on_arxiv(ref_text)
                        if ref_paper:
                            ref_paper["cited_by"] = seminal_arx[0].get("id", arx_id)
                            citation_results.append(ref_paper)
                            crawled_count += 1

            make_event("log", f"Depth-1 complete - {len(citation_results)} citations found.")

            ss_d1_with_ids = [c for c in citation_results if c.get("id") and c.get("source") == "Semantic Scholar"]
            if ss_d1_with_ids:
                d2_target = ss_d1_with_ids[0]
                make_event("log", "Going deeper - tracing citations of citations...")
                d2_raw = get_citations(d2_target["id"], limit=6)
                for c in d2_raw:
                    c["source"] = "Semantic Scholar (D2)"
                    c["cited_by"] = d2_target["id"]
                    depth2_citations.append(c)
                    crawled_count += 1

                arx_d1_papers = [c for c in citation_results if "arXiv" in c.get("source", "")]
                if arx_d1_papers:
                    d2_arxpath = arx_d1_papers[0].get("url", "")
                    d2_arx_id = get_arxiv_id(d2_arxpath)
                    if d2_arx_id:
                        d2_refs = extract_references(d2_arx_id, limit=4)
                        for ref_text in d2_refs:
                            d2_ref_paper = search_reference_on_arxiv(ref_text)
                            if d2_ref_paper:
                                d2_ref_paper["source"] = "arXiv (D2)"
                                d2_ref_paper["cited_by"] = arx_d1_papers[0].get("id", d2_arx_id)
                                depth2_citations.append(d2_ref_paper)
                                crawled_count += 1

            make_event("log", f"Depth-2 complete - {len(depth2_citations)} additional papers.")

            # ── Retraction check ──
            all_papers = seminal_papers + citation_results + depth2_citations
            make_event("log", "Checking for retracted papers...")
            try:
                check_papers_retraction(all_papers, max_checks=15)
                retracted = [p for p in all_papers if p.get("retraction_status", {}).get("is_retracted")]
                if retracted:
                    make_event("log", f"  ⚠️ {len(retracted)} retracted paper(s) detected!")
                else:
                    make_event("log", "  ✓ No retractions detected.")
            except Exception as e:
                make_event("log", f"  Retraction check skipped: {str(e)[:60]}")

            make_event("log", "Starting Multi-Agent Peer Review Synthesis...")
            
            def synthesis_progress_callback(msg):
                make_event("log", f"🤖 {msg}")

            ai_synthesis = generate_structured_synthesis(
                all_papers, 
                chat_history, 
                progress_callback=synthesis_progress_callback
            )

            elapsed_seconds = round(time.time() - start_time, 1)
            make_event("log", f"Done - {crawled_count} papers analyzed in {elapsed_seconds}s.")

            report_payload = {
                "query": query,
                "total_crawled": crawled_count,
                "seminal": seminal_papers,
                "citations": citation_results,
                "citations_depth2": depth2_citations,
                "ai_synthesis": ai_synthesis,
                "elapsed_seconds": elapsed_seconds,
            }

            save_research_session(req.user_id, query, report_payload)
            make_event("complete", report_payload)

        except Exception as e:
            make_event("error", f"An error occurred: {str(e)}")
        finally:
            q.put(None)

    threading.Thread(target=background_task, daemon=True).start()

    async def event_generator():
        while True:
            if await request.is_disconnected():
                break
            try:
                item = await asyncio.to_thread(q.get, True, 1.0)
                if item is None:
                    break
                yield item
            except queue.Empty:
                continue
            except asyncio.CancelledError:
                break

    return EventSourceResponse(event_generator())
