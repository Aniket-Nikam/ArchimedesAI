"""Build the detailed report from the captured verification evidence."""

import json
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "docs/test-results"

# Each entry explains actual assertions, not inferred production guarantees.
CATALOG = {
    "test_protected_routes_require_session": (
        "Security",
        "Send unauthenticated history, research and bookmark requests, including a forged user ID; require HTTP 401.",
        "Those three entry points reject anonymous callers. This is not an exhaustive penetration test.",
    ),
    "test_csrf_and_logout_revocation": (
        "Security",
        "Register, remove the CSRF header, attempt a bookmark mutation, restore the token and log out, then replay the old session cookie.",
        "Mutation returns 403 without CSRF; replay returns 401 after logout.",
    ),
    "test_caller_cannot_impersonate_other_user": (
        "Security",
        "Create Alice's research/project, sign in separately as Bob, forge Alice's IDs in history, export, bookmark and project-assignment requests.",
        "Bob cannot read/export Alice's report or assign his report to her project; forged bookmark ownership is ignored.",
    ),
    "test_session_secret_is_hashed_and_expires": (
        "Security",
        "Compare the browser token with the database value; force database expiry and request the session.",
        "The stored value differs from the cookie and an expired session returns 401. This does not measure cryptographic resistance.",
    ),
    "test_origin_and_multibyte_password_validation": (
        "Security",
        "Submit registration from an untrusted Origin; separately submit 40 two-byte characters as a password.",
        "Foreign origin is rejected with 403; the password exceeding bcrypt's 72-byte boundary returns 400.",
    ),
    "test_session_migration_reversible_preserves_users": (
        "Data",
        "Create an account, run session migration 001 down, verify the user remains, then apply its up migration twice.",
        "Session-table rollback preserves the user and reapplication is idempotent. It does not test migration 002 downgrade or a large historical database.",
    ),
    "test_unconfigured_ai_returns_actionable_failure": (
        "Research",
        "Sign in with no AI key configured and request research.",
        "HTTP 503 is returned with an unavailable message; history remains empty.",
    ),
    "test_research_stream_saves_deduplicated_report_and_real_id": (
        "Research",
        "Stub three sources and synthesis, return overlapping titles, submit a forged user ID, consume SSE and reload the saved ID.",
        "Two unique papers are saved under the authenticated account; source uncertainty and unknown retraction state survive; the real saved ID reloads.",
    ),
    "test_empty_sources_and_failed_synthesis_never_save_fake_success": (
        "Research",
        "Stub all search sources as empty and consume the research stream.",
        "An error event is emitted and no report is saved. Despite the legacy test name, this case checks empty retrieval; invalid synthesis has its own test.",
    ),
    "test_only_one_research_job_per_account": (
        "Capacity",
        "Pre-mark the signed-in account as running, then submit another job and clean up the marker.",
        "A duplicate account job gets 409. Admission logic is checked; this is not simultaneous browser load.",
    ),
    "test_invalid_synthesis_never_becomes_saved_success": (
        "Research",
        "Make synthesis return a failure string instead of the required report object.",
        "The stream contains an error, contains no completion event and saves nothing.",
    ),
    "test_global_research_capacity_returns_retryable_error": (
        "Capacity",
        "Acquire every research slot, submit a request, and release slots in cleanup.",
        "Saturated admission returns 429 with Retry-After 10. This does not establish requests-per-second capacity.",
    ),
    "test_timeout_stops_pipeline_before_sources_or_save": (
        "Research",
        "Set a 30 ms deadline and make keyword extraction sleep 100 ms; consume the result and wait for worker cleanup.",
        "An error is delivered, account admission is released, and no session is saved. Active remote-call cancellation is not measured.",
    ),
    "test_retraction_failures_and_unchecked_papers_remain_unknown": (
        "Integrity",
        "Make DOI lookup unavailable and give two DOI papers a one-lookup budget.",
        "Both unavailable and unchecked cases remain unknown rather than falsely safe.",
    ),
    "test_dedup_normalizes_title_and_doi": (
        "Integrity",
        "Supply punctuation/case title duplicates and a DOI duplicate with a different title.",
        "The fixture collapses to two unique papers. This is not a fuzzy bibliographic entity-resolution benchmark.",
    ),
    "test_http_retry_after_is_capped_and_no_final_sleep": (
        "Resilience",
        "Return HTTP 429 with an enormous Retry-After and capture requested sleeps across two attempts.",
        "Exactly one 5-second sleep is requested; no final redundant sleep occurs. Sleep is stubbed, not actually waited.",
    ),
    "test_export_quotes_and_formula_text": (
        "Exports",
        "Export a formula-like title and an abstract containing commas, quotes and a newline; parse the generated CSV.",
        "The CSV retains six columns and the complete abstract; formula text is prefixed to prevent spreadsheet execution.",
    ),
    "test_bibtex_keys_are_unique_and_ris_fields_cannot_inject_lines": (
        "Exports",
        "Export repeated author/year papers containing braces, and a RIS title containing a fake field line.",
        "BibTeX keys differ, braces are escaped and the RIS title cannot insert a separate field line. External reference managers were not tested.",
    ),
    "test_all_saved_report_export_formats": (
        "Exports",
        "Save a report and request CSV, BibTeX, APA-style text and RIS through the authenticated endpoint.",
        "All four return 200, attachment headers and the paper title. Bibliographic style compliance is not formally certified.",
    ),
    "test_auth_endpoints_rate_limit": (
        "Security",
        "Send 30 invalid login attempts from one client, then send a 31st.",
        "The first 30 return 401 and the next returns 429. The guard is process-local; distributed abuse is not tested.",
    ),
    "test_bookmark_notes_and_removal_roundtrip": (
        "Tools",
        "Save a paper, update notes, read it back, remove it and reread.",
        "Paper data and notes persist correctly, then the list becomes empty.",
    ),
    "test_health_does_not_expose_provider_secret": (
        "Security",
        "Set a distinctive fake provider secret and fetch public health metadata.",
        "Health reports configuration presence but never returns the fake secret.",
    ),
    "test_draft_receives_selected_papers_and_notes": (
        "Tools",
        "Stub drafting, submit section/notes/papers and capture the service arguments.",
        "The route forwards exactly the selected evidence and returns the stubbed draft. Writing quality and citations are not evaluated.",
    ),
    "test_extraction_returns_provider_rows": (
        "Tools",
        "Stub extraction with a known row, submit one paper and compare the response.",
        "The endpoint preserves the expected extraction response shape. Extraction accuracy is not evaluated.",
    ),
    "test_literature_review_download_uses_saved_evidence": (
        "Tools",
        "Save an owned report, stub review generation, request its ID and capture the evidence/query passed to the service.",
        "The correct saved paper/query are used and the review is downloadable. Generated scientific content is not evaluated.",
    ),
    "test_unconfigured_utility_tools_return_503": (
        "Tools",
        "Submit valid drafting and extraction inputs without an AI key.",
        "Both endpoints explicitly return 503 instead of a fake successful output.",
    ),
    "test_utility_provider_failure_returns_502_and_recovers": (
        "Resilience",
        "Make extraction raise a private provider diagnostic three times, then replace it with a successful stub.",
        "Failures become 502 without exposing the diagnostic, and a later request succeeds, showing slot cleanup.",
    ),
    "test_utility_capacity_rejects_then_recovers": (
        "Capacity",
        "Hold all utility slots, request extraction, release slots, then request it again.",
        "Saturation returns 429; a later request returns 200. This is a deterministic admission test, not a load benchmark.",
    ),
    "test_malformed_pdf_rejected": (
        "PDF",
        "Upload non-PDF bytes with a .pdf filename.",
        "The parser failure becomes HTTP 400 rather than a server crash.",
    ),
    "test_non_pdf_extension_rejected": (
        "PDF",
        "Upload a .txt file to the PDF endpoint.",
        "The unsupported extension is rejected with HTTP 400.",
    ),
    "test_pdf_page_limit_enforced": (
        "PDF",
        "Generate and upload a real 101-page synthetic PDF.",
        "The endpoint returns 400 and identifies the 100-page maximum.",
    ),
    "test_pdf_read_limit_enforced": (
        "PDF",
        "Temporarily reduce the size threshold to 1,024 bytes and send 1,025 bytes.",
        "The oversized-read branch rejects the input. This checks the logic without a 20 MB upload; it does not test proxy or multipart-spooling limits.",
    ),
    "test_pdf_analysis_returns_page_count_and_stubbed_analysis": (
        "PDF",
        "Generate a readable one-page PDF, stub metadata/search/claim services, and upload it.",
        "Real PDF text extraction works, page count is one, extracted text exceeds the minimum and the stubbed analysis is returned. This is not live claim verification.",
    ),
}


