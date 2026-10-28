from typing import List

from fastapi import APIRouter
from pydantic import BaseModel, Field

from ai.extraction_service import extract_paper_data
from services.ai_jobs import ai_job

router = APIRouter()


class ExtractRequest(BaseModel):
    papers: List[dict] = Field(min_length=1, max_length=50)


@router.post("/")
def extract_data(req: ExtractRequest):
    with ai_job():
        extracted = extract_paper_data(req.papers)
    return {"extracted_data": extracted}
