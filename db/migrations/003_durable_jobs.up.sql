CREATE TABLE IF NOT EXISTS research_jobs (
 id TEXT PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
 request_json TEXT NOT NULL, status TEXT NOT NULL CHECK(status IN ('queued','running','complete','error','cancelled')),
 generation TEXT, lease_until REAL NOT NULL DEFAULT 0, attempts INTEGER NOT NULL DEFAULT 0,
 deadline REAL NOT NULL, created_at REAL NOT NULL, updated_at REAL NOT NULL,
 session_id INTEGER REFERENCES research_sessions(id) ON DELETE SET NULL, error TEXT
);
CREATE INDEX IF NOT EXISTS idx_jobs_status_lease ON research_jobs(status,lease_until);
CREATE INDEX IF NOT EXISTS idx_jobs_owner ON research_jobs(user_id,created_at DESC);
CREATE TABLE IF NOT EXISTS research_job_events (
 id INTEGER PRIMARY KEY AUTOINCREMENT, job_id TEXT NOT NULL REFERENCES research_jobs(id) ON DELETE CASCADE,
 payload TEXT NOT NULL, created_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_job_events_cursor ON research_job_events(job_id,id);
CREATE TABLE IF NOT EXISTS rate_limit_events (
 bucket TEXT NOT NULL, at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_rate_limit_bucket ON rate_limit_events(bucket,at);
