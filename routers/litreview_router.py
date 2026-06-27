from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from services.history_service import get_session_by_id
from ai.groq_service import generate_literature_review

router = APIRouter()


class LitReviewRequest(BaseModel):
    session_id: int
    user_id: int


@router.post("/")
async def create_literature_review(req: LitReviewRequest):
    """Generate a structured literature review from a research session."""
    session = get_session_by_id(req.session_id, req.user_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    report = session.get("report", {})
    all_papers = (
        report.get("seminal", []) +
        report.get("citations", []) +
        report.get("citations_depth2", [])
    )
    
    if not all_papers:
        raise HTTPException(status_code=400, detail="No papers found in this session")
    
    query = report.get("query", session.get("query", ""))
    synthesis = report.get("ai_synthesis")
    
    review = generate_literature_review(all_papers, query, synthesis)
    
    return PlainTextResponse(
        content=review,
        media_type="text/markdown",
        headers={"Content-Disposition": f"attachment; filename=literature_review.md"}
    )
