# ArchimedesAI

A full-stack academic research workspace: discover papers, follow citation links, compare findings, save a reading list, and draft manuscript sections with AI assistance.

React 19 / TypeScript / Vite frontend; FastAPI / SQLite backend; Groq for language-model inference.

## Run locally

Use Python 3.12 and Node.js 24.

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt -c requirements.lock
Copy-Item .env.example .env
```

Set your own Groq key in the local `.env` file. Never commit it. No API key is needed to test sign-in, history, bookmarks, exports, or the automated suite. Research synthesis and AI utility tools return a clear 503 when the key is missing.

```powershell
cd frontend
npm ci
npm run build
cd ..
.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000
```

Open [the research workspace](http://127.0.0.1:8000). FastAPI serves the built frontend and API on the same origin. For frontend development, run `npm run dev` in `frontend` while the backend runs on port 8000; Vite proxies `/api`.

## Research workflow

1. Sign in through an expiring, revocable, HttpOnly cookie session.
2. Ask a research question. Semantic Scholar, arXiv and PubMed run in parallel.
3. Deduplicate source results and trace Semantic Scholar citation links up to two levels when available.
4. Inspect source coverage, limited Crossref/OpenAlex retraction metadata, and AI-assisted synthesis. Named titles are looked up separately; missing citation links are explained without inventing relationships.
5. Reopen saved reports, bookmark papers, and export BibTeX, CSV, APA-style text or RIS.
6. Use bookmarked papers in Manuscript Studio, generate an extraction matrix, or upload a readable PDF.

Google Scholar is an **optional experimental adapter**, disabled by default. Install `requirements-scholar.txt` and set `ENABLE_GOOGLE_SCHOLAR=1` to opt in. It depends on scraping and is not covered by the default release verification.

## Verification

```powershell
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m ruff check auth api ai db routers services utils main.py tests
.venv\Scripts\python.exe -m ruff format --check auth api ai db routers services utils main.py tests
cd frontend
npm test
npm run lint
npm run build
```

The Python suite uses a separate database under `data/tests` and fake providers. It never uses real credentials or developer research. The stream tests exercise arbitrary chunk boundaries, split Unicode, malformed responses and cancellation.

The [earlier automated report](docs/TEST_REPORT.md) is historical. Current live-browser evidence is in [the user study](docs/user-study/), with an illustrated walkthrough under `output/pdf/`. The current suite includes durable-job recovery, cross-process limits, backup restoration, storage failures and bounded input fuzzing.

## Deployment and data

- Research admission, authentication rate windows and utility leases are coordinated through SQLite. Research runs in isolated worker subprocesses with persisted events and bounded recovery. This is for one machine sharing the same SQLite data directory; distributed hosting remains unverified.
- Put HTTPS in front of the app and set `COOKIE_SECURE=1`. Set `ALLOWED_ORIGINS` to your own frontend origin. Configure a reverse-proxy body-size limit (25 MB maximum for uploads, a lower limit for JSON APIs).
- Keep the SQLite data directory on persistent storage and back it up before upgrades. `ARCHIMEDES_DATA_DIR` changes its location.
- Existing integer user IDs, bcrypt passwords, bookmarks and research history are preserved. Startup applies additive, idempotent SQL migrations from `db/migrations`. Each has a corresponding downgrade file; rolling back sessions signs all browsers out.
- Limits, model overrides and optional source configuration are documented in [.env.example](.env.example).
- The original Streamlit entry point is legacy code. The supported application starts at `main:app`.

## Practical limits

This is a research aid, not a systematic-review or publication-validation service. Retrieval is bounded and source coverage varies. A source that returns no data may be empty, rate-limited or unavailable; the UI preserves that uncertainty.

Crossref metadata is incomplete. “No notice found” does not establish that a paper is safe; failed and unperformed checks remain **unknown**. AI can misread abstracts and invent claims or citations despite a review pass. Read and verify the original papers before using generated findings or drafts.

Stopping research terminates the owned subprocess; workers also monitor persisted cancellation and deadlines. A restarted dispatcher can recover an expired worker lease, with up to three attempts within the original deadline. Recovery restarts computation rather than resuming an individual provider request. Browser reloads reconnect to persisted events. PDF analysis examines text excerpts and supports at most 20 MB / 100 pages; scanned PDFs need OCR outside this app.

On Windows, an optional current-user DPAPI encrypted Groq credential can be stored under the ignored `data/secrets` directory. An explicit `GROQ_API_KEY` environment value takes precedence. Never commit plaintext or encrypted credentials.

Create and verify SQLite snapshots with `python scripts/database_backup.py backup SOURCE.db NEW_BACKUP.db`. Restore with `python scripts/database_backup.py restore BACKUP.db NEW_RESTORED.db`; retain the checksum sidecar. Restoration refuses existing destinations. Stop the app and deliberately select the restored data directory before using it. See [operations and verification limits](docs/OPERATIONS_REVIEW.md).
