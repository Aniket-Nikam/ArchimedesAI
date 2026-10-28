# Verification — 28 October 2026

## Observed checks

| Check | Result |
| --- | --- |
| Backend integration/regression suite | 20 passed |
| Frontend SSE tests | 4 passed |
| Python Ruff lint and formatting | Passed |
| Frontend Oxlint | Passed, no warnings |
| TypeScript and Vite production build | Passed |
| Installed dependency consistency (`pip check`) | Passed |
| Git whitespace/error check | Passed |
| Fresh frontend installation from repaired lockfile | `npm ci` passed |

Backend coverage includes account isolation, forged user IDs, CSRF rejection, session expiry/logout revocation, session-secret hashing, origin checks, migration rollback, project ownership, research admission/deadline handling, deduplication, missing/invalid synthesis, unknown retraction status, capped HTTP retries and authenticated citation exports.

The stream suite tests every split point in a Unicode JSON event, one-byte chunks, multiple frames, comments, CRLF, multiline data, malformed/truncated events and consumer cancellation.

## Browser evidence

Tested the built frontend served by FastAPI at `127.0.0.1:8000`:

- Test-account registration and cookie-based session restoration after reload.
- Desktop workspace and 390 × 844 mobile layout; sidebar open/close.
- Honest unavailable-AI feedback when no provider key is configured.
- A clearly labelled synthetic report loaded from history, graph rendered, paper bookmarked, and the paper title appeared in Manuscript Studio.
- CSV downloaded through the authenticated export endpoint and contained the selected report's papers.

Synthetic UI fixtures are not evidence of a live AI research result. Browser test data is local and ignored by Git.

## Performance and dependency changes

The original production entry bundle was 552.39 KB (171.92 KB gzip). The final entry is 354.57 KB (109.53 KB gzip): about **36% less JavaScript initially downloaded**. The 194.20 KB citation graph is loaded separately when a report is shown; total code has not disappeared.

Project session counts use one aggregate query. Cache keys distinguish result limits and cache storage is capped at 2,000 entries. Research and provider concurrency, streamed event queues, input sizes, network retry delays and PDF reads are bounded.

The original broad environment freeze was replaced with direct runtime requirements plus a 35-package runtime/test version constraint snapshot. Optional Google Scholar scraping dependencies are separate.

## Live dependencies and limitations

- Public-API smoke query: `graph neural networks`, one result requested.
- arXiv: returned a paper with a title.
- PubMed: returned a paper with a title.
- Semantic Scholar: returned no data during this run. The client cannot distinguish every empty response from provider refusal; UI coverage says `empty or unavailable`.
- No Groq key was configured in this checkout. A full real-provider search → synthesis → save → literature-review/draft run remains **unverified**.
- CI configuration was added, but hosted GitHub Actions has not run from this local branch.
- The installed Starlette test client emitted a deprecation warning about its HTTPX transport; all integration tests passed.
- Google Scholar scraping, production hosting, load testing and multi-process operation were not verified.

## Listing decision

The implementation is substantially improved and locally verified. Do not describe this revision as a finished deployed product yet. Configure the provider, complete a live research/AI-tools smoke run, and verify the deployed URL before listing it as completed on Handshake.
