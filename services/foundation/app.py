"""Actual cookie-authenticated synthetic-care service; no statistical worker."""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hmac
import json
from pathlib import Path
import secrets
from typing import Callable, Literal
from urllib.parse import urlparse
import uuid

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import Field
from contracts.domain.common import Action, StrictModel
from contracts.domain.entities import Approval, DecisionSnapshot, ViewContext
from contracts.domain.boundaries import ContractViolation, validate_approval
from .store import Store, canonical, digest, instant, timestamp
from .workflow import create_decision, history, record_header, state_for
from .replay import append_event, apply_current_state, parse_observed

COOKIE = "remission_session"
HASHER = PasswordHasher()


@dataclass(frozen=True)
class Settings:
    database: Path
    origin: str = "http://127.0.0.1:8765"
    session_seconds: int = 1800
    preauth_seconds: int = 600
    login_window_seconds: int = 300
    login_max_attempts: int = 5
    clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc)
    fault: Callable[[str], None] | None = None
    web_root: Path | None = None

    @property
    def secure_cookie(self):
        return urlparse(self.origin).hostname not in ("127.0.0.1", "localhost", "::1")


class APIError(Exception):
    def __init__(self, status: int, code: str, detail: str):
        self.status, self.code, self.detail = status, code, detail


class Login(StrictModel):
    username: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=1, max_length=256)


class ApprovalInput(StrictModel):
    decision_id: str
    expected_patient_version: int = Field(gt=0)
    expected_state_version: int = Field(gt=0)
    expected_consent_version: int = Field(gt=0)
    expected_eligibility_version: int = Field(gt=0)
    mode: Literal["current", "historical", "retrospective_evaluation"]
    option: Action
    rationale: str = Field(min_length=1, max_length=1000)
    follow_up_at: str
    purpose: Literal["ordinary_treatment"]


class StateInput(StrictModel):
    expected_version: int = Field(gt=0)
    stage: Literal["ASSIGN-01", "ASSIGN-02", "ASSIGN-03", "ASSIGN-04", "ASSIGN-05", "ASSIGN-06", "ASSIGN-07", "ASSIGN-08", "ASSIGN-09", "ASSIGN-10"]
    reason: str = Field(min_length=1, max_length=256)


class DraftInput(StrictModel):
    decision_id: str
    expected_version: int = Field(gt=0)
    mode: Literal["current", "historical"]
    option: Action | None
    rationale: str = Field(max_length=1000)
    follow_up_at: str


class IngestionInput(StrictModel):
    record: dict
    raw_source: str = Field(max_length=32768)


class ReportInput(StrictModel):
    event_at: str
    sleep_quality: float = Field(ge=0,le=10)
    function: float = Field(ge=0,le=10)
    diary_sleep_minutes: float = Field(ge=0,le=1440)
    note: str = Field(max_length=256)


