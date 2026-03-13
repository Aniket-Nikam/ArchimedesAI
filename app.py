import streamlit as st
from groq import Groq
import requests
import feedparser

st.title("Archimedes")

client = Groq(api_key=st.secrets["GROQ_API_KEY"])

# default model
if "model" not in st.session_state:
    st.session_state.model = "llama-3.3-70b-versatile"

# chat history
if "messages" not in st.session_state:
    st.session_state.messages = []


# -------------------------
# Extract research topics
# -------------------------
def extract_topics(prompt):

    response = client.chat.completions.create(
        model=st.session_state.model,
        messages=[
            {
                "role": "system",
                "content": "Extract 3 research keywords from this query. Return only comma separated keywords."
            },
            {"role": "user", "content": prompt}
        ]
    )

    return response.choices[0].message.content


# -------------------------
# arXiv search
# -------------------------
def search_arxiv(query, max_results=5):

    url = (
        "http://export.arxiv.org/api/query?"
        f"search_query=all:{query}&start=0&max_results={max_results}"
    )

    response = requests.get(url)

    feed = feedparser.parse(response.text)

    papers = []

    for entry in feed.entries:

        authors = [a.name for a in entry.authors]

        papers.append({
            "title": entry.title,
            "summary": entry.summary,
            "link": entry.link,
            "authors": authors
        })

    return papers


# -------------------------
# Display chat history
# -------------------------
for message in st.session_state.messages:

    with st.chat_message(message["role"]):
        st.markdown(message["content"])


# -------------------------
# Chat input
# -------------------------
if prompt := st.chat_input("Ask a research question"):

    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):

        # Extract topics
        topics = extract_topics(prompt)

        st.markdown(f"**Detected topics:** {topics}")

        # Search papers
        papers = search_arxiv(topics, 5)

        st.markdown("## 📄 Papers")

        for i, paper in enumerate(papers, 1):

            st.subheader(f"{i}. {paper['title']}")

            st.write(paper["summary"])

            st.markdown(f"[Read paper]({paper['link']})")

            # show authors (citations)
            st.markdown("### 👨‍🔬 Authors")

            for author in paper["authors"]:
                st.markdown(f"- {author}")

            st.divider()

        full_response = f"Detected topics: {topics}"

    st.session_state.messages.append({"role": "assistant", "content": full_response})
