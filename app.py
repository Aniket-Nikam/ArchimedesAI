import streamlit as st
from streamlit_chat import message
import arxiv
import requests
import time
import re
import fitz
from scholarly import scholarly
from Bio import Entrez
import os
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

try:
    groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
except Exception:
    groq_client = None

# --- Setup Page ---
st.set_page_config(page_title="Autonomous Research Agent", page_icon="🧬", layout="wide")

# --- Custom CSS for Premium Look ---
st.markdown("""
<style>
    /* Main Layout */
    .block-container {
        max-width: 1000px !important;
        padding-top: 2rem !important;
        padding-bottom: 6rem !important;
    }
    header {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Agent Status Logs */
    .agent-log {
        font-family: 'Courier New', Courier, monospace;
        font-size: 0.85rem;
        color: #a3b1c6;
        margin-bottom: 0.2rem;
    }
    .agent-log-highlight {
        color: #58a6ff;
        font-weight: bold;
    }

    /* Knowledge Graph / Report Cards */
    .report-section {
        background: #161b22;
        border: 1px solid #30363d;
        border-radius: 8px;
        padding: 1.5rem;
        margin-top: 1rem;
        margin-bottom: 1rem;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    .report-title {
        color: #8b5cf6;
        font-size: 1.2rem;
        font-weight: bold;
        margin-bottom: 1rem;
        border-bottom: 1px solid #30363d;
        padding-bottom: 0.5rem;
    }
    .paper-box {
        background: #0d1117;
        border-left: 3px solid #3b82f6;
        padding: 1rem;
        margin-bottom: 0.8rem;
        border-radius: 4px;
    }
    .badge {
        display: inline-block;
        padding: 0.2rem 0.5rem;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: bold;
        margin-right: 0.5rem;
        margin-top: 0.5rem;
    }
    .badge-seminal { background: #1f2937; color: #58a6ff; border: 1px solid #58a6ff; }
    .badge-contradiction { background: #2d1515; color: #f85149; border: 1px solid #f85149; }
    .badge-gap { background: #1c2e1f; color: #3fb950; border: 1px solid #3fb950; }

</style>
""", unsafe_allow_html=True)

st.title("🧬 Autonomous Research Agent")
st.markdown("I act as your junior researcher. Give me a topic, and I will **autonomously fan out** across *arXiv* and *Semantic Scholar*, follow citation trails, build a knowledge graph, and surface contradictions & research gaps.")

# --- API Modules ---
def search_arxiv(query, max_results=2):
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
    except Exception as e:
        pass
    return papers

def search_semantic_scholar(query, max_results=2):
    url = f"https://api.semanticscholar.org/graph/v1/paper/search?query={query}&limit={max_results}&fields=paperId,title,authors,year,citationCount,abstract"
    papers = []
    try:
        res = requests.get(url, timeout=10).json()
        if 'data' in res:
            for p in res['data']:
                papers.append({
                    "id": p.get('paperId'),
                    "title": p.get('title'),
                    "authors": [a.get('name') for a in p.get('authors', [])],
                    "year": p.get('year'),
                    "citations": p.get('citationCount', 0),
                    "abstract": p.get('abstract', ''),
                    "source": "Semantic Scholar"
                })
    except Exception as e:
        pass
    return papers

def get_citations(paper_id, limit=3):
    url = f"https://api.semanticscholar.org/graph/v1/paper/{paper_id}/citations?limit={limit}&fields=title,authors,year"
    citations = []
    try:
        res = requests.get(url, timeout=10).json()
        if 'data' in res:
            for c in res['data']:
                p = c.get('citingPaper', {})
                if p and p.get('title'):
                    citations.append({
                        "id": p.get('paperId'),
                        "title": p.get('title'),
                        "year": p.get('year')
                    })
    except Exception as e:
        pass
    return citations

