import logging
import re
from urllib.parse import urlencode
from xml.etree import ElementTree as ET

import pymupdf as fitz

from api.api_utils import resilient_request
from services.cache_service import get_cached, set_cached

logger = logging.getLogger(__name__)

CACHE_SOURCE = "arxiv"


def search_arxiv(query, max_results=2):
    # Check cache first
    cached = get_cached(f"{max_results}:{query}", CACHE_SOURCE)
    if cached is not None:
        return cached[:max_results]

    papers = []
    try:
        response = resilient_request(
            "https://export.arxiv.org/api/query?"
            + urlencode({"search_query": query, "max_results": max_results, "sortBy": "relevance"})
        )
        if response is None or response.status_code != 200:
            return papers
        ns = {"a": "http://www.w3.org/2005/Atom"}
        for entry in ET.fromstring(response.content).findall("a:entry", ns):
            identifier = entry.findtext("a:id", "", ns)
            papers.append(
                {
                    "id": identifier,
                    "title": " ".join(entry.findtext("a:title", "", ns).split()),
                    "authors": [
                        a.findtext("a:name", "", ns) for a in entry.findall("a:author", ns)
                    ],
                    "year": entry.findtext("a:published", "", ns)[:4],
                    "url": identifier,
                    "abstract": entry.findtext("a:summary", "", ns),
                    "source": "arXiv",
                }
            )
        if papers:
            set_cached(f"{max_results}:{query}", CACHE_SOURCE, papers)
    except Exception as e:
        logger.error(f"Error searching arXiv for query '{query}': {e}")
    return papers


def get_arxiv_id(link):
    if not link:
        return None
    match = re.search(r"arxiv\.org/(?:abs|pdf)/(.+?)(?:v\d+)?(?:\.pdf)?(?:[?#].*)?$", link)
    if match:
        return match.group(1)
    return None


def extract_references(arxiv_id, limit=5):
    pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
    try:
        res = resilient_request(pdf_url, timeout=15)
        if res is None:
            return []
        res.raise_for_status()
        with fitz.open(stream=res.content, filetype="pdf") as doc:
            text = "".join(page.get_text() for page in doc)
        match = re.search(r"(REFERENCES|References)(.*)", text, re.DOTALL)
        if not match:
            return []
        refs_text = match.group(2)
        lines = refs_text.split("\n")
        refs = []
        current_ref = ""
        for line in lines:
            line = line.strip()
            if re.match(r"\[\d+\]", line):
                if current_ref:
                    refs.append(current_ref)
                current_ref = line
            else:
                current_ref += " " + line
        if current_ref:
            refs.append(current_ref)
        return refs[:limit]
    except Exception as e:
        logger.error(f"Error extracting references from arXiv ID '{arxiv_id}': {e}")
        return []


def search_reference_on_arxiv(reference):
    reference = re.sub(r"\[\d+\]", "", reference).strip()
    words = reference.split()[:8]
    query = " ".join(words)
    results = search_arxiv(query, max_results=1)
    if results:
        results[0]["source"] = "arXiv (Reference)"
        return results[0]
    return None
