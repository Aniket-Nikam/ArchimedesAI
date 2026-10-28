"""Conservative Crossref metadata checks. Unknown is never reported as safe."""

from datetime import UTC, datetime
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
            primary = check_retraction_by_doi(doi)
            observations = [{"source": "Crossref", "status": primary.get("status", "unknown")}]
            secondary = unknown("OpenAlex lookup unavailable")
            if primary.get("is_retracted") is not True:
                try:
                    response = resilient_request(
                        f"https://api.openalex.org/works/https://doi.org/{quote(doi, safe='/')}?select=id,doi,is_retracted",
                        max_retries=1,
                        timeout=5,
                    )
                    if response is not None and response.status_code == 200:
                        value = response.json().get("is_retracted")
                        if isinstance(value, bool):
                            secondary = {
                                "is_retracted": value,
                                "status": "retracted" if value else "no_notice_found",
                            }
                except (ValueError, TypeError, AttributeError):
                    pass
                observations.append({"source": "OpenAlex", "status": secondary["status"]})
            flagged = primary.get("is_retracted") is True or secondary.get("is_retracted") is True
            fully_checked = (
                primary.get("is_retracted") is False and secondary.get("is_retracted") is False
            )
            paper["retraction_status"] = {
                "is_retracted": True if flagged else False if fully_checked else None,
                "status": "retracted"
                if flagged
                else "no_notice_found"
                if fully_checked
                else "unknown",
                "retraction_reason": "Retraction metadata flagged"
                if flagged
                else "No notice in queried records; this is not proof of safety"
                if fully_checked
                else "Incomplete retraction metadata; verify original sources",
                "observations": observations,
                "checked_at": datetime.now(UTC).isoformat(),
            }
            checked += 1
    return papers
