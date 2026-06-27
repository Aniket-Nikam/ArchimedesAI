from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional
from ai.drafting_service import generate_manuscript_draft

router = APIRouter()

class DraftRequest(BaseModel):
    section: str
    notes: str
    papers: List[dict]

@router.post("/")
async def create_draft(req: DraftRequest):
    draft_markdown = generate_manuscript_draft(req.section, req.notes, req.papers)
    return {"draft": draft_markdown}
