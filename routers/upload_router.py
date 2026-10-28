import logging

import pymupdf as fitz
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from ai.groq_service import analyze_paper_claims, extract_paper_metadata
from api.arxiv_client import search_arxiv
from api.semantic_scholar_client import search_semantic_scholar
from services.ai_jobs import ai_job

router = APIRouter()
logger = logging.getLogger(__name__)

MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB


@router.post("/")
def upload_and_analyze(file: UploadFile = File(...), user_id: int | None = Form(None)):
    """
    Upload a PDF paper for analysis.
    Extracts text, identifies claims, finds related work, and verifies claims.
    """
    if not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    content = file.file.read(MAX_FILE_SIZE + 1)
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large (max 20MB)")

    try:
        # Step 1: Extract text from PDF
        with fitz.open(stream=content, filetype="pdf") as doc:
            pages = len(doc)
            if pages > 100:
                raise HTTPException(400, "PDF must contain at most 100 pages")
            text = "".join(page.get_text() for page in doc)[:200000]

        if len(text.strip()) < 100:
            raise HTTPException(status_code=400, detail="Could not extract text from PDF")

        # Step 2: Extract metadata using AI
        with ai_job():
            metadata = extract_paper_metadata(text)
        if not metadata:
            metadata = {
                "title": file.filename.replace(".pdf", ""),
                "abstract": text[:500],
                "key_claims": [],
                "methodology": "Unknown",
                "keywords": [],
            }

        # Step 3: Search for related papers
        search_query = metadata.get("title", "") + " " + " ".join(metadata.get("keywords", []))
        related_ss = search_semantic_scholar(search_query[:200], max_results=6)
        related_arx = search_arxiv(search_query[:200], max_results=4)
        related_papers = related_ss + related_arx

        # Step 4: Analyze claims against related literature
        with ai_job():
            claim_analysis = analyze_paper_claims(text, related_papers)

        return JSONResponse(
            {
                "metadata": metadata,
                "related_papers": related_papers,
                "claim_analysis": claim_analysis,
                "text_length": len(text),
                "pages": pages,
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"PDF analysis failed: {e}")
        raise HTTPException(
            status_code=400,
            detail="Could not analyze this PDF. Check that it is a readable, unencrypted PDF.",
        )
