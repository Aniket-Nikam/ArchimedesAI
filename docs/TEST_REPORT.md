# ArchimedesAI — detailed test and reliability report

Executed: **2026-10-28T06:30:40.221485+00:00** (UTC).

## Verdict

**The tested local application paths passed. Production and scientific reliability are not yet established.**

This run contains **33 distinct backend tests**, repeated three times (**99 passing backend executions**), and **4 distinct frontend stream tests**: **37 distinct automated tests** in total. Repeated executions are not counted as additional distinct tests.

Three live academic-source checks also returned papers in this snapshot. No live Groq synthesis, literature review, manuscript draft or claim-analysis evaluation was performed because this checkout has no configured provider key.

## How the application works

1. Registration/login verifies credentials and establishes an expiring HttpOnly session. The database stores a hash of its secret. The server derives ownership from this session; submitted user IDs do not grant access. Mutations require a CSRF token.
2. Research admission allows at most two jobs globally and one per account in the current backend process. Source requests run through a bounded provider executor.
3. Semantic Scholar, arXiv and PubMed retrieve candidate papers. Title/DOI normalization removes duplicates; available Semantic Scholar links extend the citation graph.
4. Limited DOI metadata checks annotate retractions conservatively. Missing, failed or unperformed checks stay unknown. AI services synthesize the retrieved evidence; invalid synthesis must not be saved as success.
5. Progress and the completed report stream as SSE. The browser buffers complete frames across arbitrary network chunks. Completed reports use real database IDs for history, exports and follow-on tools.
6. Reading-list papers feed manuscript drafting; uploaded PDFs use bounded reads and text extraction before AI-assisted analysis. These AI outputs still require human verification.

## Method and evidence

- Environment: Windows, Python 3.12.14, Node v24.13.0.
- Application base commit: `bc487866bd8ed475ab853baf36af9ffac4a0cdcf`. Any tested working-tree changes after this base are included in the report's Git commit.
- Backend requests exercise the real FastAPI routing, validation, sessions, CSRF and SQLite persistence through TestClient. Each case starts with cleaned isolated test tables, not developer research.
- Provider-facing tests use explicit stubs, synthetic papers and fake keys. Password hashing uses reduced bcrypt rounds in tests, so durations do not predict production login latency.
- The frontend tests run the real stream decoder under Node; they are not React component or full-browser tests.
- XML results, command logs, the JSON summary and live observations are stored in [test-results/](test-results/). Hostnames and user-home paths are removed from the retained evidence.

## Per-test results

Every backend test below passed in all three runs. Durations are first-run test-case timings (including fixture overhead where reported), not service latency benchmarks.

