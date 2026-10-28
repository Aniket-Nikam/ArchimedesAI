"""Authenticated durable research jobs with replayable SSE progress."""

import asyncio
import json
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

import config
from auth.sessions import current_user_id
from db.database import get_connection
from services import job_service

router = APIRouter()


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=20000)


class ResearchRequest(BaseModel):
    query: str = Field(min_length=3, max_length=1000)
    user_id: int | None = None
    chat_history: list[ChatMessage] = Field(default_factory=list, max_length=20)
    existing_report: dict | None = None
    mode: Literal["synthesis", "search"] = "synthesis"


def create(req, user_id):
    if req.mode == "synthesis" and not config.GROQ_API_KEY:
        raise HTTPException(
            503,
            "AI research is currently unavailable. Ask the workspace administrator to enable it.",
        )
    if not req.query.strip():
        raise HTTPException(422, "Enter a research question.")
    job = job_service.enqueue(user_id, req.model_dump())
    job_service.dispatch()
    return job


@router.post("/jobs")
def create_job(req: ResearchRequest, user_id: int = Depends(current_user_id)):
    return {"job_id": create(req, user_id)}


@router.get("/jobs/active")
def active_job(user_id: int = Depends(current_user_id)):
    row = (
        get_connection()
        .execute(
            "SELECT id FROM research_jobs WHERE user_id=? AND status IN ('queued','running') ORDER BY created_at DESC LIMIT 1",
            (user_id,),
        )
        .fetchone()
    )
    return job_service.get_job(row["id"], user_id) if row else None


@router.get("/jobs/{job}")
def status(job: str, user_id: int = Depends(current_user_id)):
    return job_service.get_job(job, user_id)


@router.delete("/jobs/{job}")
def cancel(job: str, user_id: int = Depends(current_user_id)):
    return job_service.cancel(job, user_id)


def event_stream(job, request, user_id, after=0):
    job_service.get_job(job, user_id)

    async def events():
        cursor = after
        yield {"event": "message", "data": json.dumps({"type": "job", "data": {"job_id": job}})}
        while not await request.is_disconnected():
            await asyncio.to_thread(job_service.dispatch)
            rows = (
                get_connection()
                .execute(
                    "SELECT id,payload FROM research_job_events WHERE job_id=? AND id>? ORDER BY id LIMIT 100",
                    (job, cursor),
                )
                .fetchall()
            )
            for row in rows:
                cursor = row["id"]
                yield {"event": "message", "id": str(cursor), "data": row["payload"]}
            state = job_service.get_job(job, user_id)
            if state["status"] in {"complete", "cancelled", "error"}:
                # A final read avoids losing the terminal event during a write race.
                tail = (
                    get_connection()
                    .execute(
                        "SELECT id,payload FROM research_job_events WHERE job_id=? AND id>? ORDER BY id",
                        (job, cursor),
                    )
                    .fetchall()
                )
                for row in tail:
                    yield {"event": "message", "id": str(row["id"]), "data": row["payload"]}
                break
            await asyncio.sleep(0.1)

    return EventSourceResponse(events(), ping=10, headers={"X-Accel-Buffering": "no"})


@router.get("/jobs/{job}/events")
async def resume(
    job: str, request: Request, after: int = 0, user_id: int = Depends(current_user_id)
):
    return event_stream(job, request, user_id, after)


@router.post("/")
async def legacy_stream(
    req: ResearchRequest, request: Request, user_id: int = Depends(current_user_id)
):
    return event_stream(create(req, user_id), request, user_id)
