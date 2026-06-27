"""
Retraction checker — queries CrossRef and OpenRetractions APIs
to detect if papers have been retracted.
"""
import logging
from api.api_utils import resilient_request

logger = logging.getLogger(__name__)


def check_retraction_by_doi(doi):
    """
    Check if a paper with a given DOI has been retracted via CrossRef.
    Returns { is_retracted, retraction_date, retraction_reason } or None.
    """
    if not doi:
        return None
    try:
        url = f"https://api.crossref.org/works/{doi}"
        res = resilient_request(url, max_retries=2, timeout=8)
        if res and res.status_code == 200:
            data = res.json()
            message = data.get("message", {})
            # Check if the paper type indicates retraction
            update_to = message.get("update-to", [])
            for update in update_to:
                if update.get("type") == "retraction":
                    return {
                        "is_retracted": True,
                        "retraction_date": update.get("updated", {}).get("date-parts", [[]])[0],
                        "retraction_reason": "Retracted (via CrossRef)"
                    }
            # Also check if this paper itself is a retraction notice
            if "retraction" in str(message.get("type", "")).lower():
                return {
                    "is_retracted": True,
                    "retraction_date": None,
                    "retraction_reason": "This is a retraction notice"
                }
        return {"is_retracted": False}
    except Exception as e:
        logger.warning(f"Retraction check failed for DOI {doi}: {e}")
        return None


def check_retraction_by_title(title):
    """
    Check if a paper has been retracted using title-based search via OpenRetractions API.
    Falls back to a CrossRef title search to find the DOI first.
    """
    if not title or len(title) < 10:
        return None
    try:
        # Try OpenRetractions API first
        url = f"https://openretractions.com/api/doi?title={title[:200]}"
        res = resilient_request(url, max_retries=1, timeout=6)
        if res and res.status_code == 200:
            data = res.json()
            if data and isinstance(data, list) and len(data) > 0:
                return {
                    "is_retracted": True,
                    "retraction_date": data[0].get("timestamp"),
                    "retraction_reason": data[0].get("type", "Retracted")
                }
    except Exception:
        pass
    
    return {"is_retracted": False}


def check_papers_retraction(papers, max_checks=15):
    """
    Batch check a list of papers for retractions.
    Adds 'retraction_status' field to each paper dict.
    Limits checks to avoid API abuse.
    """
    checked = 0
    for paper in papers:
        if checked >= max_checks:
            break
        
        # Try DOI-based check first (more reliable)
        url = paper.get("url", "")
        doi = None
        if "doi.org" in url:
            doi = url.split("doi.org/")[-1]
        elif "semanticscholar" in url and paper.get("id"):
            # Semantic Scholar papers — try their DOI field
            doi = paper.get("doi")
        
        result = None
        if doi:
            result = check_retraction_by_doi(doi)
        
        if result is None:
            result = check_retraction_by_title(paper.get("title", ""))
        
        if result:
            paper["retraction_status"] = result
        else:
            paper["retraction_status"] = {"is_retracted": False}
        
        checked += 1
    
    return papers
