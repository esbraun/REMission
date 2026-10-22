CREATE TABLE analysis_attempts (
 job_id TEXT PRIMARY KEY REFERENCES pending_work(id),
 patient_id TEXT NOT NULL REFERENCES patients(id), owner_id TEXT NOT NULL REFERENCES accounts(id),
 previous_attempt TEXT REFERENCES analysis_attempts(job_id),
 request_json TEXT NOT NULL, input_sha256 TEXT NOT NULL, history_sha256 TEXT NOT NULL,
 cutoff TEXT NOT NULL, configuration_json TEXT NOT NULL, cohort_json TEXT NOT NULL,
 status TEXT NOT NULL CHECK(status IN ('queued','running','completed','failed','abstained')),
 stage TEXT NOT NULL CHECK(stage IN ('queued','preparing','fitting','diagnostics','rollouts','complete','failed','abstained')),
 claim_token TEXT, created_at TEXT NOT NULL, started_at TEXT, finished_at TEXT,
 failure_reason TEXT, result_json TEXT, artifact_root TEXT, progress_json TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX analysis_patient_history ON analysis_attempts(patient_id,created_at,job_id);
CREATE UNIQUE INDEX analysis_one_active_patient ON analysis_attempts(patient_id) WHERE status IN ('queued','running');
CREATE TRIGGER analysis_frozen_identity BEFORE UPDATE ON analysis_attempts
WHEN NEW.job_id IS NOT OLD.job_id OR NEW.patient_id IS NOT OLD.patient_id OR NEW.owner_id IS NOT OLD.owner_id
 OR NEW.previous_attempt IS NOT OLD.previous_attempt OR NEW.request_json IS NOT OLD.request_json
 OR NEW.input_sha256 IS NOT OLD.input_sha256 OR NEW.history_sha256 IS NOT OLD.history_sha256
 OR NEW.cutoff IS NOT OLD.cutoff OR NEW.configuration_json IS NOT OLD.configuration_json
 OR NEW.cohort_json IS NOT OLD.cohort_json OR NEW.created_at IS NOT OLD.created_at
 OR OLD.status IN ('completed','failed','abstained')
BEGIN SELECT RAISE(ABORT,'immutable_analysis_attempt'); END;
CREATE TRIGGER analysis_no_delete BEFORE DELETE ON analysis_attempts BEGIN SELECT RAISE(ABORT,'immutable_analysis_attempt'); END;
INSERT INTO schema_migrations(version) VALUES(5);
