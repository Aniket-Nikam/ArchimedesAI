# 🧬 Archimedes AI

Archimedes is an advanced, autonomous AI research assistant designed to dramatically reduce the cognitive load of conducting academic literature reviews and drafting research papers. By combining agentic search, natural language synthesis, and interactive visualizations, Archimedes allows researchers to move from an initial question to a fully drafted manuscript seamlessly.

## 🚀 How It Works

Archimedes automates the heavy lifting of academic research through a multi-step workflow:
1. **Query Processing**: Simply ask a research question or upload a PDF.
2. **Autonomous Retrieval**: Archimedes searches across primary academic databases (Semantic Scholar, ArXiv, PubMed, Google Scholar) to fetch highly relevant seminal papers.
3. **Citation Tracing (Depth-N)**: The agent autonomously traverses the citation tree, fetching papers that cite the seminal works to map out the current state-of-the-art.
4. **Synthesis & Extraction**: Using advanced LLMs, it synthesizes the abstract findings, extracts key methodologies, identifies glaring research gaps, and highlights contradictions in the literature.
5. **Interactive Visualization**: It automatically plots a responsive **Citation Network** (Knowledge Graph) that you can explore, click, and inspect to visually understand how the research connects.
6. **Manuscript Studio**: Users can directly port these findings and their bookmarked papers into the Manuscript Studio, an integrated drafting environment equipped with AI-assisted writing tools and automatic citation formatting.

## 🛠️ Technology Stack

The application is built on a modern, highly performant stack:
*   **Frontend**: React (with TypeScript), Vite for ultra-fast bundling, `react-force-graph-2d` for the immersive physics-based citation networks, and vanilla CSS with a premium glassmorphic dark-mode UI.
*   **Backend**: Python with **FastAPI** for blazing-fast concurrent asynchronous API requests and server-sent events (SSE) for real-time streaming of research progress.
*   **AI Engine**: Powered by **Groq** for instantaneous, high-throughput LLM inference, making complex literature synthesis happen in seconds rather than minutes.
*   **APIs**: Semantic Scholar API, ArXiv API, PubMed API, Google Scholar, and Retraction Watch for validating paper integrity.

## ✨ Why It's Good

Archimedes goes beyond typical AI chatbots by acting as a true research agent:
*   **Prevents Hallucinations**: Every claim in the synthesis is strictly grounded in real, verifiable academic papers fetched from trusted databases.
*   **Citation Integrity**: Integrates retraction checkers to ensure you aren't citing retracted or compromised papers.
*   **Human-Centric UX**: Features like Context-Aware Citation Hover Cards, Seamless Scroll Memory, and Exploration Tracking in the Knowledge Graph drastically reduce cognitive friction.
*   **All-in-One Workflow**: Instead of keeping 30 tabs open and copying pasting into a Google Doc, Archimedes handles the discovery, analysis, and the drafting phase (Manuscript Studio) all in a single beautiful interface.
