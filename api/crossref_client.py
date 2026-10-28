"""Conservative exact-title discovery using Crossref bibliographic metadata."""

import re
from html import unescape
from urllib.parse import urlencode

from api.api_utils import resilient_request
from services.search_intent import title_score


def search_crossref_title(title, limit=3):
    response = resilient_request(
        "https://api.crossref.org/works?"
        + urlencode({"query.title": title, "rows": min(limit, 3)}),
        max_retries=1,
        timeout=8,
    )
    if response is None or response.status_code != 200:
        return []
    papers = []
    for item in response.json().get("message", {}).get("items", []):
        paper = {"title": (item.get("title") or [""])[0]}
        if title_score(paper, title) != 2:
            continue
        dates = item.get("published", {}).get("date-parts", [[]])
        paper.update(
            id="DOI:" + item["DOI"],
            doi=item["DOI"],
            url="https://doi.org/" + item["DOI"],
            source="Crossref",
            authors=[
                " ".join(filter(None, (a.get("given"), a.get("family"))))
                for a in item.get("author", [])
            ],
            year=dates[0][0] if dates and dates[0] else "N/A",
            abstract=unescape(re.sub("<[^>]+>", " ", item.get("abstract", ""))).strip(),
        )
        papers.append(paper)
    return papers