def search_pubmed(query, max_results=2):
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
                            
                papers.append({
                    "title": title,
                    "authors": authors,
                    "year": year,
                    "abstract": abstract_text,
                    "source": "PubMed"
                })
    except Exception as e:
        pass
    return papers

def search_google_scholar(query, max_results=2):
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
                "source": "Google Scholar"
            })
    except Exception as e:
        pass
    return papers

FALLBACK_MODELS = [
    "llama-3.1-8b-instant",
    "meta-llama/llama-4-scout-17b-16e-instruct",
    "meta-llama/llama-prompt-guard-2-22m",
    "moonshotai/kimi-k2-instruct"
]

def extract_topics(chat_history):
    if not groq_client: return chat_history[-1]['content']
    
    history_str = ""
    for msg in chat_history[-4:]:
        # Avoid putting massive assistant messages in the topic extraction context if not needed, just the user ones are mostly fine, but we'll put both:
        content_snippet = str(msg.get("content", ""))[:200]
        history_str += f"{msg['role']}: {content_snippet}\n"

    for model in FALLBACK_MODELS:
        try:
            response = groq_client.chat.completions.create(
                model=model,
                temperature=0.0,
                messages=[
                    {"role": "system", "content": "You are a query extractor. Based on the conversation history, extract 3-4 optimal core research keywords/phrases to use in an academic search engine to find the papers the user is asking about. Return ONLY the keywords separated by spaces. Do not use quotes."},
                    {"role": "user", "content": f"Conversation History:\n{history_str}\n\nExtract keywords for the latest request:"}
                ]
            )
            return response.choices[0].message.content.replace(",", " ")
        except Exception:
            continue
    return chat_history[-1]['content']

def generate_synthesis(papers, chat_history):
    if not groq_client:
        return "Configure your Groq API key in the .env file to enable AI synthesis."
    
    paper_text = ""
    for p in papers[:40]:
        abstract_snippet = p.get('abstract', '')
        if abstract_snippet:
            abstract_snippet = str(abstract_snippet)[:500] + "..."
        else:
            abstract_snippet = "No abstract available."
        paper_text += f"- Title: {p.get('title')} ({p.get('year', 'N/A')})\n  Abstract: {abstract_snippet}\n\n"
        
    history_str = ""
    for msg in chat_history[-4:]:
        history_str += f"{msg['role']}: {str(msg.get('content', ''))}\n"
        
    for model in FALLBACK_MODELS:
        try:
            response = groq_client.chat.completions.create(
                model=model,
                temperature=0.0,
                messages=[
                    {"role": "system", "content": "You are an expert autonomous AI research assistant. Based on the provided list of crawled papers, their abstracts, and the user's conversational history, write a highly detailed 'Synthesis & Contradiction Report' answering the user's specific request. If the user asks a comparative question, focus heavily on that. Dive deep into specific methodologies, datasets, theoretical frameworks, and exact dates/years mentioned in the abstracts. Clearly outline: 1) Areas of methodological convergence, 2) Specific technical conflicts or opposing findings, and 3) Concrete open research gaps. Format your response beautifully using markdown headers, bullet points, and bold text. Ensure exact publishing years and key author details are included when drawing comparisons."},
                    {"role": "user", "content": f"Conversation History:\n{history_str}\n\nDiscovered Papers & Abstracts:\n{paper_text}"}
                ]
            )
            return response.choices[0].message.content
        except Exception:
            continue
    return "Failed to generate AI synthesis after trying all fallback models."

# --- PDF Citation Extractor Tools ---
def get_arxiv_id(link):
    if not link: return None
    match = re.search(r'arxiv.org/(?:abs|pdf)/([^v\.]+)', link)
    if match:
        return match.group(1)
    return None

def extract_references(arxiv_id, limit=5):
    pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
    try:
        response = requests.get(pdf_url, timeout=10)
        doc = fitz.open(stream=response.content, filetype="pdf")
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
    except Exception:
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


# --- Session State ---

# --- Session State ---

