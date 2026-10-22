CREATE TABLE service_control (
 singleton INTEGER PRIMARY KEY CHECK(singleton=1), database_instance_id TEXT UNIQUE NOT NULL,
 capability TEXT NOT NULL, minimum_reader_writer_capability TEXT NOT NULL,
 authority_generation INTEGER NOT NULL CHECK(authority_generation>0), authority_sha256 TEXT NOT NULL,
 review_rules_sha256 TEXT NOT NULL, enabled INTEGER NOT NULL, activation_id TEXT NOT NULL,
 activated_at TEXT NOT NULL, last_receipt_at TEXT NOT NULL
);
CREATE TABLE live_authority_history (
 generation INTEGER PRIMARY KEY, authority_sha256 TEXT NOT NULL, review_rules_sha256 TEXT NOT NULL,
 authority TEXT NOT NULL, review_rules TEXT NOT NULL, activation_id TEXT NOT NULL, activated_at TEXT NOT NULL
);
CREATE TABLE live_hold_operations (
 sequence INTEGER PRIMARY KEY AUTOINCREMENT, id TEXT UNIQUE NOT NULL,
 patient_id TEXT NOT NULL REFERENCES patients(id), family TEXT NOT NULL,
 semantic_sha256 TEXT NOT NULL UNIQUE, received_at TEXT NOT NULL,
 payload TEXT NOT NULL, response TEXT NOT NULL
);
CREATE TABLE live_hold_episodes (
 id TEXT NOT NULL, generation INTEGER NOT NULL, patient_id TEXT NOT NULL REFERENCES patients(id),
 source_key TEXT NOT NULL, status TEXT NOT NULL CHECK(status IN ('active','closed')),
 opened_at TEXT NOT NULL, last_operation TEXT NOT NULL, payload TEXT NOT NULL,
 PRIMARY KEY(id,generation)
);
CREATE UNIQUE INDEX active_episode ON live_hold_episodes(id) WHERE status='active';
CREATE TABLE live_hold_reviews (
 id TEXT PRIMARY KEY, patient_id TEXT NOT NULL REFERENCES patients(id), episode_id TEXT NOT NULL,
 generation INTEGER NOT NULL, operation_id TEXT NOT NULL UNIQUE,
 payload TEXT NOT NULL, payload_sha256 TEXT NOT NULL
);
CREATE TABLE live_hold_tasks (
 id TEXT PRIMARY KEY, patient_id TEXT NOT NULL REFERENCES patients(id), episode_id TEXT NOT NULL,
 generation INTEGER NOT NULL, owner_id TEXT NOT NULL REFERENCES accounts(id),
 due_at TEXT NOT NULL, payload TEXT NOT NULL, UNIQUE(episode_id,generation)
);
CREATE TABLE live_hold_task_events (
 id TEXT PRIMARY KEY, task_id TEXT NOT NULL REFERENCES live_hold_tasks(id),
 operation_id TEXT NOT NULL, payload TEXT NOT NULL
);
CREATE TABLE live_hold_keys (
 owner_id TEXT NOT NULL REFERENCES accounts(id), patient_id TEXT NOT NULL REFERENCES patients(id),
 family TEXT NOT NULL, key TEXT NOT NULL, request_sha256 TEXT NOT NULL,
 operation_id TEXT NOT NULL REFERENCES live_hold_operations(id), PRIMARY KEY(owner_id,patient_id,family,key)
);
CREATE TABLE live_patient_journals (
 patient_id TEXT PRIMARY KEY REFERENCES patients(id), journal_id TEXT UNIQUE NOT NULL
);
CREATE TABLE live_safety_facts (
 patient_id TEXT NOT NULL REFERENCES patients(id), patient_sequence INTEGER NOT NULL,
 operation_id TEXT NOT NULL, received_at TEXT NOT NULL, payload TEXT NOT NULL, payload_sha256 TEXT NOT NULL,
 PRIMARY KEY(patient_id,patient_sequence)
);
CREATE TABLE live_projection_receipts (
 id TEXT PRIMARY KEY, archive_id TEXT NOT NULL REFERENCES observed_archives(id),
 manifest_sha256 TEXT NOT NULL, projection_version TEXT NOT NULL, payload TEXT NOT NULL,
 UNIQUE(archive_id,manifest_sha256,projection_version)
);
CREATE TABLE live_export_receipts (
 id TEXT PRIMARY KEY, patient_id TEXT NOT NULL REFERENCES patients(id), owner_id TEXT NOT NULL,
 key TEXT NOT NULL, request_sha256 TEXT NOT NULL, payload TEXT NOT NULL, payload_sha256 TEXT NOT NULL,
 manifest BLOB NOT NULL, observed BLOB NOT NULL, facts BLOB NOT NULL, authority TEXT NOT NULL,
 UNIQUE(owner_id,patient_id,key)
);
INSERT INTO schema_migrations VALUES(3);