| # | Area / test | What it did and how | Observed result and limit | First-run time |
|---|---|---|---|---|
| 1 | Exports: `test_export_quotes_and_formula_text` | Export a formula-like title and an abstract containing commas, quotes and a newline; parse the generated CSV. | PASS — The CSV retains six columns and the complete abstract; formula text is prefixed to prevent spreadsheet execution. | 0.004s |
| 2 | Exports: `test_bibtex_keys_are_unique_and_ris_fields_cannot_inject_lines` | Export repeated author/year papers containing braces, and a RIS title containing a fake field line. | PASS — BibTeX keys differ, braces are escaped and the RIS title cannot insert a separate field line. External reference managers were not tested. | 0.008s |
| 3 | Exports: `test_all_saved_report_export_formats` | Save a report and request CSV, BibTeX, APA-style text and RIS through the authenticated endpoint. | PASS — All four return 200, attachment headers and the paper title. Bibliographic style compliance is not formally certified. | 0.112s |
| 4 | Security: `test_auth_endpoints_rate_limit` | Send 30 invalid login attempts from one client, then send a 31st. | PASS — The first 30 return 401 and the next returns 429. The guard is process-local; distributed abuse is not tested. | 0.246s |
| 5 | Research: `test_unconfigured_ai_returns_actionable_failure` | Sign in with no AI key configured and request research. | PASS — HTTP 503 is returned with an unavailable message; history remains empty. | 0.066s |
| 6 | Research: `test_research_stream_saves_deduplicated_report_and_real_id` | Stub three sources and synthesis, return overlapping titles, submit a forged user ID, consume SSE and reload the saved ID. | PASS — Two unique papers are saved under the authenticated account; source uncertainty and unknown retraction state survive; the real saved ID reloads. | 0.112s |
| 7 | Research: `test_empty_sources_and_failed_synthesis_never_save_fake_success` | Stub all search sources as empty and consume the research stream. | PASS — An error event is emitted and no report is saved. Despite the legacy test name, this case checks empty retrieval; invalid synthesis has its own test. | 0.097s |
| 8 | Capacity: `test_only_one_research_job_per_account` | Pre-mark the signed-in account as running, then submit another job and clean up the marker. | PASS — A duplicate account job gets 409. Admission logic is checked; this is not simultaneous browser load. | 0.154s |
| 9 | Research: `test_invalid_synthesis_never_becomes_saved_success` | Make synthesis return a failure string instead of the required report object. | PASS — The stream contains an error, contains no completion event and saves nothing. | 0.149s |
| 10 | Capacity: `test_global_research_capacity_returns_retryable_error` | Acquire every research slot, submit a request, and release slots in cleanup. | PASS — Saturated admission returns 429 with Retry-After 10. This does not establish requests-per-second capacity. | 0.114s |
| 11 | Research: `test_timeout_stops_pipeline_before_sources_or_save` | Set a 30 ms deadline and make keyword extraction sleep 100 ms; consume the result and wait for worker cleanup. | PASS — An error is delivered, account admission is released, and no session is saved. Active remote-call cancellation is not measured. | 0.200s |
| 12 | Integrity: `test_retraction_failures_and_unchecked_papers_remain_unknown` | Make DOI lookup unavailable and give two DOI papers a one-lookup budget. | PASS — Both unavailable and unchecked cases remain unknown rather than falsely safe. | 0.042s |
| 13 | Integrity: `test_dedup_normalizes_title_and_doi` | Supply punctuation/case title duplicates and a DOI duplicate with a different title. | PASS — The fixture collapses to two unique papers. This is not a fuzzy bibliographic entity-resolution benchmark. | 0.035s |
| 14 | Resilience: `test_http_retry_after_is_capped_and_no_final_sleep` | Return HTTP 429 with an enormous Retry-After and capture requested sleeps across two attempts. | PASS — Exactly one 5-second sleep is requested; no final redundant sleep occurs. Sleep is stubbed, not actually waited. | 0.039s |
| 15 | Security: `test_protected_routes_require_session` | Send unauthenticated history, research and bookmark requests, including a forged user ID; require HTTP 401. | PASS — Those three entry points reject anonymous callers. This is not an exhaustive penetration test. | 0.083s |
| 16 | Security: `test_csrf_and_logout_revocation` | Register, remove the CSRF header, attempt a bookmark mutation, restore the token and log out, then replay the old session cookie. | PASS — Mutation returns 403 without CSRF; replay returns 401 after logout. | 0.136s |
| 17 | Security: `test_caller_cannot_impersonate_other_user` | Create Alice's research/project, sign in separately as Bob, forge Alice's IDs in history, export, bookmark and project-assignment requests. | PASS — Bob cannot read/export Alice's report or assign his report to her project; forged bookmark ownership is ignored. | 0.244s |
| 18 | Security: `test_session_secret_is_hashed_and_expires` | Compare the browser token with the database value; force database expiry and request the session. | PASS — The stored value differs from the cookie and an expired session returns 401. This does not measure cryptographic resistance. | 0.097s |
| 19 | Security: `test_origin_and_multibyte_password_validation` | Submit registration from an untrusted Origin; separately submit 40 two-byte characters as a password. | PASS — Foreign origin is rejected with 403; the password exceeding bcrypt's 72-byte boundary returns 400. | 0.059s |
| 20 | Data: `test_session_migration_reversible_preserves_users` | Create an account, run session migration 001 down, verify the user remains, then apply its up migration twice. | PASS — Session-table rollback preserves the user and reapplication is idempotent. It does not test migration 002 downgrade or a large historical database. | 0.102s |
| 21 | Tools: `test_bookmark_notes_and_removal_roundtrip` | Save a paper, update notes, read it back, remove it and reread. | PASS — Paper data and notes persist correctly, then the list becomes empty. | 0.151s |
| 22 | Security: `test_health_does_not_expose_provider_secret` | Set a distinctive fake provider secret and fetch public health metadata. | PASS — Health reports configuration presence but never returns the fake secret. | 0.053s |
| 23 | Tools: `test_draft_receives_selected_papers_and_notes` | Stub drafting, submit section/notes/papers and capture the service arguments. | PASS — The route forwards exactly the selected evidence and returns the stubbed draft. Writing quality and citations are not evaluated. | 0.108s |
| 24 | Tools: `test_extraction_returns_provider_rows` | Stub extraction with a known row, submit one paper and compare the response. | PASS — The endpoint preserves the expected extraction response shape. Extraction accuracy is not evaluated. | 0.082s |
| 25 | Tools: `test_literature_review_download_uses_saved_evidence` | Save an owned report, stub review generation, request its ID and capture the evidence/query passed to the service. | PASS — The correct saved paper/query are used and the review is downloadable. Generated scientific content is not evaluated. | 0.085s |
| 26 | Tools: `test_unconfigured_utility_tools_return_503` | Submit valid drafting and extraction inputs without an AI key. | PASS — Both endpoints explicitly return 503 instead of a fake successful output. | 0.087s |
| 27 | Resilience: `test_utility_provider_failure_returns_502_and_recovers` | Make extraction raise a private provider diagnostic three times, then replace it with a successful stub. | PASS — Failures become 502 without exposing the diagnostic, and a later request succeeds, showing slot cleanup. | 0.103s |
| 28 | Capacity: `test_utility_capacity_rejects_then_recovers` | Hold all utility slots, request extraction, release slots, then request it again. | PASS — Saturation returns 429; a later request returns 200. This is a deterministic admission test, not a load benchmark. | 0.102s |
| 29 | PDF: `test_malformed_pdf_rejected` | Upload non-PDF bytes with a .pdf filename. | PASS — The parser failure becomes HTTP 400 rather than a server crash. | 0.112s |
| 30 | PDF: `test_non_pdf_extension_rejected` | Upload a .txt file to the PDF endpoint. | PASS — The unsupported extension is rejected with HTTP 400. | 0.099s |
| 31 | PDF: `test_pdf_page_limit_enforced` | Generate and upload a real 101-page synthetic PDF. | PASS — The endpoint returns 400 and identifies the 100-page maximum. | 0.447s |
| 32 | PDF: `test_pdf_read_limit_enforced` | Temporarily reduce the size threshold to 1,024 bytes and send 1,025 bytes. | PASS — The oversized-read branch rejects the input. This checks the logic without a 20 MB upload; it does not test proxy or multipart-spooling limits. | 0.103s |
| 33 | PDF: `test_pdf_analysis_returns_page_count_and_stubbed_analysis` | Generate a readable one-page PDF, stub metadata/search/claim services, and upload it. | PASS — Real PDF text extraction works, page count is one, extracted text exceeds the minimum and the stubbed analysis is returned. This is not live claim verification. | 0.109s |