if 'chat_history' not in st.session_state:
    st.session_state['chat_history'] = [
        {"role": "assistant", "content": "What complex research question would you like me to deeply analyze today?"}
    ]

# --- Render Chat ---
for message_data in st.session_state['chat_history']:
    if message_data["role"] == "user":
        message(message_data["content"], is_user=True, avatar_style="avataaars", seed="Aneka", key=f"hist_user_{time.time()}")
    else:
        message(message_data["content"], avatar_style="bottts", seed="Felix", key=f"hist_bot_{time.time()}")
        
        # Render the rich report if it exists in the bot message
        if "report" in message_data:
            report = message_data["report"]
            seminal_title = report['seminal'][0]['title'][:30] if len(report.get('seminal', [])) > 0 else "Unknown Seminal Paper"
            citation_title = report['citations'][0]['title'][:30] if len(report.get('citations', [])) > 0 else "recent works"

            st.markdown(f"""
            <div class="report-section">
                <div class="report-title">1. Knowledge Graph & Discovered Papers</div>
                <p style="color: #c9d1d9; font-size: 0.9em;">Autonomously crawled <b>{report['total_crawled']}</b> papers across multiple database layers.</p>
            """, unsafe_allow_html=True)
            
            # Seminal Papers
            st.markdown("<b>Seminal Foundations</b>", unsafe_allow_html=True)
            if report.get("seminal"):
                with st.expander(f"View all {len(report['seminal'])} seminal papers extracted", expanded=True):
                    for p in report["seminal"]:
                        st.markdown(f"""
                        <div class="paper-box">
                            <span class="badge badge-seminal">Seminal</span> <b>{p['title']}</b> ({p.get('year', 'N/A')})<br>
                            <span style="font-size:0.85em; color:#8b949e;">Source: {p.get('source', 'Database')} | Citations: {p.get('citations', 'N/A')}</span>
                        </div>
                        """, unsafe_allow_html=True)
            else:
                st.markdown("<p style='color: #8b949e;'>No seminal papers found.</p>", unsafe_allow_html=True)
                
            # Citation Expansion
            st.markdown("<br><b>Citation Trail Discoveries (Depth 1)</b>", unsafe_allow_html=True)
            if report.get("citations"):
                with st.expander(f"View all {len(report['citations'])} connected citation trails", expanded=False):
                    for c in report["citations"]:
                        st.markdown(f"""
                        <div class="paper-box">
                            🔗 <i>Cites foundational work:</i> <b>{c['title']}</b> ({c.get('year','N/A')})
                        </div>
                        """, unsafe_allow_html=True)
            else:
                st.markdown("<p style='color: #8b949e;'>No citation trails found.</p>", unsafe_allow_html=True)

            st.markdown("</div>", unsafe_allow_html=True)
            
            # Depth-2 citation trails
            if report.get('citations_depth2'):
                st.markdown("<br><b>🔬 Depth-2 Citation Chain (Citations-of-Citations)</b>", unsafe_allow_html=True)
                with st.expander(f"View {len(report['citations_depth2'])} depth-2 linked papers", expanded=False):
                    for c in report['citations_depth2']:
                        st.markdown(f"""
                        <div class="paper-box" style="border-left-color: #f59e0b;">
                            ↳ <i>Extended trail:</i> <b>{c['title']}</b> ({c.get('year','N/A')})
                        </div>
                        """, unsafe_allow_html=True)

            st.markdown("</div>", unsafe_allow_html=True)

            # Elaborate Synthesis & Contradiction Report using native Streamlit
            d1 = len(report.get('citations', []))
            d2 = len(report.get('citations_depth2', []))
            total = report['total_crawled']
            sources_used = list(set([p.get('source', '?') for p in report.get('seminal', [])]))
            key_paper_a = report['seminal'][0]['title'] if len(report.get('seminal', [])) > 0 else 'a seminal work'
            key_paper_b = report['citations'][0]['title'] if len(report.get('citations', [])) > 0 else 'a key citing paper'

            st.markdown("---")
            st.markdown("### 📋 2. Synthesis & Contradiction Report")

            # Stats summary row
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("🗂️ Seminal Papers", len(report.get('seminal', [])))
            col2.metric("🔗 Depth-1 Citations", d1)
            col3.metric("🔬 Depth-2 Chain Nodes", d2)
            col4.metric("📦 Total Crawled", total)

            st.caption(f"Sources: {', '.join(sources_used)}")
            st.divider()

            if report.get('ai_synthesis'):
                st.markdown("### 🤖 Agentic AI Synthesis")
                st.info(report['ai_synthesis'])
                
                st.download_button(
                    label="⬇️ Download Detailed Synthesis Report",
                    data=f"# Research Synthesis Report\n\n**Query:** {report.get('query', 'N/A')}\n\n**Total Papers Crawled:** {total}\n\n---\n\n{report['ai_synthesis']}",
                    file_name="arxival_synthesis_report.md",
                    mime="text/markdown"
                )
            else:
                st.warning("AI Synthesis failed or API key not configured.")



