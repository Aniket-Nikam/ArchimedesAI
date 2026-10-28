"""One public query per default source; no AI calls, no developer database."""

import json
import os
import sys
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path


def main():
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT))
    data_root = ROOT / "data" / "source-smoke"
    data_root.mkdir(parents=True, exist_ok=True)
    os.environ["ARCHIMEDES_DATA_DIR"] = tempfile.mkdtemp(dir=data_root)
    os.environ["GROQ_API_KEY"] = ""

    import requests

    from api.arxiv_client import search_arxiv
    from api.pubmed_client import search_pubmed
    from api.semantic_scholar_client import search_semantic_scholar
    from db.database import close_connection, init_db

    init_db()
    close_connection()
    local = threading.local()
    original_get = requests.get

    def tracked_get(*args, **kwargs):
        response = original_get(*args, **kwargs)
        local.statuses.append(response.status_code)
        return response

    requests.get = tracked_get
    query = "retrieval augmented generation"

    def check(item):
        name, function = item
        local.statuses = []
        started = time.monotonic()
        try:
            papers = function(query, 1)
            return {
                "source": name,
                "query": query,
                "requested": 1,
                "returned": len(papers),
                "has_title": bool(papers and papers[0].get("title")),
                "http_statuses": list(local.statuses),
                "elapsed_seconds": round(time.monotonic() - started, 3),
                "interpretation": "Result retrieved"
                if papers
                else "No result; inspect HTTP status, not evidence of a successful retrieval",
            }
        finally:
            close_connection()

    with ThreadPoolExecutor(max_workers=3) as pool:
        observations = list(
            pool.map(
                check,
                [
                    ("arXiv", search_arxiv),
                    ("PubMed", search_pubmed),
                    ("Semantic Scholar", search_semantic_scholar),
                ],
            )
        )
    report = {
        "executed_at_utc": datetime.now(UTC).isoformat(),
        "observations": observations,
        "limit": "One snapshot per source, not a statistical uptime estimate. No live AI evaluation.",
    }
    output = ROOT / "docs" / "test-results"
    output.mkdir(parents=True, exist_ok=True)
    (output / "live-sources.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
