from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
import fitz
import logging

from ai.groq_service import extract_paper_metadata, analyze_paper_claims
from api.semantic_scholar_client import search_semantic_scholar
from api.arxiv_client import search_arxiv

router = APIRouter()
logger = logging.getLogger(__name__)

MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB


@router.post("/")
async def upload_and_analyze(
    file: UploadFile = File(...),
    user_id: int = Form(...)
):
    """
    Upload a PDF paper for analysis.
    Extracts text, identifies claims, finds related work, and verifies claims.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large (max 20MB)")
    
    try:
        # Step 1: Extract text from PDF
        doc = fitz.open(stream=content, filetype="pdf")
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        
        if len(text.strip()) < 100:
            raise HTTPException(status_code=400, detail="Could not extract text from PDF")
        
        # Step 2: Extract metadata using AI
        metadata = extract_paper_metadata(text)
        if not metadata:
            metadata = {
                "title": file.filename.replace(".pdf", ""),
                "abstract": text[:500],
                "key_claims": [],
                "methodology": "Unknown",
                "keywords": []
            }
        
        # Step 3: Search for related papers
        search_query = metadata.get("title", "") + " " + " ".join(metadata.get("keywords", []))
        related_ss = search_semantic_scholar(search_query[:200], max_results=6)
        related_arx = search_arxiv(search_query[:200], max_results=4)
        related_papers = related_ss + related_arx
        
        # Step 4: Analyze claims against related literature
        claim_analysis = analyze_paper_claims(text, related_papers)
        
        return JSONResponse({
            "metadata": metadata,
            "related_papers": related_papers,
            "claim_analysis": claim_analysis,
            "text_length": len(text),
            "pages": len(fitz.open(stream=content, filetype="pdf")),
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"PDF analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")