def create_app(settings: Settings) -> FastAPI:
    store = Store(settings.database)
    app = FastAPI(title="REMission synthetic foundation", docs_url=None, redoc_url=None, openapi_url=None)
    app.state.store, app.state.settings = store, settings
    dummy_hash = HASHER.hash("non-account-timing-control")

    @app.exception_handler(APIError)
    async def api_error(_request, error):
        return JSONResponse({"code": error.code, "detail": error.detail}, status_code=error.status)

    @app.exception_handler(ContractViolation)
    async def contract_error(_request, error):
        return JSONResponse({"code": error.code, "detail": str(error)}, status_code=409)

    @app.middleware("http")
    async def headers(request, call_next):
        # This service never permits a browser response to be cached across a
        # patient/account/authentication generation.
        response = await call_next(request)
        response.headers.update({"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff", "Referrer-Policy": "same-origin",
                                 "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; object-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"})
        return response

    async def body(request: Request, model):
        raw = await request.body()
        if len(raw) > 65536:
            raise APIError(413, "request_too_large", "Request exceeds synthetic admission limit")
        try:
            return model.model_validate_json(raw)
        except ValueError:
            raise APIError(422, "invalid_request", "Request does not match the accepted foundation contract")

    def session(db, request, *, required=True, mutation=False):
        token = request.cookies.get(COOKIE, "")
        row = db.execute("SELECT s.*,a.display_name,a.username,a.auth_version AS current_auth_version FROM sessions s LEFT JOIN accounts a ON a.id=s.account_id WHERE token_hash=?", (digest(token),)).fetchone()
        valid = row and not row["revoked"] and row["expires_at"] > settings.clock().timestamp() and (not row["account_id"] or row["auth_version"] == row["current_auth_version"])
        if not valid or (required and not row["account_id"]):
            raise APIError(401, "authentication_required", "Sign in again; unsaved local input must be cleared")
        if mutation:
            if request.headers.get("origin") != settings.origin or not hmac.compare_digest(request.headers.get("x-csrf-token", ""), row["csrf"]):
                raise APIError(403, "csrf_rejected", "Refresh this session before submitting")
        return row

    def own(db, patient_id, account_id):
        row = db.execute("SELECT * FROM patients WHERE id=? AND owner_id=?", (patient_id, account_id)).fetchone()
        if not row:
            raise APIError(404, "not_found", "Resource not found")
        return row

    def put_cookie(response, token):
        response.set_cookie(COOKIE, token, httponly=True, secure=settings.secure_cookie, samesite="lax", max_age=settings.session_seconds, path="/")

    def read_decision(db, patient):
        return db.execute("SELECT * FROM decisions WHERE id=? AND patient_id=?", (patient["current_decision"], patient["id"])).fetchone()

    @app.get("/health")
    def health():
        with store.transaction() as db:
            assert db.execute("SELECT version FROM schema_migrations").fetchone()[0] == 1
        return {"status": "ok", "synthetic": True, "runtime": "foundation-v1"}

    @app.get("/api/session")
    def bootstrap(request: Request):
        with store.transaction(write=True) as db:
            token = None
            try:
                current = session(db,request,required=False)
            except APIError:
                token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
                db.execute("INSERT INTO sessions(token_hash,csrf,expires_at) VALUES(?,?,?)", (digest(token),csrf,settings.clock().timestamp()+settings.preauth_seconds))
                current = db.execute("SELECT * FROM sessions WHERE token_hash=?", (digest(token),)).fetchone()
            principal = {"id":current["account_id"],"name":current["display_name"]} if current["account_id"] else None
            response = JSONResponse({"principal":principal,"csrf":current["csrf"],"auth_generation":current["token_hash"],"expires_at":current["expires_at"]})
            if token:
                put_cookie(response,token)
            return response

    @app.post("/api/login")
    async def login(request: Request):
        data = await body(request,Login)
        with store.transaction(write=True) as db:
            current=session(db,request,required=False,mutation=True)
            account_key=digest(data.username);source_key=digest(request.client.host if request.client else "unknown")
            attempts=db.execute("SELECT count(*) FROM login_attempts WHERE success=0 AND attempted_at>? AND (account_key=? OR source_key=?)",(settings.clock().timestamp()-settings.login_window_seconds,account_key,source_key)).fetchone()[0]
            if attempts>=settings.login_max_attempts:
                return JSONResponse({"code":"login_rate_limited","detail":"Try again later"},status_code=429)
            account=db.execute("SELECT * FROM accounts WHERE username=?",(data.username,)).fetchone()
            try:
                valid=HASHER.verify(account["password_hash"] if account else dummy_hash,data.password) and account is not None
            except (VerifyMismatchError,VerificationError):
                valid=False
            db.execute("INSERT INTO login_attempts(account_key,source_key,attempted_at,success) VALUES(?,?,?,?)",(account_key,source_key,settings.clock().timestamp(),int(valid)))
            if not valid:
                return JSONResponse({"code":"invalid_credentials","detail":"Invalid username or password"},status_code=401)
            db.execute("UPDATE sessions SET revoked=1 WHERE token_hash=?",(current["token_hash"],))
            token,csrf=secrets.token_urlsafe(32),secrets.token_urlsafe(32)
            db.execute("INSERT INTO sessions VALUES(?,?,?,?,?,0)",(digest(token),csrf,account["id"],account["auth_version"],settings.clock().timestamp()+settings.session_seconds))
            response=JSONResponse({"principal":{"id":account["id"],"name":account["display_name"]},"csrf":csrf,"auth_generation":digest(token),"expires_at":settings.clock().timestamp()+settings.session_seconds})
            put_cookie(response,token)
            return response

    @app.post("/api/logout")
    def logout(request: Request):
        with store.transaction(write=True) as db:
            current=session(db,request,mutation=True)
            db.execute("UPDATE sessions SET revoked=1 WHERE token_hash=?",(current["token_hash"],))
        response=JSONResponse({"status":"signed_out"});response.delete_cookie(COOKIE,path="/",secure=settings.secure_cookie,httponly=True,samesite="lax")
        return response

    @app.get("/api/patients")
    def panel(request: Request):
        with store.transaction() as db:
            current=session(db,request)
            rows=db.execute("SELECT id,name,state_json,cutoff,version FROM patients WHERE owner_id=? ORDER BY id",(current["account_id"],)).fetchall()
            return {"patients":[dict(id=r["id"],name=r["name"],state=json.loads(r["state_json"]),cutoff=r["cutoff"],version=r["version"]) for r in rows],"denominator":len(rows)}

    @app.get("/api/patients/{patient_id}")
    def workspace(patient_id: str,request: Request):
        with store.transaction() as db:
            current=session(db,request);patient=own(db,patient_id,current["account_id"])
            result=json.loads(read_decision(db,patient)["display"])
            result["tasks"]=[dict(id=r["id"],due_at=r["due_at"],owner_id=r["owner_id"],payload=json.loads(r["payload"])) for r in db.execute("SELECT * FROM tasks WHERE patient_id=?",(patient_id,))]
            result["history"]=[dict(id=r["id"],approved_at=r["approved_at"],display_sha256=r["display_sha256"]) for r in db.execute("SELECT id,approved_at,display_sha256 FROM bundles WHERE patient_id=? ORDER BY approved_at,id",(patient_id,))]
            result["mode"]="current";result["auth_generation"]=current["token_hash"]
            return result

    @app.get("/api/patients/{patient_id}/history/{bundle_id}")
    def historical(patient_id: str,bundle_id: str,request: Request):
        with store.transaction() as db:
            current=session(db,request);own(db,patient_id,current["account_id"])
            row=db.execute("SELECT * FROM bundles WHERE id=? AND patient_id=?",(bundle_id,patient_id)).fetchone()
            if not row:raise APIError(404,"not_found","Resource not found")
            return {"mode":"historical","patient_id":patient_id,"snapshot_id":bundle_id,"display":json.loads(row["display"]),"display_sha256":row["display_sha256"],"auth_generation":current["token_hash"]}

    @app.get("/api/patients/{patient_id}/history/{bundle_id}/later-outcomes")
    def later(patient_id: str,bundle_id: str,request: Request):
        with store.transaction() as db:
            current=session(db,request);own(db,patient_id,current["account_id"])
            bundle=db.execute("SELECT display FROM bundles WHERE id=? AND patient_id=?",(bundle_id,patient_id)).fetchone()
            if not bundle:raise APIError(404,"not_found","Resource not found")
            cutoff=instant(json.loads(bundle[0])["workspace"]["snapshot"]["cutoff"])
            values=[r.model_dump(mode="json") for r in history(db,patient_id).as_known_at(settings.clock()) if r.kind in ("isi","daily_report") and r.available_at>=cutoff]
            return {"label":"Retrospective later outcomes; not available to the original decision","records":values}

    @app.get("/api/patients/{patient_id}/events/{record_id}")
    def event(patient_id: str,record_id: str,request: Request):
        with store.transaction() as db:
            current=session(db,request);own(db,patient_id,current["account_id"])
            row=db.execute("SELECT payload FROM events WHERE id=? AND patient_id=?",(record_id,patient_id)).fetchone()
            if not row:raise APIError(404,"not_found","Resource not found")
            return json.loads(row[0])

    @app.get("/api/tasks/{task_id}")
    def task(task_id: str,request: Request):
        with store.transaction() as db:
            current=session(db,request)
            row=db.execute("SELECT t.payload FROM tasks t JOIN patients p ON t.patient_id=p.id WHERE t.id=? AND p.owner_id=?",(task_id,current["account_id"])).fetchone()
            if not row:raise APIError(404,"not_found","Resource not found")
            return json.loads(row[0])

    @app.get("/api/jobs/{job_id}")
    def job(job_id: str,request: Request):
        with store.transaction() as db:
            current=session(db,request)
            row=db.execute("SELECT w.id,w.status,w.reason FROM pending_work w JOIN patients p ON w.patient_id=p.id WHERE w.id=? AND p.owner_id=?",(job_id,current["account_id"])).fetchone()
            if not row:raise APIError(404,"not_found","Resource not found")
            return dict(row)

    @app.post("/api/patients/{patient_id}/approve")
    async def approve(patient_id: str,request: Request):
        data=await body(request,ApprovalInput);now=settings.clock()
        if not request.headers.get("idempotency-key") or len(request.headers["idempotency-key"])>128:
            raise APIError(422,"idempotency_required","Supply a bounded stable idempotency key")
        encoded=canonical(data.model_dump());key=request.headers["idempotency-key"]
        with store.transaction(write=True) as db:
            current=session(db,request,mutation=True);patient=own(db,patient_id,current["account_id"])
            prior=db.execute("SELECT * FROM receipts WHERE owner_id=? AND session_id=? AND key=?",(current["account_id"],current["token_hash"],key)).fetchone()
            if prior:
                if prior["scope"]!=patient_id or prior["payload_sha256"]!=digest(encoded):raise APIError(409,"idempotency_conflict","This key already identifies different content")
                return json.loads(prior["response"])
            decision=read_decision(db,patient);snapshot=DecisionSnapshot.model_validate_json(decision["snapshot"])
            workspace=json.loads(decision["display"])
            approval=Approval.model_validate_json(canonical(dict(**record_header("approval-"+uuid.uuid4().hex,patient_id,now),
                kind="approval",decision_id=data.decision_id,option=data.option,permitted_options=[],clinician_id=current["account_id"],purpose=data.purpose,
                **{k:getattr(data,k) for k in ["expected_patient_version","expected_state_version","expected_consent_version","expected_eligibility_version"]})))
            view=ViewContext(patient_id=patient_id,mode=data.mode,snapshot_id=data.decision_id if data.mode!="current" else None)
            validate_approval(approval,snapshot,view,"doctor",now,None,[r for r in history(db,patient_id).records if r.kind=="consent"])
            if not workspace["permissions"]["approve_ordinary"] or data.option not in [e["action"] for e in workspace["options"]]:raise APIError(409,"stage_action_unavailable","This stage requires review; no ordinary assignment is due")
            due=instant(data.follow_up_at)
            if due<=now or due>now+timedelta(days=365):raise APIError(422,"invalid_follow_up","Follow-up must be in the next 365 days")
            bundle_id=approval.record_id;task_id="follow-up-"+uuid.uuid4().hex
            saved=dict(workspace=workspace,approval=approval.model_dump(mode="json"),rationale=data.rationale,follow_up=dict(id=task_id,owner_id=current["account_id"],due_at=timestamp(due),status="pending"),audit=dict(actor=current["account_id"],change="ordinary synthetic approval",at=timestamp(now)))
            saved_bytes=canonical(saved)
            db.execute("INSERT INTO bundles VALUES(?,?,?,?,?,?)",(bundle_id,patient_id,snapshot.record_id,saved_bytes,digest(saved_bytes),timestamp(now)))
            db.execute("INSERT INTO tasks VALUES(?,?,?,?,?,?)",(task_id,patient_id,bundle_id,current["account_id"],timestamp(due),canonical(saved["follow_up"])))
            if settings.fault:settings.fault("after_follow_up")
            state=state_for("ASSIGN-03");state["plan"]={"option":data.option,"approved_at":timestamp(now),"rationale":data.rationale,"bundle_id":bundle_id}
            db.execute("UPDATE patients SET version=version+1,state_version=state_version+1,eligibility_version=eligibility_version+1,state_json=? WHERE id=?",(canonical(state),patient_id))
            db.execute("INSERT INTO state_changes VALUES(?,?,?,?,?)",("audit-"+uuid.uuid4().hex,patient_id,current["account_id"],timestamp(now),canonical(saved["audit"])))
            create_decision(db,patient_id,now)
            response={"status":"approved","bundle_id":bundle_id,"task_id":task_id,"display_sha256":digest(saved_bytes)}
            db.execute("INSERT INTO receipts VALUES(?,?,?,?,?,?)",(current["account_id"],current["token_hash"],key,patient_id,digest(encoded),canonical(response)))
            db.execute("DELETE FROM drafts WHERE owner_id=? AND patient_id=?",(current["account_id"],patient_id))
            return response

    @app.get("/api/patients/{patient_id}/receipts/{key}")
    def receipt(patient_id: str,key: str,request: Request):
        with store.transaction() as db:
            current=session(db,request);own(db,patient_id,current["account_id"])
            row=db.execute("SELECT response FROM receipts WHERE owner_id=? AND session_id=? AND key=? AND scope=?",(current["account_id"],current["token_hash"],key,patient_id)).fetchone()
            if not row:raise APIError(404,"not_found","Resource not found")
            return json.loads(row[0])

    @app.post("/api/patients/{patient_id}/state")
    async def state_change(patient_id: str,request: Request):
        data=await body(request,StateInput)
        with store.transaction(write=True) as db:
            current=session(db,request,mutation=True);patient=own(db,patient_id,current["account_id"])
            if data.expected_version!=patient["version"] and data.stage!="ASSIGN-09":raise APIError(409,"stale_state","Refresh before recording a state change")
            # Foundation allows hold, assessment and ordinary review transitions.
            # Statistical/protocol engines cannot be activated by changing stage.
            if data.stage not in ("ASSIGN-01","ASSIGN-02","ASSIGN-09","ASSIGN-10"):
                raise APIError(409,"engine_unavailable","Protocol engines remain unavailable")
            if data.stage!="ASSIGN-09" and any(r.kind=="intercurrent_event" and r.event_type=="death" for r in history(db,patient_id).as_known_at(settings.clock())):
                raise APIError(409,"outside_scope","A deceased patient cannot reenter ordinary approval")
            state=state_for(data.stage,data.reason);state["plan"]=json.loads(patient["state_json"])["plan"]
            db.execute("UPDATE patients SET version=version+1,state_version=state_version+1,eligibility_version=eligibility_version+1,state_json=? WHERE id=?",(canonical(state),patient_id))
            db.execute("INSERT INTO state_changes VALUES(?,?,?,?,?)",("state-"+uuid.uuid4().hex,patient_id,current["account_id"],timestamp(settings.clock()),canonical(data.model_dump())))
            create_decision(db,patient_id,settings.clock())
            return {"status":"recorded"}

    @app.post("/api/patients/{patient_id}/events")
    async def ingest(patient_id: str,request: Request):
        data=await body(request,IngestionInput)
        try:record=parse_observed(canonical(data.record).encode())
        except ValueError:raise APIError(422,"invalid_observed_record","Observed record failed source/timing/field validation")
        with store.transaction(write=True) as db:
            current=session(db,request,mutation=True);own(db,patient_id,current["account_id"])
            if record.patient_id!=patient_id:raise APIError(404,"not_found","Resource not found")
            key=request.headers.get("idempotency-key", "")
            if not key:raise APIError(422,"idempotency_required","Supply a transport key")
            run_id="live:"+current["account_id"]+":"+patient_id;raw=data.raw_source.encode();payload_hash=digest(canonical(data.model_dump()))
            prior=db.execute("SELECT * FROM ingestion_receipts WHERE run_id=? AND transport_key=?",(run_id,key)).fetchone()
            if prior:
                if prior["payload_sha256"]!=payload_hash:raise APIError(409,"idempotency_conflict","Transport key content changed")
                return {"status":prior["status"],"detail":prior["detail"]}
            try:
                if record.recorded_at>settings.clock():raise ValueError("future_recording_time")
                inserted=append_event(db,record,raw,received_at=settings.clock())
            except ValueError as error:
                db.execute("INSERT INTO ingestion_receipts VALUES(?,?,?,?,?)",(run_id,key,payload_hash,"rejected",str(error)))
                return JSONResponse({"status":"rejected","detail":str(error)},status_code=422)
            if inserted:apply_current_state(db,patient_id,settings.clock())
            db.execute("INSERT INTO ingestion_receipts VALUES(?,?,?,?,?)",(run_id,key,payload_hash,"accepted","validated"))
            return {"status":"accepted","record_id":record.record_id}

    @app.put("/api/patients/{patient_id}/draft")
    async def save_draft(patient_id: str,request: Request):
        data=await body(request,DraftInput)
        with store.transaction(write=True) as db:
            current=session(db,request,mutation=True);patient=own(db,patient_id,current["account_id"])
            if data.mode!="current":raise APIError(409,"historical_write","History is read-only")
            if data.decision_id!=patient["current_decision"] or data.expected_version!=patient["version"]:raise APIError(409,"stale_draft","Review current state before saving this draft")
            db.execute("INSERT INTO drafts VALUES(?,?,?,?,?,?) ON CONFLICT(owner_id,patient_id,decision_id) DO UPDATE SET auth_generation=excluded.auth_generation,base_version=excluded.base_version,payload=excluded.payload",
                       (current["account_id"],patient_id,data.decision_id,current["token_hash"],patient["version"],canonical(data.model_dump())))
            return {"status":"draft_saved","approval_created":False}

    @app.get("/api/patients/{patient_id}/draft")
    def saved_draft(patient_id: str,request: Request):
        with store.transaction() as db:
            current=session(db,request);patient=own(db,patient_id,current["account_id"])
            row=db.execute("SELECT * FROM drafts WHERE owner_id=? AND patient_id=? AND decision_id=?",(current["account_id"],patient_id,patient["current_decision"])).fetchone()
            return {"draft":json.loads(row["payload"]) if row else None,"requires_explicit_resume":bool(row),"base_valid":bool(row and row["base_version"]==patient["version"]),"auth_generation_changed":bool(row and row["auth_generation"]!=current["token_hash"])}

    @app.post("/api/patients/{patient_id}/reports")
    async def report(patient_id: str,request: Request):
        data=await body(request,ReportInput);now=settings.clock()
        try:event_at=instant(data.event_at)
        except ValueError:raise APIError(422,"timezone_required","Report event requires a valid explicit UTC offset")
        if event_at>now:raise APIError(422,"future_observation","Report event cannot be in the future")
        with store.transaction(write=True) as db:
            current=session(db,request,mutation=True);own(db,patient_id,current["account_id"])
            key=request.headers.get("idempotency-key","")
            if not key:raise APIError(422,"idempotency_required","Supply the original report key")
            run_id="report:"+current["account_id"]+":"+patient_id;payload_hash=digest(canonical(data.model_dump()))
            prior=db.execute("SELECT * FROM ingestion_receipts WHERE run_id=? AND transport_key=?",(run_id,key)).fetchone()
            if prior:
                if prior["payload_sha256"]!=payload_hash:raise APIError(409,"idempotency_conflict","Report key content changed")
                return {"status":prior["status"],"detail":prior["detail"]}
            record=record_header("report-"+uuid.uuid4().hex,patient_id,event_at)
            record.update(kind="daily_report",recorded_at=timestamp(now),available_at=timestamp(now),sleep_quality=data.sleep_quality,function=data.function,
                          adverse_symptoms=[data.note] if data.note else [],diary_sleep_minutes=data.diary_sleep_minutes,goals=[],burden=None,missingness="observed")
            record["source"]["adapter"]="patient_report"
            raw=canonical({k:v for k,v in record.items() if k!="source"}).encode();record["source"]["raw_sha256"]=digest(raw)
            try:append_event(db,parse_observed(canonical(record).encode()),raw,received_at=now)
            except ValueError as error:
                db.execute("INSERT INTO ingestion_receipts VALUES(?,?,?,?,?)",(run_id,key,payload_hash,"rejected",str(error)))
                return JSONResponse({"status":"rejected","detail":str(error)},status_code=422)
            apply_current_state(db,patient_id,settings.clock())
            db.execute("INSERT INTO ingestion_receipts VALUES(?,?,?,?,?)",(run_id,key,payload_hash,"accepted",record["record_id"]))
            return {"status":"accepted","record_id":record["record_id"]}

    @app.post("/api/patients/{patient_id}/randomize")
    def unavailable(patient_id: str,request: Request):
        with store.transaction(write=True) as db:
            current=session(db,request,mutation=True);own(db,patient_id,current["account_id"])
            raise APIError(409,"engine_unavailable","No randomization or statistical engine is implemented")

    if settings.web_root:
        app.mount("/assets",StaticFiles(directory=settings.web_root/"assets"),name="assets")

        @app.get("/{route:path}")
        def shell(route: str):
            if (route and not route.startswith("patients/")) or ".." in route:
                raise APIError(404,"not_found","Resource not found")
            return FileResponse(settings.web_root/"index.html")

    return app
