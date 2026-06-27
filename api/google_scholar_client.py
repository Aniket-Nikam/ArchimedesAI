from scholarly import scholarly
import logging
from services.cache_service import get_cached, set_cached

logger = logging.getLogger(__name__)

CACHE_SOURCE = "google_scholar"


def search_google_scholar(query, max_results=2):
    # Check cache first
    cached = get_cached(query, CACHE_SOURCE)
    if cached is not None:
        return cached[:max_results]

    papers = []
    try:
        search_query = scholarly.search_pubs(query)
        for i in range(max_results):
            pub = next(search_query, None)
            if not pub:
                break
            papers.append({
                "title": pub.get('bib', {}).get('title', 'No Title'),
                "authors": pub.get('bib', {}).get('author', []),
                "year": pub.get('bib', {}).get('pub_year', 'N/A'),
                "abstract": pub.get('bib', {}).get('abstract', ''),
                "url": pub.get('pub_url', pub.get('eprint_url', '')),
                "source": "Google Scholar"
            })
        if papers:
            set_cached(query, CACHE_SOURCE, papers)
    except Exception as e:
        logger.error(f"Error searching Google Scholar for query '{query}': {e}")
    return papers
