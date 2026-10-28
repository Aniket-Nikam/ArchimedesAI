# Reply formatting follow-up

The walkthrough PDF records the older reply presentation. A follow-up fix addresses the raw Markdown table separators and narrow PDF output visible in that report.

- A shared safe GFM renderer now handles research responses, PDF analysis and manuscript drafts. Tables render as semantic rows/columns; raw generated HTML is omitted and unsafe URL schemes remain blocked.
- Completed PDF analysis expands from the 520px upload box to the research workspace width. The introductory empty-state content is hidden while results are present, and long results scroll from their beginning rather than remaining vertically centered.
- Headings, paragraphs, lists and table rows have consistent spacing. Cells have a minimum readable width; small screens scroll the table horizontally without overflowing the page.
- A fresh upload of the original Transformer PDF rendered three real comparison tables. Desktop and mobile screenshots are saved alongside the other study evidence.
- At a 390px viewport, document width remained 390px, while each table exposed 620px of content inside a 305px scrolling region. The mobile sidebar was closed through its normal control; the viewport override was reset afterward.
- All 9 frontend tests, lint and TypeScript/production build passed. Two new regressions cover semantic table/section rendering and unsafe generated HTML/links. Compatible dependency patches resolved the audit findings observed during installation; the resulting npm audit reported zero vulnerabilities.

This changes presentation, not the scientific correctness of generated content. The earlier limitations in CLAIM_REVIEW.md still apply.