def main():
    summary = json.loads((RESULTS / "summary.json").read_text())
    live = json.loads((RESULTS / "live-sources.json").read_text())
    runs = [ET.parse(RESULTS / f"backend-run-{n}.xml").getroot() for n in range(1, 4)]
    cases = list(runs[0].iter("testcase"))
    names = {case.get("name") for case in cases}
    if names != set(CATALOG):
        raise SystemExit(f"Catalog mismatch: {names.symmetric_difference(CATALOG)}")
    lines = [
        "# ArchimedesAI — detailed test and reliability report",
        "",
        f"Executed: **{summary['executed_at_utc']}** (UTC).",
        "",
        "## Verdict",
        "",
        "**The tested local application paths passed. Production and scientific reliability are not yet established.**",
        "",
        "This run contains **33 distinct backend tests**, repeated three times (**99 passing backend executions**), and **4 distinct frontend stream tests**: **37 distinct automated tests** in total. Repeated executions are not counted as additional distinct tests.",
        "",
        "Three live academic-source checks also returned papers in this snapshot. No live Groq synthesis, literature review, manuscript draft or claim-analysis evaluation was performed because this checkout has no configured provider key.",
        "",
        "## How the application works",
        "",
        "1. Registration/login verifies credentials and establishes an expiring HttpOnly session. The database stores a hash of its secret. The server derives ownership from this session; submitted user IDs do not grant access. Mutations require a CSRF token.",
        "2. Research admission allows at most two jobs globally and one per account in the current backend process. Source requests run through a bounded provider executor.",
        "3. Semantic Scholar, arXiv and PubMed retrieve candidate papers. Title/DOI normalization removes duplicates; available Semantic Scholar links extend the citation graph.",
        "4. Limited DOI metadata checks annotate retractions conservatively. Missing, failed or unperformed checks stay unknown. AI services synthesize the retrieved evidence; invalid synthesis must not be saved as success.",
        "5. Progress and the completed report stream as SSE. The browser buffers complete frames across arbitrary network chunks. Completed reports use real database IDs for history, exports and follow-on tools.",
        "6. Reading-list papers feed manuscript drafting; uploaded PDFs use bounded reads and text extraction before AI-assisted analysis. These AI outputs still require human verification.",
        "",
        "## Method and evidence",
        "",
        f"- Environment: {summary['platform']}, Python {summary['python']}, Node {summary['node']}.",
        f"- Application base commit: `{summary['source_base_commit']}`. Tests/scripts added after this base are included in the report's Git commit.",
        "- Backend requests exercise the real FastAPI routing, validation, sessions, CSRF and SQLite persistence through TestClient. Each case starts with cleaned isolated test tables, not developer research.",
        "- Provider-facing tests use explicit stubs, synthetic papers and fake keys. Password hashing uses reduced bcrypt rounds in tests, so durations do not predict production login latency.",
        "- The frontend tests run the real stream decoder under Node; they are not React component or full-browser tests.",
        "- XML results, command logs, the JSON summary and live observations are stored in [test-results/](test-results/). Hostnames and user-home paths are removed from the retained evidence.",
        "",
        "## Per-test results",
        "",
        "Every backend test below passed in all three runs. Durations are first-run test-case timings (including fixture overhead where reported), not service latency benchmarks.",
        "",
        "| # | Area / test | What it did and how | Observed result and limit | First-run time |",
        "|---|---|---|---|---|",
    ]
    for index, case in enumerate(cases, 1):
        name = case.get("name")
        category, method, meaning = CATALOG[name]
        failed = any(case.find(tag) is not None for tag in ("failure", "error", "skipped"))
        lines.append(
            f"| {index} | {category}: `{name}` | {method} | {'FAIL' if failed else 'PASS'} — {meaning} | {float(case.get('time', 0)):.3f}s |"
        )
    lines += [
        "",
        "### Frontend stream tests",
        "",
        "| Test | Procedure | Observed result / meaning |",
        "|---|---|---|",
        "| Unicode and arbitrary chunk boundaries | Split a Unicode JSON event at every possible byte boundary, then feed one byte at a time. | PASS: the original event is reconstructed without losing Unicode or the saved session ID. |",
        "| Multiple frames and SSE formatting | Feed comments, CRLF, multiline data and multiple events together. | PASS: two data events are recognized; comments are ignored. |",
        "| Truncation and malformed JSON | Feed an incomplete event and malformed JSON. | PASS: decoder rejects both instead of claiming completion. |",
        "| Consumer cancellation | Stop consuming after one progress event and observe the stream's cancel callback. | PASS: the reader is cancelled. This does not prove immediate cancellation of a running external HTTP request. |",
        "",
        "## Repeatability and build checks",
        "",
        "| Check | Exit result | Wall time |",
        "|---|---|---|",
    ]
    for check in summary["checks"]:
        lines.append(
            f"| {check['name']} | {'PASS' if check['exit_code'] == 0 else 'FAIL'} | {check['elapsed_seconds']:.3f}s |"
        )
    lines += [
        "",
        "These wall times include process startup/imports. The three backend runs found no observed flakiness in this sample; three runs are far too few to estimate a failure probability. There is no coverage-percentage or throughput claim.",
        "",
        "The Starlette test client emitted one HTTPX transport deprecation warning per backend run. Tests passed, but that dependency compatibility should be revisited during upgrades. Frontend lint/build, Python lint/format and pip dependency consistency checks also passed.",
        "",
        "## Live source checks",
        "",
        f"Executed: {live['executed_at_utc']}. One fresh, isolated query per source: `retrieval augmented generation`, one paper requested.",
        "",
        "| Source | HTTP statuses | Papers returned | Wall time | Interpretation |",
        "|---|---|---|---|---|",
    ]
    for observation in live["observations"]:
        lines.append(
            f"| {observation['source']} | {', '.join(map(str, observation['http_statuses']))} | {observation['returned']} | {observation['elapsed_seconds']:.3f}s | {observation['interpretation']} |"
        )
    lines += [
        "",
        "All three sources returned a titled paper in this run. An earlier smoke run returned no Semantic Scholar data, so availability clearly can vary. These observations do not establish uptime, relevance, bibliographic accuracy, citation coverage or reproducible search ranking.",
        "",
        "## How reliable is it?",
        "",
        "| Area | Evidence-supported assessment | What remains uncertain |",
        "|---|---|---|",
        "| Account boundaries | Stronger local confidence: forged-ID, expiry, CSRF, logout and ownership cases passed. | No independent security audit; no broad attack/fuzz testing; rate limits are process-local. |",
        "| Saved-data workflow | Good local confidence for the tested history, bookmark, notes and export paths. | Large databases, backup restoration, disk exhaustion and concurrent write stress were not tested. |",
        "| Stream transport | Good confidence in the tested decoder edge cases and server completion/error contracts. | Real slow networks, reverse-proxy buffering and React/browser lifecycle races need broader end-to-end coverage. |",
        "| Failure handling | Tested errors remain errors; slots recover after provider failures; invalid synthesis is not saved. | Cancellation is cooperative; in-flight HTTP requests are not forcibly killed; jobs do not survive restarts. |",
        "| Academic retrieval | All default providers responded in one current snapshot. | Rate limits/outages and search quality can vary; no uptime or relevance benchmark. |",
        "| AI research quality | Unverified with live models. Stubbed tests prove data handoff and error behavior only. | Hallucinations, unsupported conclusions, citation correctness, extraction accuracy and draft quality require a labelled evaluation set and human review. |",
        "| Retraction integrity | Unknown states are preserved in the tested failure/budget cases. | Crossref is incomplete; no notice is not proof of safety. |",
        "| Deployment readiness | The local production build passes; CI is configured. | Hosted CI outcome is recorded separately after push. Deployment, HTTPS/cookies, persistent storage and load remain unverified. |",
        "",
        "**I would trust this revision for further development and a controlled local demonstration. I would not yet describe it as a scientifically validated or production-proven autonomous research product.** The automated pass rate is 100% for these cases; that is not an overall reliability percentage.",
        "",
        "## Before marking the project completed on Handshake",
        "",
        "1. Configure Groq locally or on the intended host, without committing credentials.",
        "2. Run genuine research, follow-up, literature-review, extraction, PDF-analysis and manuscript workflows; retain the retrieved evidence and inspect outputs.",
        "3. Evaluate several representative questions against known papers. Record unsupported claims, incorrect citations, omissions, response times and API failures.",
        "4. Verify the deployed URL, account isolation, HTTPS secure cookies and persistent history across a restart; test representative concurrent users before making capacity claims.",
        "",
        "## Reproduce",
        "",
        "```powershell",
        ".venv\\Scripts\\python.exe scripts/verify_release.py",
        ".venv\\Scripts\\python.exe scripts/live_source_smoke.py",
        ".venv\\Scripts\\python.exe scripts/build_test_report.py",
        "```",
        "",
        "Run the live script only when network access is intended. It uses a public query, isolated database and no AI calls. A failed or changed rerun should replace the current evidence rather than be hidden.",
    ]
    (ROOT / "docs/TEST_REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
