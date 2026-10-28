# Operations and verification review

Reviewed on 28 October 2026. Deployment is excluded from this task.

## Implemented controls

- SQLite transactions coordinate account/global research admission and authentication windows across local processes. Utility jobs use expiring shared leases. This does not make SQLite a distributed queue.
- Each research job has a persisted request, event log, generation, deadline and worker lease. Expired workers can be reclaimed at most three times. Completion and report insertion share a transaction; stale generations cannot save a second result.
- Cancellation terminates a process handle created by this application. Worker monitoring also observes cancellation/deadline changes. A remote provider may already have received a request; killing the client cannot retract that request or guarantee billing cancellation.
- Request bodies are bounded before parsing, including chunked bodies. Memory spools to temporary storage after 1 MB. PDF extraction remains bounded and is not OCR.
- DOI notices are checked against Crossref and OpenAlex where available. Unknown and unperformed checks remain unknown. These are metadata services, not independent guarantees of paper integrity.
- Source identifiers in findings are checked against retrieved papers. A membership match proves only that a cited paper was retrieved, not that it supports the generated statement.
- Windows DPAPI protects the local key at rest for the current OS user. It does not protect against malicious software running as that user. Data/secrets and environment files remain ignored by Git.

## Evidence and limits

The automated suite includes 25,000-record backup/restore, 400 concurrent bookmark writes, virtual SQLITE_FULL rollback, storage-error sanitization, migration upgrade/downgrade, cross-process authentication limits, stale worker recovery, cancellation of an owned subprocess and a deterministic 200-input malformed JSON/PDF corpus. This is bounded engineering verification, not an independent penetration test or exhaustive fuzz campaign. A virtual database quota does not reproduce physical disk exhaustion, filesystem corruption or a full temporary volume.

The live study initiates research through the normal browser. Provider observations and saved outputs are read afterward from an isolated study database. Expected titles are labelled before evaluation. Repeated runs and fixes are disclosed; final-run retrieval rates must not be represented as first-attempt success or general relevance/uptime estimates.

Scientific claim review is a limited agent-assisted comparison with linked paper descriptions. Independent domain-expert review, a larger labelled claim/extraction/draft evaluation corpus, and publication-level citation verification remain necessary. No confidence badge substitutes for reading the original.

## Operating boundaries

Keep all processes on one host with one SQLite data directory. Monitor database size, job/event growth and free space. There is currently no automatic retention policy for saved jobs/events. Set a retention policy before unattended production use. Backups contain research and account data; restrict access and retain checksum sidecars. Checksums detect changes only relative to a trusted sidecar; they are not authenticated signatures or encrypted backups.

HTTPS, secure cookies behind the actual proxy, persistent hosting storage, production load, multi-host operation and deployment recovery have not been certified here. Local proxy simulation is a distinct test, not a production deployment test.
