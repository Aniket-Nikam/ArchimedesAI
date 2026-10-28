"""Read-only collection of evidence from browser-created research sessions."""

import json
import re
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STUDY = ROOT / "docs/user-study"
DATABASE = ROOT / "data/user-study/archimedes.db"


def normalize(text):
    return re.sub(r"\W", "", str(text).casefold())


def collect():
    cases = json.loads((STUDY / "cases.json").read_text(encoding="utf-8"))
    connection = sqlite3.connect(f"{DATABASE.resolve().as_uri()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    output = []
    for case in cases:
        row = connection.execute(
            "SELECT id,report_json,created_at FROM research_sessions WHERE query=? ORDER BY id DESC LIMIT 1",
            (case["query"],),
        ).fetchone()
        if not row:
            output.append({**case, "state": "not_completed"})
            continue
        report = json.loads(row["report_json"])
        papers = (
            report.get("seminal", [])
            + report.get("citations", [])
            + report.get("citations_depth2", [])
        )
        matches = [
            (index, paper)
            for index, paper in enumerate(papers, 1)
            if normalize(paper.get("title")) == normalize(case["expected_title"])
        ]
        synthesis = report.get("ai_synthesis", {})
        output.append(
            {
                **case,
                "state": "complete",
                "session_id": row["id"],
                "created_at": row["created_at"],
                "elapsed_seconds": report.get("elapsed_seconds"),
                "papers": len(papers),
                "expected_paper_found": bool(matches),
                "expected_rank": matches[0][0] if matches else None,
                "source_status": report.get("source_status", []),
                "citation_status": report.get("citation_status"),
                "citation_edges": len(report.get("citations", []))
                + len(report.get("citations_depth2", [])),
                "overview": synthesis.get("overview") if isinstance(synthesis, dict) else synthesis,
                "findings": synthesis.get("key_findings", [])
                if isinstance(synthesis, dict)
                else [],
                "evidence_review": synthesis.get("evidence_review")
                if isinstance(synthesis, dict)
                else None,
                "paper_metadata": [
                    {
                        key: paper.get(key)
                        for key in (
                            "evidence_id",
                            "title",
                            "year",
                            "url",
                            "doi",
                            "source",
                            "retraction_status",
                        )
                    }
                    for paper in papers
                ],
            }
        )
    attempts = [
        dict(row)
        for row in connection.execute(
            "SELECT id,status,attempts,created_at,updated_at,session_id,request_json FROM research_jobs ORDER BY created_at"
        )
    ]
    for attempt in attempts:
        attempt["query"] = json.loads(attempt.pop("request_json"))["query"]
    result = {
        "collected_at_utc": datetime.now(UTC).isoformat(),
        "method": "Research initiated and observed via the normal browser UI; this script only reads the isolated study database.",
        "cases": output,
        "attempts": attempts,
    }
    (STUDY / "results.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            [
                {
                    "id": case["id"],
                    "state": case["state"],
                    "expected_paper_found": case.get("expected_paper_found"),
                    "seconds": case.get("elapsed_seconds"),
                }
                for case in output
            ],
            indent=2,
        )
    )


if __name__ == "__main__":
    collect()
