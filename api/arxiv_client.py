import arxiv
import re
import fitz
import logging
from api.api_utils import resilient_request
from services.cache_service import get_cached, set_cached

logger = logging.getLogger(__name__)

CACHE_SOURCE = "arxiv"


def search_arxiv(query, max_results=2):
    # Check cache first
    cached = get_cached(query, CACHE_SOURCE)
    if cached is not None:
        return cached[:max_results]

    client = arxiv.Client()
    search = arxiv.Search(query=query, max_results=max_results, sort_by=arxiv.SortCriterion.Relevance)
    papers = []
    try:
        for r in client.results(search):
            papers.append({
                "title": r.title,
                "authors": [a.name for a in r.authors],
                "year": r.published.year,
                "url": r.pdf_url,
                "abstract": r.summary,
                "source": "arXiv"
            })
        if papers:
            set_cached(query, CACHE_SOURCE, papers)
    except Exception as e:
        logger.error(f"Error searching arXiv for query '{query}': {e}")
    return papers


def get_arxiv_id(link):
    if not link: return None
    match = re.search(r'arxiv.org/(?:abs|pdf)/([^v\.]+)', link)
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
        doc = fitz.open(stream=res.content, filetype="pdf")
        text = ""
        for page in doc:
            text += page.get_text()
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
        results[0]['source'] = 'arXiv (Reference)'
        return results[0]
    return None
