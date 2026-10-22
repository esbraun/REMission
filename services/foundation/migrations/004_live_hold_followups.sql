CREATE TABLE live_hold_additional_tasks (
 id TEXT PRIMARY KEY, patient_id TEXT NOT NULL REFERENCES patients(id),
 episode_id TEXT NOT NULL, generation INTEGER NOT NULL,
 owner_id TEXT NOT NULL REFERENCES accounts(id), due_at TEXT NOT NULL, payload TEXT NOT NULL,
 FOREIGN KEY(episode_id,generation) REFERENCES live_hold_episodes(id,generation)
);
CREATE TABLE live_hold_task_bindings (
 episode_id TEXT NOT NULL, generation INTEGER NOT NULL, full_binding_sha256 TEXT NOT NULL,
 task_id TEXT NOT NULL UNIQUE, anchor_task_id TEXT REFERENCES live_hold_tasks(id),
 additional_task_id TEXT REFERENCES live_hold_additional_tasks(id), payload TEXT NOT NULL,
 PRIMARY KEY(episode_id,generation,full_binding_sha256),
 FOREIGN KEY(episode_id,generation) REFERENCES live_hold_episodes(id,generation),
 CHECK((anchor_task_id IS NOT NULL)+(additional_task_id IS NOT NULL)=1),
 CHECK(task_id=COALESCE(anchor_task_id,additional_task_id))
);
CREATE TABLE live_hold_additional_task_events (
 id TEXT PRIMARY KEY, task_id TEXT NOT NULL REFERENCES live_hold_additional_tasks(id),
 operation_id TEXT NOT NULL, payload TEXT NOT NULL
);
CREATE TRIGGER followup_binding_relation BEFORE INSERT ON live_hold_task_bindings
WHEN NOT EXISTS (
 SELECT 1 FROM live_hold_episodes e JOIN patients p ON p.id=e.patient_id
 LEFT JOIN live_hold_tasks a ON a.id=NEW.anchor_task_id
 LEFT JOIN live_hold_additional_tasks x ON x.id=NEW.additional_task_id
 WHERE e.id=NEW.episode_id AND e.generation=NEW.generation
 AND COALESCE(a.patient_id,x.patient_id)=e.patient_id
 AND COALESCE(a.episode_id,x.episode_id)=e.id
 AND COALESCE(a.generation,x.generation)=e.generation
 AND COALESCE(a.owner_id,x.owner_id)=p.owner_id
) BEGIN SELECT RAISE(ABORT,'followup_task_relation_mismatch'); END;
INSERT INTO schema_migrations VALUES(4);
