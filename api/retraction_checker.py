"""Conservative Crossref metadata checks. Unknown is never reported as safe."""

from urllib.parse import quote

from api.api_utils import resilient_request


def unknown(reason="No verified retraction metadata available"):
    return {"is_retracted": None, "status": "unknown", "retraction_reason": reason}


def check_retraction_by_doi(doi):
    if not doi:
        return unknown("No DOI available")
    try:
        response = resilient_request(
            f"https://api.crossref.org/works/{quote(doi, safe='/')}", max_retries=1, timeout=5
        )
        if response is None or response.status_code != 200:
            return unknown("Retraction metadata service unavailable")
        message = response.json().get("message", {})
        for update in message.get("update-to", []):
            if update.get("type") == "retraction":
                return {
                    "is_retracted": True,
                    "status": "retracted",
                    "retraction_reason": "Crossref retraction update",
                    "retraction_date": update.get("updated", {}).get("date-parts"),
                }
        if "retraction" in str(message.get("type", "")).lower():
            return {
                "is_retracted": True,
                "status": "retracted",
                "retraction_reason": "Retraction notice",
            }
        # Crossref does not provide exhaustive retraction coverage.
        return {
            "is_retracted": False,
            "status": "no_notice_found",
            "retraction_reason": "No notice in this Crossref record; not a safety guarantee",
        }
    except (ValueError, TypeError, AttributeError):
        return unknown("Retraction metadata could not be read")


def check_retraction_by_title(title):
    # Title-only matching cannot reliably establish that a paper is not retracted.
    return unknown("DOI required for a reliable metadata lookup")


def check_papers_retraction(papers, max_checks=15):
    checked = 0
    for paper in papers:
        doi = paper.get("doi")
        if not doi and "doi.org/" in paper.get("url", ""):
            doi = paper["url"].split("doi.org/", 1)[1]
        paper["retraction_status"] = unknown("Not checked: no DOI or lookup budget exhausted")
        if doi and checked < max_checks:
            paper["retraction_status"] = check_retraction_by_doi(doi)
            checked += 1
    return papers
