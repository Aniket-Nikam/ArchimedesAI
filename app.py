import streamlit as st
from groq import Groq
import requests
import feedparser
import fitz
import re

st.title("Archimedes")

client = Groq(api_key=st.secrets["GROQ_API_KEY"])

# default model
if "model" not in st.session_state:
    st.session_state.model = "openai/gpt-oss-120b"

# chat history
if "messages" not in st.session_state:
    st.session_state.messages = []


# -------- arXiv search --------
def search_arxiv(query, max_results=5):

    url = f"http://export.arxiv.org/api/query?search_query=all:{query}&start=0&max_results={max_results}"

    response = requests.get(url)

    feed = feedparser.parse(response.text)

    papers = []

    for entry in feed.entries:
        papers.append({
            "title": entry.title,
            "summary": entry.summary,
            "link": entry.link
        })

    return papers


# -------- topic extraction --------
def extract_topics(prompt):

    response = client.chat.completions.create(
        model=st.session_state.model,
        messages=[
            {"role": "system",
             "content": "Extract 3 research keywords from this query. Return only keywords separated by commas."},
            {"role": "user", "content": prompt}
        ]
    )

    return response.choices[0].message.content


# -------- get arxiv id --------
def get_arxiv_id(link):

    match = re.search(r'arxiv.org/abs/(.*)', link)

    if match:
        return match.group(1)

    return None


# -------- extract references from pdf --------
def extract_references(arxiv_id, limit=15):

    pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"

    response = requests.get(pdf_url)

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


# -------- search arxiv for reference --------
def search_reference_on_arxiv(reference):

    # remove citation number
    reference = re.sub(r"\[\d+\]", "", reference)

    # search using first 10 words
    words = reference.split()[:10]
    query = " ".join(words)

    results = search_arxiv(query, max_results=1)

    if results:
        return results[0]

    return None


# -------- display previous chat --------
for message in st.session_state.messages:

    with st.chat_message(message["role"]):
        st.markdown(message["content"])


# -------- user input --------
if prompt := st.chat_input("Ask a research question"):

    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):

        # extract topics
        topics = extract_topics(prompt)

        st.markdown("### Detected Topics")
        st.write(topics)

        # search arxiv
        papers = search_arxiv(topics)

        paper_text = ""

        st.markdown("## Relevant Papers")

        for paper in papers:

            st.subheader(paper["title"])
            st.write(paper["summary"])
            st.markdown(f"[Read paper]({paper['link']})")

            st.markdown("### Citation Trail")

            arxiv_id = get_arxiv_id(paper["link"])

            if arxiv_id:

                refs = extract_references(arxiv_id)

                if refs:

                    for ref in refs[:5]:

                        ref_paper = search_reference_on_arxiv(ref)

                        if ref_paper:

                            st.markdown(
                                f"- **{ref_paper['title']}**  \n"
                                f"  [{ref_paper['link']}]({ref_paper['link']})"
                            )

                        else:
                            st.markdown(f"- {ref}")

                else:
                    st.write("No references detected")

            st.markdown("---")

            paper_text += paper["title"] + "\n" + paper["summary"] + "\n"

        # summarize
        response = client.chat.completions.create(
            model=st.session_state.model,
            messages=[
                {"role": "system",
                 "content": "Summarize the research insights from these papers."},
                {"role": "user", "content": paper_text}
            ]
        )

        summary = response.choices[0].message.content

        st.markdown("## Research Summary")
        st.markdown(summary)

    st.session_state.messages.append({"role": "assistant", "content": summary})
