from Bio import Entrez
import logging
from services.cache_service import get_cached, set_cached

logger = logging.getLogger(__name__)

CACHE_SOURCE = "pubmed"


def search_pubmed(query, max_results=2):
    # Check cache first
    cached = get_cached(query, CACHE_SOURCE)
    if cached is not None:
        return cached[:max_results]

    Entrez.email = "agent@researcher.com"
    papers = []
    try:
        handle = Entrez.esearch(db="pubmed", term=query, retmax=max_results)
        record = Entrez.read(handle)
        handle.close()
        
        id_list = record.get("IdList", [])
        if id_list:
            fetch_handle = Entrez.efetch(db="pubmed", id=",".join(id_list), retmode="xml")
            fetch_record = Entrez.read(fetch_handle)
            fetch_handle.close()
            
            for article in fetch_record.get('PubmedArticle', []):
                medline = article['MedlineCitation']
                article_data = medline['Article']
                title = article_data.get('ArticleTitle', 'No Title')
                
                abstract_text = ""
                if 'Abstract' in article_data and 'AbstractText' in article_data['Abstract']:
                    abs_list = article_data['Abstract']['AbstractText']
                    abstract_text = " ".join([str(a) for a in abs_list])

                # Try to extract year safely
                year = "N/A"
                if 'Journal' in article_data and 'JournalIssue' in article_data['Journal']:
                    pub_date = article_data['Journal']['JournalIssue'].get('PubDate', {})
                    year = pub_date.get('Year', "N/A")
                    
                authors = []
                if 'AuthorList' in article_data:
                    for attr in article_data['AuthorList']:
                        if 'LastName' in attr and 'ForeName' in attr:
                            authors.append(f"{attr.get('ForeName')} {attr.get('LastName')}")
                            
                pmid = str(medline.get('PMID', ''))
                papers.append({
                    "title": title,
                    "authors": authors,
                    "year": year,
                    "abstract": abstract_text,
                    "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else "",
                    "source": "PubMed"
                })
        if papers:
            set_cached(query, CACHE_SOURCE, papers)
    except Exception as e:
        logger.error(f"Error searching PubMed for query '{query}': {e}")
    return papers