### Frontend stream tests

| Test | Procedure | Observed result / meaning |
|---|---|---|
| Unicode and arbitrary chunk boundaries | Split a Unicode JSON event at every possible byte boundary, then feed one byte at a time. | PASS: the original event is reconstructed without losing Unicode or the saved session ID. |
| Multiple frames and SSE formatting | Feed comments, CRLF, multiline data and multiple events together. | PASS: two data events are recognized; comments are ignored. |
| Truncation and malformed JSON | Feed an incomplete event and malformed JSON. | PASS: decoder rejects both instead of claiming completion. |
| Consumer cancellation | Stop consuming after one progress event and observe the stream's cancel callback. | PASS: the reader is cancelled. This does not prove immediate cancellation of a running external HTTP request. |

## Repeatability and build checks

| Check | Exit result | Wall time |
|---|---|---|
| backend-run-1 | PASS | 7.141s |
| backend-run-2 | PASS | 7.031s |
| backend-run-3 | PASS | 7.344s |
| python-lint | PASS | 0.297s |
| python-format | PASS | 0.282s |
| dependencies | PASS | 1.375s |
| frontend-tests | PASS | 1.109s |
| frontend-lint | PASS | 1.031s |
| frontend-build | PASS | 5.031s |

These wall times include process startup/imports. The three backend runs found no observed flakiness in this sample; three runs are far too few to estimate a failure probability. There is no coverage-percentage or throughput claim.

The Starlette test client emitted one HTTPX transport deprecation warning per backend run. Tests passed, but that dependency compatibility should be revisited during upgrades. Frontend lint/build, Python lint/format and pip dependency consistency checks also passed.

## Live source checks

