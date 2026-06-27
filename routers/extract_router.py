from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
from ai.extraction_service import extract_paper_data

router = APIRouter()

class ExtractRequest(BaseModel):
    papers: List[dict]

@router.post("/")
async def extract_data(req: ExtractRequest):
    extracted = extract_paper_data(req.papers)
    return {"extracted_data": extracted}
