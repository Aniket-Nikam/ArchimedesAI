from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from typing import Literal

from services.history_service import get_session_by_id
from utils.citation_generator import generate_bibtex, generate_csv, generate_apa

router = APIRouter()

class ExportRequest(BaseModel):
    session_id: int
    user_id: int
    format: Literal["bibtex", "csv", "apa"]

@router.post("/")
async def export_papers(req: ExportRequest):
    """Export papers from a research session in BibTeX, CSV, or APA format."""
    session = get_session_by_id(req.session_id, req.user_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    report = session.get("report", {})
    all_papers = (
        report.get("seminal", []) +
        report.get("citations", []) +
        report.get("citations_depth2", [])
    )

    # Deduplicate by title
    seen_titles = set()
    unique_papers = []
    for p in all_papers:
        title = p.get("title", "")
        if title and title not in seen_titles:
            seen_titles.add(title)
            unique_papers.append(p)

    if not unique_papers:
        raise HTTPException(status_code=400, detail="No papers found in this session")

    if req.format == "bibtex":
        content = generate_bibtex(unique_papers)
        return PlainTextResponse(
            content=content,
            media_type="application/x-bibtex",
            headers={"Content-Disposition": f"attachment; filename=archimedes_export.bib"}
        )
    elif req.format == "csv":
        content = generate_csv(unique_papers)
        return PlainTextResponse(
            content=content,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=archimedes_export.csv"}
        )
    elif req.format == "apa":
        apa_lines = [generate_apa(p) for p in unique_papers]
        content = "\n\n".join(apa_lines)
        return PlainTextResponse(
            content=content,
            media_type="text/plain",
            headers={"Content-Disposition": f"attachment; filename=archimedes_export_apa.txt"}
        )
