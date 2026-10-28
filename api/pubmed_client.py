"""PubMed E-utilities over the shared HTTP client, with bounded request timeouts."""

import logging
from urllib.parse import urlencode
from xml.etree import ElementTree as ET

from api.api_utils import resilient_request
from services.cache_service import get_cached, set_cached

logger = logging.getLogger(__name__)
CACHE_SOURCE = "pubmed"
BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"


def search_pubmed(query, max_results=2):
    key = f"{max_results}:{query}"
    cached = get_cached(key, CACHE_SOURCE)
    if cached is not None:
        return cached
    papers = []
    try:
        response = resilient_request(
            BASE
            + "esearch.fcgi?"
            + urlencode(
                {
                    "db": "pubmed",
                    "term": query,
                    "retmax": max_results,
                    "retmode": "json",
                    "tool": "ArchimedesAI",
                }
            )
        )
        if response is None or response.status_code != 200:
            return papers
        ids = response.json().get("esearchresult", {}).get("idlist", [])
        if not ids:
            return papers
        response = resilient_request(
            BASE
            + "efetch.fcgi?"
            + urlencode(
                {"db": "pubmed", "id": ",".join(ids), "retmode": "xml", "tool": "ArchimedesAI"}
            )
        )
        if response is None or response.status_code != 200:
            return papers
        for item in ET.fromstring(response.content).findall("PubmedArticle"):
            article = item.find("MedlineCitation/Article")
            if article is None:
                continue
            title = article.find("ArticleTitle")
            if title is None:
                continue
            pmid = item.findtext("MedlineCitation/PMID", "")
            doi = next(
                (
                    node.text
                    for node in item.findall("PubmedData/ArticleIdList/ArticleId")
                    if node.get("IdType") == "doi"
                ),
                None,
            )
            papers.append(
                {
                    "id": f"PMID:{pmid}",
                    "title": "".join(title.itertext()),
                    "authors": [
                        " ".join(filter(None, (a.findtext("ForeName"), a.findtext("LastName"))))
                        or a.findtext("CollectiveName", "")
                        for a in article.findall("AuthorList/Author")
                    ],
                    "year": article.findtext("Journal/JournalIssue/PubDate/Year", "N/A"),
                    "abstract": " ".join(
                        "".join(a.itertext()) for a in article.findall("Abstract/AbstractText")
                    ),
                    "doi": doi,
                    "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                    "source": "PubMed",
                }
            )
        if papers:
            set_cached(key, CACHE_SOURCE, papers)
    except (ValueError, ET.ParseError, TypeError, AttributeError):
        logger.warning("PubMed returned an unreadable response")
    return papers
