CREATE TABLE IF NOT EXISTS observed_archives (
 id TEXT PRIMARY KEY, owner_id TEXT NOT NULL REFERENCES accounts(id),
 export_sha256 TEXT NOT NULL, manifest BLOB NOT NULL, mode TEXT NOT NULL,
 received_at TEXT NOT NULL, cursor INTEGER NOT NULL, record_count INTEGER NOT NULL,
 receipt TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS observed_archive_entries (
 archive_id TEXT NOT NULL REFERENCES observed_archives(id),
 partition_id TEXT NOT NULL, ordinal INTEGER NOT NULL,
 patient_id TEXT NOT NULL REFERENCES patients(id), record_id TEXT NOT NULL,
 schema_version TEXT NOT NULL, kind TEXT NOT NULL,
 payload BLOB NOT NULL, payload_sha256 TEXT NOT NULL,
 raw_source BLOB NOT NULL, raw_sha256 TEXT NOT NULL,
 PRIMARY KEY(archive_id,partition_id,record_id), UNIQUE(archive_id,ordinal)
);
CREATE TABLE IF NOT EXISTS observed_archive_artifacts (
 archive_id TEXT NOT NULL REFERENCES observed_archives(id), path TEXT NOT NULL,
 payload BLOB NOT NULL, sha256 TEXT NOT NULL, PRIMARY KEY(archive_id,path)
);
INSERT OR IGNORE INTO schema_migrations VALUES(2);
