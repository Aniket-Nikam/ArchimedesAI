CREATE TABLE IF NOT EXISTS work_leases(id TEXT PRIMARY KEY,pool TEXT NOT NULL,expires_at REAL NOT NULL);
CREATE INDEX IF NOT EXISTS idx_work_leases_pool ON work_leases(pool,expires_at);