# --- Bottom Input ---
if prompt := st.chat_input("Enter a research query (e.g., 'Transformer attention mechanisms')..."):
    st.session_state['chat_history'].append({"role": "user", "content": prompt})
    st.rerun()

# --- Agentic Execution Logic (Runs if newest msg is user) ---
if len(st.session_state['chat_history']) > 0 and st.session_state['chat_history'][-1]["role"] == "user":
    user_query = st.session_state['chat_history'][-1]["content"]
    
    with st.status("🧠 Agent execution in progress...", expanded=True) as status:
        st.markdown(f"<div class='agent-log'>[System] Initializing autonomous agent for query: <i>\"{user_query}\"</i></div>", unsafe_allow_html=True)
        time.sleep(1)
        
        # 1. Search Cross-Domain Databases
        st.markdown(f"<div class='agent-log'>[System] Asking Groq AI to extract core research keyphrases from conversation context...</div>", unsafe_allow_html=True)
        search_query = extract_topics(st.session_state['chat_history'])
        st.markdown(f"<div class='agent-log'>[System] Extracted optimal search topics: <span class='agent-log-highlight'>{search_query}</span></div>", unsafe_allow_html=True)

        st.markdown(f"<div class='agent-log'>[Crawler] Fanning out to <span class='agent-log-highlight'>Semantic Scholar</span>, <span class='agent-log-highlight'>arXiv</span>, <span class='agent-log-highlight'>PubMed</span>, & <span class='agent-log-highlight'>Google Scholar</span>...</div>", unsafe_allow_html=True)
        seminal_ss = search_semantic_scholar(search_query, max_results=8)
        seminal_arx = search_arxiv(search_query, max_results=5)
        seminal_pubmed = search_pubmed(search_query, max_results=5)
        seminal_gs = search_google_scholar(search_query, max_results=4)
        
        seminal_papers = seminal_ss + seminal_arx + seminal_pubmed + seminal_gs
        
        st.markdown(f"<div class='agent-log'>[Extarctor] Found {len(seminal_papers)} seminal papers across 4 databases.</div>", unsafe_allow_html=True)
        time.sleep(1)
        
        # 2. Depth-1 Citation Trails
        citation_results = []
        crawled_count = len(seminal_papers)
        depth2_citations = []
        
        if len(seminal_ss) > 0:
            target_id = seminal_ss[0]['id']
            st.markdown(f"<div class='agent-log'>[Depth-1] Tracing Semantic Scholar citations for: <i>{seminal_ss[0]['title'][:40]}...</i></div>", unsafe_allow_html=True)
            ss_citations = get_citations(target_id, limit=8)
            for c in ss_citations: c['source'] = 'Semantic Scholar'
            citation_results.extend(ss_citations)
            crawled_count += len(ss_citations)
            time.sleep(0.7)
            
        if len(seminal_arx) > 0:
            arxpath = seminal_arx[0].get('url', '')
            st.markdown(f"<div class='agent-log'>[Depth-1] Scraping PDF references for arXiv paper: <i>{seminal_arx[0]['title'][:40]}...</i></div>", unsafe_allow_html=True)
            arx_id = get_arxiv_id(arxpath)
            
            if arx_id:
                refs = extract_references(arx_id, limit=6)
                for ref_text in refs:
                    ref_paper = search_reference_on_arxiv(ref_text)
                    if ref_paper:
                        citation_results.append(ref_paper)
                        crawled_count += 1
            time.sleep(0.7)

        st.markdown(f"<div class='agent-log'>[Depth-1] Layer 1 complete. <b>{len(citation_results)}</b> citation nodes discovered.</div>", unsafe_allow_html=True)
        time.sleep(0.5)

        # 3. Depth-2 Citation Trails (Citations of Citations)
        ss_d1_with_ids = [c for c in citation_results if c.get('id') and c.get('source') == 'Semantic Scholar']
        if ss_d1_with_ids:
            d2_target = ss_d1_with_ids[0]
            st.markdown(f"<div class='agent-log'>[Depth-2] Drilling deeper — tracing citations of: <i>\"{d2_target['title'][:40]}...\"</i></div>", unsafe_allow_html=True)
            d2_raw = get_citations(d2_target['id'], limit=6)
            for c in d2_raw:
                c['source'] = 'Semantic Scholar (D2)'
                depth2_citations.append(c)
                crawled_count += 1
            time.sleep(0.7)
            
            # Also PDF scrape from the D1 arXiv papers for Depth-2 tracing
            arx_d1_papers = [c for c in citation_results if 'arXiv' in c.get('source', '')]
            if arx_d1_papers:
                d2_arxpath = arx_d1_papers[0].get('url', '')
                st.markdown(f"<div class='agent-log'>[Depth-2] Deep-scraping citations of citations from arXiv: <i>{arx_d1_papers[0]['title'][:40]}...</i></div>", unsafe_allow_html=True)
                d2_arx_id = get_arxiv_id(d2_arxpath)
                
                if d2_arx_id:
                    d2_refs = extract_references(d2_arx_id, limit=4)
                    for ref_text in d2_refs:
                        d2_ref_paper = search_reference_on_arxiv(ref_text)
                        if d2_ref_paper:
                            d2_ref_paper['source'] = 'arXiv (D2)'
                            depth2_citations.append(d2_ref_paper)
                            crawled_count += 1
                time.sleep(0.5)

        st.markdown(f"<div class='agent-log'>[Depth-2] Deep traversal complete. <b>{len(depth2_citations)}</b> additional chain nodes added.</div>", unsafe_allow_html=True)
        time.sleep(0.5)
        st.markdown(f"<div class='agent-log'>[Synthesizer] Synthesizing {crawled_count} nodes using Groq AI...</div>", unsafe_allow_html=True)
        
        all_papers = seminal_papers + citation_results + depth2_citations
        ai_synthesis = generate_synthesis(all_papers, st.session_state['chat_history'])
        
        st.markdown(f"<div class='agent-log'>[System] Analysis complete. Building final structured report.</div>", unsafe_allow_html=True)
        status.update(label=f"✅ Agent finalized — {crawled_count} papers analyzed across 4 databases.", state="complete", expanded=False)
        
    # Generate final report payload
    bot_reply = f"I have autonomously scoured **4 academic databases**, traversed **2 levels of citation chains**, and synthesized **{crawled_count} papers** for your query: *'{user_query}'*. See the structured report below."
    report_payload = {
        "query": user_query,
        "total_crawled": crawled_count,
        "seminal": seminal_papers,
        "citations": citation_results,
        "citations_depth2": depth2_citations,
        "ai_synthesis": ai_synthesis
    }
    
    st.session_state['chat_history'].append({
        "role": "assistant",
        "content": bot_reply,
        "report": report_payload
    })
    
    st.rerun()

