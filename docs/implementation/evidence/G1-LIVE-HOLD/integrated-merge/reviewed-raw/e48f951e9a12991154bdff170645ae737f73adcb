CREATE TABLE IF NOT EXISTS schema_migrations (version INTEGER PRIMARY KEY);
CREATE TABLE IF NOT EXISTS accounts (
 id TEXT PRIMARY KEY, username TEXT UNIQUE NOT NULL, display_name TEXT NOT NULL,
 password_hash TEXT NOT NULL, auth_version INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS sessions (
 token_hash TEXT PRIMARY KEY, csrf TEXT NOT NULL, account_id TEXT REFERENCES accounts(id),
 auth_version INTEGER, expires_at REAL NOT NULL, revoked INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS login_attempts (
 id INTEGER PRIMARY KEY, account_key TEXT NOT NULL, source_key TEXT NOT NULL,
 attempted_at REAL NOT NULL, success INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS patients (
 id TEXT PRIMARY KEY, owner_id TEXT NOT NULL REFERENCES accounts(id), name TEXT NOT NULL,
 version INTEGER NOT NULL, state_version INTEGER NOT NULL, consent_version INTEGER NOT NULL,
 eligibility_version INTEGER NOT NULL, state_json TEXT NOT NULL, current_decision TEXT,
 cutoff TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS events (
 id TEXT PRIMARY KEY, patient_id TEXT NOT NULL REFERENCES patients(id), kind TEXT NOT NULL,
 lineage_id TEXT NOT NULL, revision INTEGER NOT NULL, duplicate_of TEXT,
 payload TEXT NOT NULL, payload_sha256 TEXT NOT NULL,
 raw_source BLOB NOT NULL, raw_sha256 TEXT NOT NULL,
 event_at TEXT NOT NULL, recorded_at TEXT NOT NULL, available_at TEXT NOT NULL,
 phase INTEGER NOT NULL, live_received_at TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS unique_lineage_revision
 ON events(patient_id,lineage_id,revision) WHERE duplicate_of IS NULL;
CREATE TABLE IF NOT EXISTS decisions (
 id TEXT PRIMARY KEY, patient_id TEXT NOT NULL REFERENCES patients(id),
 snapshot TEXT NOT NULL, display TEXT NOT NULL, display_sha256 TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS bundles (
 id TEXT PRIMARY KEY, patient_id TEXT NOT NULL REFERENCES patients(id),
 decision_id TEXT NOT NULL REFERENCES decisions(id), display TEXT NOT NULL,
 display_sha256 TEXT NOT NULL, approved_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS tasks (
 id TEXT PRIMARY KEY, patient_id TEXT NOT NULL REFERENCES patients(id), bundle_id TEXT NOT NULL,
 owner_id TEXT NOT NULL, due_at TEXT NOT NULL, payload TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS receipts (
 owner_id TEXT NOT NULL, session_id TEXT NOT NULL, key TEXT NOT NULL,
 scope TEXT NOT NULL, payload_sha256 TEXT NOT NULL, response TEXT NOT NULL,
 PRIMARY KEY(owner_id,session_id,key)
);
CREATE TABLE IF NOT EXISTS ingestion_receipts (
 run_id TEXT NOT NULL, transport_key TEXT NOT NULL, payload_sha256 TEXT NOT NULL,
 status TEXT NOT NULL, detail TEXT NOT NULL, PRIMARY KEY(run_id,transport_key)
);
CREATE TABLE IF NOT EXISTS replay_runs (
 id TEXT PRIMARY KEY, source_sha256 TEXT NOT NULL, cursor INTEGER NOT NULL,
 record_count INTEGER NOT NULL, cutoff TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS pending_work (
 id TEXT PRIMARY KEY, patient_id TEXT NOT NULL REFERENCES patients(id),
 status TEXT NOT NULL, reason TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS drafts (
 owner_id TEXT NOT NULL, patient_id TEXT NOT NULL REFERENCES patients(id),
 decision_id TEXT NOT NULL, auth_generation TEXT NOT NULL, base_version INTEGER NOT NULL,
 payload TEXT NOT NULL, PRIMARY KEY(owner_id,patient_id,decision_id)
);
CREATE TABLE IF NOT EXISTS state_changes (
 id TEXT PRIMARY KEY, patient_id TEXT NOT NULL REFERENCES patients(id),
 actor_id TEXT NOT NULL, created_at TEXT NOT NULL, payload TEXT NOT NULL
);
INSERT OR IGNORE INTO schema_migrations VALUES(1);