Executed: 2026-10-28T06:18:55.416226+00:00. One fresh, isolated query per source: `retrieval augmented generation`, one paper requested.

| Source | HTTP statuses | Papers returned | Wall time | Interpretation |
|---|---|---|---|---|
| arXiv | 200 | 1 | 0.797s | Result retrieved |
| PubMed | 200, 200 | 1 | 1.078s | Result retrieved |
| Semantic Scholar | 200 | 1 | 1.359s | Result retrieved |

## Hosted GitHub Actions verification

Public workflow state captured at 2026-10-28T06:32:32.673220+00:00. These are separate Linux runner checks, not the local Windows runs above.

| Commit | Workflow | Backend / frontend jobs |
|---|---|---|
| `b8691b3` | [success](https://github.com/Aniket-Nikam/ArchimedesAI/actions/runs/40644354479) | frontend (24.13.0): success; frontend (24): success; backend: success |
| `bc48786` | [success](https://github.com/Aniket-Nikam/ArchimedesAI/actions/runs/40643979656) | frontend: success; backend: success |
| `f548257` | [failure](https://github.com/Aniket-Nikam/ArchimedesAI/actions/runs/40643473159) | frontend: failure; backend: success |

The first hosted run passed the backend but failed frontend clean installation. The known Node 24.13.0 toolchain then passed both jobs. Investigation also found missing optional WASM peer entries under newer npm validation; the lockfile was completed and frontend CI expanded to the known version plus the latest Node 24 release. No direct application dependency versions were changed by this repair.

CI passing supports clean installation, tests, lint and build on the listed runner/toolchains. It does not establish deployed uptime or live AI output quality.

All three sources returned a titled paper in this run. An earlier smoke run returned no Semantic Scholar data, so availability clearly can vary. These observations do not establish uptime, relevance, bibliographic accuracy, citation coverage or reproducible search ranking.

## How reliable is it?

| Area | Evidence-supported assessment | What remains uncertain |
|---|---|---|
| Account boundaries | Stronger local confidence: forged-ID, expiry, CSRF, logout and ownership cases passed. | No independent security audit; no broad attack/fuzz testing; rate limits are process-local. |
| Saved-data workflow | Good local confidence for the tested history, bookmark, notes and export paths. | Large databases, backup restoration, disk exhaustion and concurrent write stress were not tested. |
| Stream transport | Good confidence in the tested decoder edge cases and server completion/error contracts. | Real slow networks, reverse-proxy buffering and React/browser lifecycle races need broader end-to-end coverage. |
| Failure handling | Tested errors remain errors; slots recover after provider failures; invalid synthesis is not saved. | Cancellation is cooperative; in-flight HTTP requests are not forcibly killed; jobs do not survive restarts. |
| Academic retrieval | All default providers responded in one current snapshot. | Rate limits/outages and search quality can vary; no uptime or relevance benchmark. |
| AI research quality | Unverified with live models. Stubbed tests prove data handoff and error behavior only. | Hallucinations, unsupported conclusions, citation correctness, extraction accuracy and draft quality require a labelled evaluation set and human review. |
| Retraction integrity | Unknown states are preserved in the tested failure/budget cases. | Crossref is incomplete; no notice is not proof of safety. |
| Deployment readiness | The local production build and captured Linux CI backend/frontend jobs pass. | Deployment, HTTPS/cookies, persistent storage and load remain unverified. |

**I would trust this revision for further development and a controlled local demonstration. I would not yet describe it as a scientifically validated or production-proven autonomous research product.** The automated pass rate is 100% for these cases; that is not an overall reliability percentage.

## Before marking the project completed on Handshake

1. Configure Groq locally or on the intended host, without committing credentials.
2. Run genuine research, follow-up, literature-review, extraction, PDF-analysis and manuscript workflows; retain the retrieved evidence and inspect outputs.
3. Evaluate several representative questions against known papers. Record unsupported claims, incorrect citations, omissions, response times and API failures.
4. Verify the deployed URL, account isolation, HTTPS secure cookies and persistent history across a restart; test representative concurrent users before making capacity claims.

## Reproduce

```powershell
.venv\Scripts\python.exe scripts/verify_release.py
.venv\Scripts\python.exe scripts/live_source_smoke.py
.venv\Scripts\python.exe scripts/build_test_report.py
```

Run the live script only when network access is intended. It uses a public query, isolated database and no AI calls. A failed or changed rerun should replace the current evidence rather than be hidden.
