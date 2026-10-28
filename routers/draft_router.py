from typing import List

from fastapi import APIRouter
from pydantic import BaseModel, Field

from ai.drafting_service import generate_manuscript_draft
from services.ai_jobs import ai_job

router = APIRouter()


class DraftRequest(BaseModel):
    section: str = Field(min_length=1, max_length=80)
    notes: str = Field(min_length=1, max_length=20000)
    papers: List[dict] = Field(min_length=1, max_length=50)


@router.post("/")
def create_draft(req: DraftRequest):
    with ai_job():
        draft_markdown = generate_manuscript_draft(req.section, req.notes, req.papers)
    return {"draft": draft_markdown}
