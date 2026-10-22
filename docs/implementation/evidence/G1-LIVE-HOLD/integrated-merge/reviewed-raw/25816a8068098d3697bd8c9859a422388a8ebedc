"""Real routes/cookies/SQLite; no injected principal or storage mocks."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sqlite3
import tempfile
import threading
import unittest

from fastapi.testclient import TestClient
from services.foundation.app import Settings, create_app
from services.foundation.cli import DEMO_PASSWORDS, reset_password, seed
from services.foundation.replay import replay
from services.foundation.replay import parse_observed
from services.foundation.store import Store, canonical, digest, instant
from services.foundation.workflow import history, record_header
from live_helpers import fresh_store

ORIGIN="http://127.0.0.1:8765"


class Clock:
    def __init__(self,at=None):self.at=at or instant("2026-10-21T12:00:00+00:00")
    def __call__(self):return self.at


def observed(identifier="report-1",kind="daily_report",patient="SYN-02",event="2026-10-21T07:00:00+00:00",available="2026-10-21T08:01:00+00:00",**updates):
    base=record_header(identifier,patient,instant(event));base.update(kind=kind,recorded_at=available,available_at=available)
    base["source"]["adapter"]="patient_report"
    if kind=="daily_report":base.update(sleep_quality=6.0,function=5.0,adverse_symptoms=[],diary_sleep_minutes=360.0,goals=[],burden=1.0,missingness="observed")
    elif kind=="intercurrent_event":base.update(event_type="fall",detail="Synthetic fall requires review")
    elif kind=="consent":base.update(component="nof1",consent_version="1.0.0",oversight_version="1.0.0",consent_status="withdrawn",oversight_status="withdrawn",effective_at=event,expires_at=None,withdrawn_at=event)
    base.update(updates)
    raw=canonical({k:v for k,v in base.items() if k!="source"});base["source"]["raw_sha256"]=digest(raw)
    return {"record":base,"raw_source":raw}


class FoundationTests(unittest.TestCase):
    def setUp(self,start=None):
        self.directory=tempfile.TemporaryDirectory();self.path=Path(self.directory.name)/"real.sqlite"
        self.clock=Clock(start);self.store=fresh_store(self.path);self.store.clock=self.clock;seed(self.store)
        self.settings=Settings(self.path,self.store.installed,clock=self.clock)
        self.app=create_app(self.settings);self.client=TestClient(self.app,base_url=ORIGIN)
        self.login(self.client)

    def tearDown(self):self.client.close();self.directory.cleanup()

    def login(self,client,user="alice"):
        bootstrap=client.get("/api/session");self.assertEqual(bootstrap.status_code,200)
        result=client.post("/api/login",json={"username":user,"password":DEMO_PASSWORDS[user]},headers={"Origin":ORIGIN,"X-CSRF-Token":bootstrap.json()["csrf"]})
        self.assertEqual(result.status_code,200,result.text);return result.json()

    def headers(self,client=None,key="command-1"):
        client=client or self.client
        return {"Origin":ORIGIN,"X-CSRF-Token":client.get("/api/session").json()["csrf"],"Idempotency-Key":key}

    def approval(self,patient="SYN-02",client=None):
        workspace=(client or self.client).get("/api/patients/"+patient).json();snapshot=workspace["snapshot"]
        return dict(decision_id=snapshot["record_id"],mode="current",option="MED_A",rationale="Explicit ordinary synthetic choice",follow_up_at=(self.clock()+timedelta(days=7)).isoformat(),purpose="ordinary_treatment",**{key:snapshot[key.removeprefix("expected_")] for key in ["expected_patient_version","expected_state_version","expected_consent_version","expected_eligibility_version"]})

    def test_real_cookie_csrf_and_generic_auth(self):
        response=self.client.get("/api/session");cookie=self.client.cookies.get("remission_session")
        self.assertNotIn(cookie,response.text)
        anonymous=TestClient(self.app,base_url=ORIGIN);bootstrap=anonymous.get("/api/session")
        self.assertIn("HttpOnly",bootstrap.headers["set-cookie"]);self.assertIn("SameSite=lax",bootstrap.headers["set-cookie"])
        credentials={"username":"alice","password":DEMO_PASSWORDS["alice"]}
        self.assertEqual(anonymous.post("/api/login",json=credentials).status_code,403)
        for username in ["alice","missing"]:
            r=anonymous.post("/api/login",json={"username":username,"password":"wrong"},headers={"Origin":ORIGIN,"X-CSRF-Token":bootstrap.json()["csrf"]})
            self.assertEqual(r.json(),{"code":"invalid_credentials","detail":"Invalid username or password"})
        headers=self.headers();headers["Origin"]="https://other.example"
        self.assertEqual(self.client.post("/api/logout",headers=headers).status_code,403)
        self.assertEqual(self.client.post("/api/logout",headers=self.headers()).status_code,200)
        self.assertEqual(self.client.get("/api/patients").status_code,401)
        anonymous.close()

    def test_expiry_reset_revocation_and_rate_limit(self):
        reset_password(self.store,"alice","Replacement-synthetic-password!")
        self.assertEqual(self.client.get("/api/patients").status_code,401)
        other=TestClient(self.app,base_url=ORIGIN);self.login(other,"bob")
        self.clock.at+=timedelta(seconds=1801)
        self.assertEqual(other.get("/api/patients").status_code,401)
        bootstrap=other.get("/api/session").json()
        for i in range(6):
            response=other.post("/api/login",json={"username":"bob","password":"wrong"},headers={"Origin":ORIGIN,"X-CSRF-Token":bootstrap["csrf"]})
        self.assertEqual(response.status_code,429);other.close()

    def test_owner_scoped_panel_direct_nested_history_task_job(self):
        bob=TestClient(self.app,base_url=ORIGIN);self.login(bob,"bob")
        self.assertEqual(self.client.get("/api/patients?doctor_id=bob").json()["denominator"],10)
        self.assertEqual(bob.get("/api/patients").json()["denominator"],1)
        data=self.approval("SYN-B01",bob);response=bob.post("/api/patients/SYN-B01/approve",json=data,headers=self.headers(bob)).json()
        for path in ["/api/patients/SYN-B01","/api/patients/SYN-B01/events/unknown","/api/patients/SYN-B01/draft","/api/patients/SYN-B01/history/"+response["bundle_id"],"/api/patients/SYN-B01/history/"+response["bundle_id"]+"/later-outcomes","/api/tasks/"+response["task_id"]]:
            r=self.client.get(path);self.assertEqual(r.status_code,404,path);self.assertEqual(r.json(),{"code":"not_found","detail":"Resource not found"})
        with self.store.transaction(write=True) as db:db.execute("INSERT INTO pending_work VALUES('bob-job','SYN-B01','unavailable','not implemented')")
        self.assertEqual(self.client.get("/api/jobs/bob-job").status_code,404)
        self.assertEqual(bob.get("/api/jobs/bob-job").json()["status"],"unavailable");bob.close()

    def test_approval_atomic_history_idempotency_and_immutability(self):
        data=self.approval();headers=self.headers();r=self.client.post("/api/patients/SYN-02/approve",json=data,headers=headers)
        self.assertEqual(r.status_code,200,r.text);saved=r.json()
        self.assertEqual(self.client.post("/api/patients/SYN-02/approve",json=data,headers=headers).json(),saved)
        changed={**data,"option":"MED_B"}
        self.assertEqual(self.client.post("/api/patients/SYN-02/approve",json=changed,headers=headers).status_code,409)
        self.assertEqual(self.client.post("/api/patients/SYN-02/approve",json=data,headers=self.headers(key="new-key")).status_code,409)
        historical=self.client.get("/api/patients/SYN-02/history/"+saved["bundle_id"]).json()
        self.assertEqual(historical["mode"],"historical");self.assertEqual(digest(canonical(historical["display"])),historical["display_sha256"])
        self.assertEqual(historical["display"]["workspace"]["snapshot"]["posterior"],None)
        with self.store.transaction() as db:
            self.assertEqual(db.execute("SELECT count(*) FROM tasks").fetchone()[0],1)
            self.assertEqual(db.execute("SELECT count(*) FROM state_changes").fetchone()[0],1)
            for statement in ["UPDATE bundles SET display='{}'","DELETE FROM decisions","DELETE FROM events","DELETE FROM tasks"]:
                # Trigger firing requires a real row; events are exercised by
                # the lineage test rather than claiming a zero-row DELETE ran.
                if statement=="DELETE FROM events":continue
                with self.assertRaises(sqlite3.IntegrityError):db.execute(statement)
        self.assertEqual(self.client.get("/api/patients/SYN-02/receipts/command-1").json(),saved)
        restarted=TestClient(create_app(self.settings),base_url=ORIGIN);restarted.cookies.update(self.client.cookies)
        self.assertEqual(restarted.get("/api/patients/SYN-02/history/"+saved["bundle_id"]).json(),historical);restarted.close()

    def test_same_version_concurrent_approval_has_one_commit(self):
        second=TestClient(self.app,base_url=ORIGIN);self.login(second)
        data=self.approval();clients=[self.client,second];headers=[self.headers(key="race-a"),self.headers(second,key="race-b")];barrier=threading.Barrier(2)
        def submit(i):barrier.wait();return clients[i].post("/api/patients/SYN-02/approve",json=data,headers=headers[i]).status_code
        with ThreadPoolExecutor(2) as pool:codes=list(pool.map(submit,[0,1]))
        self.assertEqual(sorted(codes),[200,409])
        with self.store.transaction() as db:self.assertEqual(db.execute("SELECT count(*) FROM bundles").fetchone()[0],1)
        second.close()

    def test_hold_and_consent_invalidate_an_old_approval(self):
        data=self.approval();r=self.client.post("/api/patients/SYN-02/state",json={"expected_version":1,"stage":"ASSIGN-09","reason":"New synthetic fall"},headers=self.headers())
        self.assertEqual(r.status_code,200,r.text)
        self.assertEqual(self.client.post("/api/patients/SYN-02/approve",json=data,headers=self.headers()).status_code,409)
        self.assertFalse(self.client.get("/api/patients/SYN-02").json()["permissions"]["approve_ordinary"])
        fresh=self.approval("SYN-B01",self._bob())
        self.assertIsNotNone(fresh)
        consent=observed("consent-withdrawn",kind="consent")
        self.assertEqual(self.client.post("/api/patients/SYN-02/events",json=consent,headers=self.headers(key="withdrawal")).status_code,200)
        self.assertEqual(self.client.post("/api/patients/SYN-02/randomize",json={},headers=self.headers()).json()["code"],"engine_unavailable")

    def _bob(self):
        client=TestClient(self.app,base_url=ORIGIN);self.login(client,"bob");self.addCleanup(client.close);return client

    def test_injected_rollback_persists_nothing(self):
        def fail(where):
            if where=="after_follow_up":raise RuntimeError("deliberate rollback probe")
        client=TestClient(create_app(Settings(self.path,self.store.installed,clock=self.clock,fault=fail)),base_url=ORIGIN,raise_server_exceptions=False);self.login(client)
        response=client.post("/api/patients/SYN-02/approve",json=self.approval(client=client),headers=self.headers(client))
        self.assertEqual(response.status_code,500)
        with self.store.transaction() as db:
            self.assertEqual(db.execute("SELECT count(*) FROM bundles").fetchone()[0],0)
            self.assertEqual(db.execute("SELECT count(*) FROM tasks").fetchone()[0],0)
            self.assertEqual(db.execute("SELECT version FROM patients WHERE id='SYN-02'").fetchone()[0],1)
        client.close()

    def test_history_write_denial_even_forged_current_and_stage_statuses(self):
        data=self.approval();response=self.client.post("/api/patients/SYN-02/approve",json=data,headers=self.headers()).json()
        for mode in ["historical","current"]:
            r=self.client.post("/api/patients/SYN-02/approve",json={**data,"mode":mode},headers=self.headers(key=mode))
            self.assertEqual(r.status_code,409)
        for i in range(1,11):
            workspace=self.client.get(f"/api/patients/SYN-{i:02d}").json()
            self.assertFalse(workspace["permissions"]["randomize"]);self.assertEqual(workspace["engines"]["bayesian"],"unavailable")
            self.assertEqual(workspace["estimates"]["status"],"pending")

    def test_drafts_require_current_identity_version_and_explicit_resume(self):
        data=self.approval();draft=dict(decision_id=data["decision_id"],expected_version=1,mode="current",option=None,rationale="Saved only",follow_up_at=data["follow_up_at"])
        self.assertEqual(self.client.put("/api/patients/SYN-02/draft",json=draft,headers=self.headers()).json()["approval_created"],False)
        self.assertTrue(self.client.get("/api/patients/SYN-02/draft").json()["requires_explicit_resume"])
        self.assertEqual(self.client.put("/api/patients/SYN-01/draft",json=draft,headers=self.headers()).status_code,409)
        self.assertEqual(self.client.put("/api/patients/SYN-02/draft",json={**draft,"mode":"historical"},headers=self.headers()).status_code,409)
        self.client.post("/api/logout",headers=self.headers());self.login(self.client)
        self.assertTrue(self.client.get("/api/patients/SYN-02/draft").json()["auth_generation_changed"])

    def test_ingestion_lineage_raw_source_and_rejected_receipt(self):
        original=observed();self.assertEqual(self.client.post("/api/patients/SYN-02/events",json=original,headers=self.headers(key="raw-1")).status_code,200)
        self.assertEqual(self.client.post("/api/patients/SYN-02/events",json=original,headers=self.headers(key="raw-1")).status_code,200)
        missing=observed("missing-correction",revision=2,supersedes="nonexistent",lineage_id="missing")
        self.assertEqual(self.client.post("/api/patients/SYN-02/events",json=missing,headers=self.headers(key="bad-correction")).status_code,422)
        with self.store.transaction() as db:
            self.assertEqual(db.execute("SELECT count(*) FROM events").fetchone()[0],1)
            self.assertEqual(db.execute("SELECT status FROM ingestion_receipts WHERE transport_key='bad-correction'").fetchone()[0],"rejected")
            with self.assertRaises(sqlite3.IntegrityError):db.execute("DELETE FROM events")
        forged={**original,"record":{**original["record"],"latent_truth":1.0}}
        self.assertEqual(self.client.post("/api/patients/SYN-02/events",json=forged,headers=self.headers(key="truth")).status_code,422)

    def test_replay_cutoffs_corrections_retractions_and_duplicate_headers(self):
        original=observed();correction=observed("report-2",available="2026-10-21T10:00:00+00:00",lineage_id="report-1",revision=2,supersedes="report-1",record_status="corrected",sleep_quality=8.0)
        tombstone=observed("report-3",available="2026-10-21T11:00:00+00:00",lineage_id="report-1",revision=3,supersedes="report-2",record_status="retracted",sleep_quality=8.0)
        duplicate=json.loads(canonical(original));duplicate["record"].update(record_id="report-duplicate",lineage_id="report-duplicate",duplicate_of="report-1",available_at="2026-10-21T09:00:00+00:00")
        replay(self.store,"lineage",[tombstone,duplicate,correction,original],"2026-10-21T12:00:00+00:00")
        with self.store.transaction() as db:
            h=history(db,"SYN-02")
            self.assertEqual(h.project(instant("2026-10-21T08:01:00+00:00")).records,[])
            self.assertEqual(h.project(instant("2026-10-21T08:01:00.000001+00:00")).records[0].sleep_quality,6.0)
            self.assertEqual(h.project(instant("2026-10-21T10:00:00+00:00")).records[0].sleep_quality,6.0)
            self.assertEqual(h.project(instant("2026-10-21T10:00:00.000001+00:00")).records[0].sleep_quality,8.0)
            projected=h.project(self.clock());self.assertEqual(projected.records,[]);self.assertEqual(len(projected.provenance),4)

    def test_replay_restart_cursor_and_order_invariance(self):
        entries=[observed("report-a"),observed("report-b",event="2026-10-20T07:00:00+00:00",available="2026-10-20T08:00:00+00:00")]
        def crash(_):raise RuntimeError("deliberate replay crash")
        with self.assertRaises(RuntimeError):replay(self.store,"resume",entries,"2026-10-21T12:00:00+00:00",fault=crash)
        with self.store.transaction() as db:self.assertEqual(db.execute("SELECT cursor FROM replay_runs").fetchone()[0],0);self.assertEqual(db.execute("SELECT count(*) FROM events").fetchone()[0],0)
        replay(Store(self.path,self.store.installed,clock=self.clock),"resume",list(reversed(entries)),"2026-10-21T12:00:00+00:00")
        other=fresh_store(Path(self.directory.name)/"reverse.sqlite");other.clock=self.clock;seed(other);replay(other,"resume",entries,"2026-10-21T12:00:00+00:00")
        with self.store.transaction() as first,other.transaction() as second:
            a=first.execute("SELECT display_sha256 FROM decisions WHERE id=(SELECT current_decision FROM patients WHERE id='SYN-02')").fetchone()[0]
            b=second.execute("SELECT display_sha256 FROM decisions WHERE id=(SELECT current_decision FROM patients WHERE id='SYN-02')").fetchone()[0];self.assertEqual(a,b)

    def test_hold_arriving_during_approval_is_not_lost_to_stale_version(self):
        entered=threading.Event();release=threading.Event()
        def pause(where):
            if where=="after_follow_up":entered.set();self.assertTrue(release.wait(5))
        app=create_app(Settings(self.path,self.store.installed,clock=self.clock,fault=pause))
        first=TestClient(app,base_url=ORIGIN);second=TestClient(app,base_url=ORIGIN);self.login(first);self.login(second)
        approval=self.approval(client=first);approval_headers=self.headers(first,key="race-before-hold");hold_headers=self.headers(second)
        with ThreadPoolExecutor(2) as pool:
            a=pool.submit(first.post,"/api/patients/SYN-02/approve",json=approval,headers=approval_headers)
            self.assertTrue(entered.wait(5))
            hold=pool.submit(second.post,"/api/patients/SYN-02/state",json={"expected_version":1,"stage":"ASSIGN-09","reason":"Concurrent new safety concern"},headers=hold_headers)
            release.set();self.assertEqual(a.result().status_code,200);self.assertEqual(hold.result().status_code,200)
        current=second.get("/api/patients/SYN-02").json()
        self.assertEqual(current["snapshot"]["workflow"]["clinical"],"clinical_hold");self.assertFalse(current["permissions"]["approve_ordinary"])
        first.close();second.close()

    def test_report_route_idempotency_and_post_death_rejection(self):
        payload={"event_at":"2026-10-21T07:00:00+00:00","sleep_quality":6.0,"function":5.0,"diary_sleep_minutes":360.0,"note":"Synthetic note"}
        headers=self.headers(key="observed-report")
        first=self.client.post("/api/patients/SYN-02/reports",json=payload,headers=headers)
        self.assertEqual(first.status_code,200,first.text)
        self.assertEqual(self.client.post("/api/patients/SYN-02/reports",json=payload,headers=headers).json()["status"],"accepted")
        self.assertEqual(self.client.post("/api/patients/SYN-02/reports",json={**payload,"sleep_quality":3.0},headers=headers).status_code,409)
        death=observed("death",kind="intercurrent_event",event="2026-10-21T11:00:00+00:00",available="2026-10-21T11:00:00+00:00",event_type="death")
        self.assertEqual(self.client.post("/api/patients/SYN-02/events",json=death,headers=self.headers(key="death")).status_code,200)
        after={**payload,"event_at":"2026-10-21T11:30:00+00:00"}
        self.assertEqual(self.client.post("/api/patients/SYN-02/reports",json=after,headers=self.headers(key="invalid-post-death")).status_code,422)

    def test_raw_source_privileged_payload_rejects_even_with_resealed_hash(self):
        forged=observed("forged-raw")
        raw=json.loads(forged["raw_source"]);raw["structural_parameters"]={"latent_truth":7.0}
        forged["raw_source"]=canonical(raw);forged["record"]["source"]["raw_sha256"]=digest(forged["raw_source"])
        result=self.client.post("/api/patients/SYN-02/events",json=forged,headers=self.headers(key="forged-raw"))
        self.assertEqual(result.status_code,422,result.text)
        with self.store.transaction() as db:self.assertEqual(db.execute("SELECT count(*) FROM events").fetchone()[0],0)

    def test_naive_nested_future_and_dst_overnight_records(self):
        naive=observed("naive",event="2026-10-21T07:00:00+00:00");naive["record"]["event_at"]="2026-10-21T07:00:00"
        with self.assertRaises(ValueError):parse_observed(canonical(naive["record"]).encode())
        base=record_header("overnight","SYN-02",instant("2026-11-01T09:30:00+00:00"))
        base.update(kind="oura_like",record_type="sleep_episode",local_date="2026-11-01",timezone="America/Los_Angeles",episode_start="2026-10-31T23:00:00-07:00",episode_end="2026-11-01T01:30:00-08:00",sync_at="2026-11-01T10:00:00+00:00",available_at="2026-11-01T10:01:00+00:00",estimated_sleep_minutes=210.0,estimated_wake_minutes=0.0,device_version="synthetic-fixture-1",quality_flags=[],missingness="observed")
        record=parse_observed(canonical(base).encode())
        self.assertEqual((record.episode_end-record.episode_start).total_seconds(),12600)
        self.assertEqual(str(record.local_date),"2026-11-01")
        observed_pain=record_header("nested","SYN-02",instant("2026-10-21T07:00:00+00:00"));observed_pain.update(kind="observation",lab_reference_context=None,measure={"concept":"pain","value":1.0,"unit":"dimensionless","observed_at":"2026-10-21T07:00:00+00:00","available_at":"2026-10-22T07:00:00+00:00"})
        with self.assertRaises(ValueError):parse_observed(canonical(observed_pain).encode())

    def test_failed_replay_retains_rejected_receipt_after_batch_rollback(self):
        bad=observed("bad-replay",lineage_id="unavailable-original",revision=2,supersedes="unavailable-original")
        with self.assertRaises(ValueError):replay(self.store,"failed-replay",[bad],"2026-10-21T12:00:00+00:00")
        with self.store.transaction() as db:
            self.assertEqual(db.execute("SELECT count(*) FROM events").fetchone()[0],0)
            self.assertEqual(db.execute("SELECT cursor FROM replay_runs WHERE id='failed-replay'").fetchone()[0],0)
            self.assertEqual(db.execute("SELECT status FROM ingestion_receipts WHERE run_id='failed-replay'").fetchone()[0],"rejected")

    def test_current_death_before_equal_after_and_strict_learner_boundary(self):
        boundary=instant("2026-10-21T12:00:00+00:00")
        for offset in (-1,0,1):
            with self.subTest(offset=offset):
                probe=FoundationTests();probe.setUp(start=boundary-timedelta(seconds=1))
                try:
                    probe.clock.at=boundary-timedelta(seconds=1)
                    report=observed("boundary-report",event="2026-10-21T10:00:00+00:00",available=boundary.isoformat(),recorded_at=probe.clock().isoformat())
                    death=observed("boundary-death",kind="intercurrent_event",event="2026-10-21T11:00:00+00:00",available=boundary.isoformat(),recorded_at=probe.clock().isoformat(),event_type="death")
                    for key,payload in [("report",report),("death",death)]:
                        result=probe.client.post("/api/patients/SYN-02/events",json=payload,headers=probe.headers(key=key))
                        self.assertEqual(result.status_code,200,result.text)
                    probe.clock.at=boundary+timedelta(seconds=offset)
                    workspace=probe.client.get("/api/patients/SYN-02").json()
                    clear=probe.client.post("/api/patients/SYN-02/state",json={"expected_version":workspace["snapshot"]["patient_version"],"stage":"ASSIGN-02","reason":"Boundary composition review"},headers=probe.headers(key="clear"))
                    approval=probe.client.post("/api/patients/SYN-02/approve",json=probe.approval(),headers=probe.headers(key="fresh-approval"))
                    self.assertEqual(clear.status_code,200 if offset<0 else 409,clear.text)
                    self.assertEqual(approval.status_code,200 if offset<0 else 409,approval.text)
                    with probe.store.transaction() as db:
                        self.assertEqual(db.execute("SELECT count(*) FROM bundles").fetchone()[0],1 if offset<0 else 0)
                        self.assertEqual(db.execute("SELECT count(*) FROM tasks").fetchone()[0],1 if offset<0 else 0)
                        h=history(db,"SYN-02")
                        self.assertEqual(h.project(boundary).records,[])
                        self.assertEqual({r.record_id for r in h.project(boundary+timedelta(microseconds=1)).records},{"boundary-report","boundary-death"})
                        self.assertEqual(len(h.records),2)
                finally:probe.tearDown()

    def test_live_equal_time_death_cannot_clear_or_persist_fresh_approval(self):
        death=observed("live-death",kind="intercurrent_event",event="2026-10-21T11:00:00+00:00",available="2026-10-21T11:00:00+00:00",event_type="death")
        admitted=self.client.post("/api/patients/SYN-02/events",json=death,headers=self.headers(key="death"))
        self.assertEqual(admitted.status_code,200,admitted.text)
        workspace=self.client.get("/api/patients/SYN-02").json()
        self.assertFalse(workspace["permissions"]["approve_ordinary"])
        for offset in (0,1):
            self.clock.at+=timedelta(microseconds=offset)
            clear=self.client.post("/api/patients/SYN-02/state",json={"expected_version":workspace["snapshot"]["patient_version"],"stage":"ASSIGN-02","reason":"Attempt terminal exclusion clearance"},headers=self.headers(key=f"clear-{offset}"))
            approval=self.client.post("/api/patients/SYN-02/approve",json=self.approval(),headers=self.headers(key=f"approve-{offset}"))
            self.assertEqual(clear.status_code,409,clear.text);self.assertEqual(approval.status_code,409,approval.text)
        with self.store.transaction() as db:
            self.assertEqual(db.execute("SELECT count(*) FROM bundles").fetchone()[0],0)
            self.assertEqual(db.execute("SELECT count(*) FROM tasks").fetchone()[0],0)
            self.assertEqual(history(db,"SYN-02").project(instant("2026-10-21T12:00:00+00:00")).records,[])

    def test_safety_lineage_retraction_correction_duplicates_and_active_control(self):
        for mode in ("retracted","changed-type","still-active"):
            with self.subTest(mode=mode):
                probe=FoundationTests();probe.setUp()
                try:
                    original=observed("safety-original",kind="intercurrent_event")
                    def ingest(payload,key):
                        response=probe.client.post("/api/patients/SYN-02/events",json=payload,headers=probe.headers(key=key))
                        self.assertEqual(response.status_code,200,response.text)
                    ingest(original,"original");probe.clock.at+=timedelta(seconds=1)
                    correction=observed("safety-head",kind="intercurrent_event",lineage_id="safety-original",revision=2,supersedes="safety-original",record_status="retracted" if mode=="retracted" else "corrected",event_type="discharge" if mode=="changed-type" else "fall")
                    ingest(correction,"correction")
                    workspace=probe.client.get("/api/patients/SYN-02").json()
                    clear=probe.client.post("/api/patients/SYN-02/state",json={"expected_version":workspace["snapshot"]["patient_version"],"stage":"ASSIGN-02","reason":"Clinician reviewed source correction"},headers=probe.headers(key="clear"))
                    self.assertEqual(clear.status_code,200,clear.text)
                    probe.clock.at+=timedelta(seconds=1)
                    duplicate=json.loads(canonical(original));duplicate["record"].update(record_id="safety-duplicate",lineage_id="safety-duplicate",duplicate_of="safety-original")
                    ingest(duplicate,"duplicate")
                    ingest(observed("unrelated-report"),"unrelated")
                    current=probe.client.get("/api/patients/SYN-02").json()
                    self.assertEqual(current["permissions"]["approve_ordinary"],mode!="still-active")
                    self.assertEqual(current["stage"],"ASSIGN-09" if mode=="still-active" else "ASSIGN-02")
                    with probe.store.transaction() as db:
                        h=history(db,"SYN-02");self.assertEqual(len(h.records),4)
                        heads={r.record_id for r in h.as_known_at(probe.clock()+timedelta(microseconds=1))}
                        self.assertNotIn("safety-original",heads);self.assertNotIn("safety-duplicate",heads)
                        self.assertEqual("safety-head" in heads,mode!="retracted")
                finally:probe.tearDown()

    def test_equal_arrival_lineage_and_batch_partition_have_identical_final_display(self):
        original=observed("zzz-original",available="2026-10-21T10:00:00+00:00")
        correction=observed("aaa-correction",available="2026-10-21T10:00:00+00:00",lineage_id="zzz-original",revision=2,supersedes="zzz-original",record_status="corrected",sleep_quality=8.0)
        third=observed("separate-arrival",event="2026-10-20T07:00:00+00:00",available="2026-10-20T08:00:00+00:00")
        entries=[correction,third,original]
        replay(self.store,"partitioned",entries,"2026-10-21T12:00:00+00:00",batch_size=1)
        second=fresh_store(Path(self.directory.name)/"single-batch.sqlite");second.clock=self.clock;seed(second)
        replay(second,"partitioned",list(reversed(entries)),"2026-10-21T12:00:00+00:00",batch_size=100)
        with self.store.transaction() as a,second.transaction() as b:
            query="SELECT display_sha256 FROM decisions WHERE id=(SELECT current_decision FROM patients WHERE id='SYN-02')"
            self.assertEqual(a.execute(query).fetchone()[0],b.execute(query).fetchone()[0])


if __name__=="__main__":unittest.main()
