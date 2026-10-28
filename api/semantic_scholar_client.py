import logging
from urllib.parse import quote

from api.api_utils import resilient_request
from services.cache_service import get_cached, set_cached

logger = logging.getLogger(__name__)

CACHE_SOURCE = "semantic_scholar"


def search_semantic_scholar(query, max_results=2):
    # Check cache first
    cached = get_cached(f"{max_results}:{query}", CACHE_SOURCE)
    if cached is not None:
        return cached[:max_results]

    url = f"https://api.semanticscholar.org/graph/v1/paper/search?query={quote(query, safe='')}&limit={max_results}&fields=paperId,title,authors,year,citationCount,abstract,url,externalIds"
    papers = []
    try:
        res = resilient_request(url)
        if res is None:
            return papers
        res.raise_for_status()
        data = res.json()
        if "data" in data:
            for p in data["data"]:
                papers.append(
                    {
                        "id": p.get("paperId"),
                        "doi": (p.get("externalIds") or {}).get("DOI"),
                        "title": p.get("title"),
                        "authors": [a.get("name") for a in p.get("authors", [])],
                        "year": p.get("year"),
                        "citations": p.get("citationCount", 0),
                        "abstract": p.get("abstract", ""),
                        "url": p.get("url", ""),
                        "source": "Semantic Scholar",
                    }
                )
        if papers:
            set_cached(f"{max_results}:{query}", CACHE_SOURCE, papers)
    except Exception as e:
        logger.error(f"Error searching Semantic Scholar for query '{query}': {e}")
    return papers


def get_citations(paper_id, limit=3):
    url = f"https://api.semanticscholar.org/graph/v1/paper/{paper_id}/citations?limit={limit}&fields=title,authors,year,url,citationCount,abstract"
    citations = []
    try:
        res = resilient_request(url)
        if res is None:
            return citations
        res.raise_for_status()
        data = res.json()
        if "data" in data:
            for c in data["data"]:
                p = c.get("citingPaper", {})
                if p and p.get("title"):
                    citations.append(
                        {
                            "id": p.get("paperId"),
                            "title": p.get("title"),
                            "authors": [a.get("name") for a in p.get("authors", [])]
                            if p.get("authors")
                            else [],
                            "year": p.get("year"),
                            "citations": p.get("citationCount", 0),
                            "abstract": p.get("abstract", ""),
                            "url": p.get("url", ""),
                        }
                    )
    except Exception as e:
        logger.error(f"Error fetching citations for Semantic Scholar paper '{paper_id}': {e}")
    return citations
