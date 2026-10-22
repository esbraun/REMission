import React, { useEffect, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { ContextGate } from './context.mjs';
import type { Bundle, Draft, Panel, Session, Workspace } from './types';
import './style.css';
import { LiveHoldPanel } from './LiveHoldPanel';
import { PanelGenerator, SimulationPanel } from './SimulationPanel';
import { AnalysisPanel } from './AnalysisPanel';

type Route = { patient: string; view: string; bundle: string };
class RequestFailure extends Error { constructor(public status: number, message: string) { super(message); } }
function routeOf(path: string): Route {
  const parts = path.split('/').filter(Boolean);
  return { patient: parts[0] === 'patients' ? decodeURIComponent(parts[1] ?? '') : '', view: parts[2] ?? 'overview', bundle: parts[3] ?? '' };
}
function readable(value: string) { return value.replaceAll('_', ' '); }
function date(value: string) { return new Date(value).toLocaleString(undefined, { year: 'numeric', month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit', timeZoneName: 'short' }); }
function NavLink({ href, navigate, children, current }: { href: string; navigate: (path: string) => void; children: React.ReactNode; current?: boolean }) {
  return <a className="link" href={href} aria-current={current ? 'page' : undefined} onClick={event => { if (event.button === 0 && !event.metaKey && !event.ctrlKey && !event.shiftKey && !event.altKey) { event.preventDefault(); navigate(href); } }}>{children}</a>;
}

function StateBanner({ workspace, mode }: { workspace: Workspace; mode: string }) {
  const flow = workspace.snapshot.workflow;
  return <section className="identity" aria-label="Patient context">
    <div><p className="eyebrow">{workspace.patient_id} · {mode === 'historical' ? 'Historical · read only' : 'Current workspace'}</p><h1>{workspace.name}</h1><p>{workspace.stage}: {workspace.stage_label}</p></div>
    <dl><div><dt>Clinical</dt><dd>{readable(flow.clinical)}</dd></div><div><dt>Learning</dt><dd>{readable(flow.learning)}</dd></div><div><dt>Data readiness</dt><dd>{flow.data_readiness}</dd></div><div><dt>Observation cutoff</dt><dd>{date(workspace.snapshot.cutoff)}</dd></div></dl>
    {flow.hold_reasons.length > 0 ? <div className="warning" role="status"><strong>Clinical hold</strong><p>{flow.hold_reasons.join('; ')}</p></div> : null}
  </section>;
}

function ObservationTable({ workspace }: { workspace: Workspace }) {
  const records = workspace.projection.records.filter(record => ['daily_report', 'isi', 'oura_like'].includes(record.kind));
  return <section><h2>Available observations</h2><p>Observed records available before the selected cutoff. Missing reports are not zero values. Oura-like measures are estimates, separate from patient reports.</p>
    {records.length ? <div className="table-wrap"><table><caption>Source observations and availability</caption><thead><tr><th scope="col">Record</th><th scope="col">Type</th><th scope="col">Observed</th><th scope="col">Available</th><th scope="col">Value</th></tr></thead><tbody>{records.map(r => <tr key={r.record_id}><th scope="row">{r.record_id}</th><td>{readable(r.kind)}</td><td>{date(r.event_at)}</td><td>{date(r.available_at)}</td><td>{r.kind === 'daily_report' ? `Quality ${r.sleep_quality ?? 'missing'}/10; function ${r.function ?? 'missing'}/10; ${r.missingness}` : r.kind === 'isi' ? `ISI ${r.items?.reduce((a, b) => a + b, 0)}/28; ${r.recall_days}-day recall; ${r.instrument_version}` : r.kind === 'oura_like' ? `${r.estimated_sleep_minutes ?? 'missing'} minutes; ${r.device_version}` : 'Inspect source event'}</td></tr>)}</tbody></table></div> : <div className="empty">No observed records are available at this cutoff.</div>}
  </section>;
}

type Report = { event_at: string; sleep_quality: number; function: number; diary_sleep_minutes: number; note: string };
function ReportForm({ save }: { save: (report: Report, key: string) => Promise<void> }) {
  const [pending, setPending] = useState(false);
  const [failure, setFailure] = useState('');
  const submitted = useRef<{ payload: Report; key: string } | null>(null);
  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault(); const form = event.currentTarget; const values = new FormData(form);
    if (!submitted.current) submitted.current = { key: crypto.randomUUID(), payload: { event_at: new Date(String(values.get('event_at'))).toISOString(), sleep_quality: Number(values.get('quality')), function: Number(values.get('function')), diary_sleep_minutes: Number(values.get('minutes')), note: String(values.get('note')) } };
    setPending(true); setFailure('');
    try { await save(submitted.current.payload, submitted.current.key); submitted.current = null; form.reset(); }
    catch (error) { setFailure(`${String(error)}. Retry sends the original report and key.`); }
    finally { setPending(false); }
  }
  return <section><h2>Record a synthetic patient report</h2><p>Record observed values. This does not estimate treatment effects or provide acute monitoring. The service retains actual receipt time.</p>{failure ? <p role="alert" className="error">{failure}</p> : null}<form onSubmit={event => void submit(event)}><fieldset disabled={pending || Boolean(submitted.current)}><label htmlFor="report-time">Observed date and time · your local timezone</label><input id="report-time" name="event_at" type="datetime-local" required autoComplete="off"/><label htmlFor="quality">Reported sleep quality · 0 to 10</label><input id="quality" name="quality" type="number" inputMode="decimal" min="0" max="10" step="0.1" required autoComplete="off"/><label htmlFor="function">Reported function · 0 to 10</label><input id="function" name="function" type="number" inputMode="decimal" min="0" max="10" step="0.1" required autoComplete="off"/><label htmlFor="minutes">Diary sleep duration · minutes</label><input id="minutes" name="minutes" type="number" inputMode="decimal" min="0" max="1440" required autoComplete="off"/><label htmlFor="report-note">Adverse symptom note · optional</label><input id="report-note" name="note" maxLength={256} autoComplete="off"/></fieldset><button disabled={pending}>{pending ? 'Recording report…' : submitted.current ? 'Retry original report' : 'Save observed report'}</button></form></section>;
}

function HistoricalView({ bundle, later, requestLater, returnCurrent }: { bundle: Bundle; later: string | null; requestLater: () => void; returnCurrent: () => void }) {
  const saved = bundle.display;
  return <><StateBanner workspace={saved.workspace} mode="historical"/><section className="history-notice"><h2>Saved decision · as known then</h2><p>This exact display is persisted. New observations and model references do not replace its inputs.</p><p><strong>Approved ordinary choice:</strong> {readable(saved.approval.option)}</p><p><strong>Rationale:</strong> {saved.rationale}</p><p><strong>Follow-up:</strong> {date(saved.follow_up.due_at)} · {saved.follow_up.owner_id}</p><details><summary>Saved display integrity and basis</summary><p className="hash">SHA256 {bundle.display_sha256}</p><p>Model: {saved.workspace.snapshot.model.id} {saved.workspace.snapshot.model.version}. Statistical engines were unavailable.</p></details><button onClick={returnCurrent}>Return to current</button></section><ObservationTable workspace={saved.workspace}/><section><h2>Later outcomes</h2><p>Separate retrospective information. These observations did not inform the saved decision.</p><button className="secondary" onClick={requestLater}>Request later outcomes</button>{later ? <pre className="source-json">{later}</pre> : null}</section></>;
}

function App() {
  const gate = useRef(new ContextGate());
  const [session, setSession] = useState<Session | null>(null);
  const [booting, setBooting] = useState(true);
  const [path, setPath] = useState(location.pathname);
  const [panel, setPanel] = useState<Panel | null>(null);
  const [panelGroup, setPanelGroup] = useState('latest');
  const [workspace, setWorkspace] = useState<Workspace | null>(null);
  const [bundle, setBundle] = useState<Bundle | null>(null);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [loading, setLoading] = useState(false);
  const [draft, setDraft] = useState<Draft | null>(null);
  const [dirty, setDirty] = useState(false);
  const [reviewing, setReviewing] = useState(false);
  const [savedDraft, setSavedDraft] = useState<{ draft: Draft | null; base_valid: boolean; auth_generation_changed: boolean } | null>(null);
  const [pendingNavigation, setPendingNavigation] = useState<string | null>(null);
  const [pendingApproval, setPendingApproval] = useState<string | null>(null);
  const [pendingAdvance, setPendingAdvance] = useState(false);
  const [later, setLater] = useState<string | null>(null);
  const [bootstrapVersion, setBootstrapVersion] = useState(0);
  const [refreshVersion, setRefreshVersion] = useState(0);
  const route = routeOf(path);

  function clearIdentity() {
    gate.current.invalidate(); setLoading(false); setPendingAdvance(false); setPanel(null); setPanelGroup('latest'); setWorkspace(null); setBundle(null); setDraft(null); setSavedDraft(null); setDirty(false); setReviewing(false); setPendingApproval(null); setLater(null); setPendingNavigation(null);
  }
  async function request<T>(url: string, options: RequestInit = {}, auth = session): Promise<T> {
    const responseContext = gate.current.capture();
    const response = await fetch(url, { ...options, credentials: 'same-origin', headers: { 'Content-Type': 'application/json', ...(options.method && options.method !== 'GET' && auth ? { 'X-CSRF-Token': auth.csrf } : {}), ...options.headers } });
    if (response.status === 401 && url !== '/api/login') { if (gate.current.accepts(responseContext)) { clearIdentity(); setSession(null); } throw new Error('Session ended. Unsaved local input was cleared; sign in again.'); }
    const result: unknown = await response.json();
    if (!response.ok) {
      const detail = typeof result === 'object' && result !== null && 'detail' in result ? String(result.detail) : 'Request failed';
      throw new RequestFailure(response.status, detail);
    }
    return result as T;
  }
  useEffect(() => {
    const ticket = gate.current.capture();
    let active = true;
    void request<Session>('/api/session')
      .then(value => { if (active && gate.current.accepts(ticket)) setSession(value); })
      .catch(e => { if (active && gate.current.accepts(ticket)) setError(String(e)); })
      .finally(() => { if (active) setBooting(false); });
    return () => { active = false; };
  }, [bootstrapVersion]);
  useEffect(() => {
    function pop() { clearIdentity(); setPath(location.pathname); }
    function warn(event: BeforeUnloadEvent) { if (dirty) { event.preventDefault(); event.returnValue = ''; } }
    window.addEventListener('popstate', pop); window.addEventListener('beforeunload', warn);
    return () => { window.removeEventListener('popstate', pop); window.removeEventListener('beforeunload', warn); };
  }, [dirty]);
  useEffect(() => {
    if (!session?.principal) return;
    const context = `${session.auth_generation}:${path}`;
    const ticket = gate.current.activate(context);
    setWorkspace(null); setBundle(null); setPendingAdvance(false); setSavedDraft(null); setDraft(null); setDirty(false); setReviewing(false); setLoading(true); setLater(null);
    async function load() {
      try {
        const ownPanel = await request<Panel>('/api/patients');
        if (!gate.current.accepts(ticket)) return; setPanel(ownPanel);
        if (route.patient && route.view === 'history' && route.bundle) {
          const value = await request<Bundle>(`/api/patients/${encodeURIComponent(route.patient)}/history/${encodeURIComponent(route.bundle)}`);
          if (gate.current.accepts(ticket) && value.auth_generation === session?.auth_generation) setBundle(value);
        } else if (route.patient) {
          const [value, serverDraft] = await Promise.all([request<Workspace>(`/api/patients/${encodeURIComponent(route.patient)}`), request<{ draft: Draft | null; base_valid: boolean; auth_generation_changed: boolean }>(`/api/patients/${encodeURIComponent(route.patient)}/draft`)]);
          if (!gate.current.accepts(ticket) || value.auth_generation !== session?.auth_generation) return;
          setWorkspace(value); setSavedDraft(serverDraft); setDraft({ decision_id: value.snapshot.record_id, expected_version: value.snapshot.patient_version, mode: 'current', option: null, rationale: '', follow_up_at: value.simulation ? new Date(new Date(value.snapshot.cutoff).getTime() + 14 * 86400000).toISOString() : '' });
        }
      } catch (e) { if (gate.current.accepts(ticket)) setError(String(e)); }
      finally { if (gate.current.accepts(ticket)) setLoading(false); }
    }
    void load();
    return () => { if (gate.current.accepts(ticket)) gate.current.activate('transition'); };
  }, [session?.auth_generation, path, refreshVersion]);

  function navigate(next: string, discard = false) {
    if (dirty && !discard) { setPendingNavigation(next); return; }
    gate.current.activate(`${session?.auth_generation}:${next}`); setWorkspace(null); setBundle(null); setDraft(null); setDirty(false); setError(''); setNotice(''); setReviewing(false); setPendingApproval(null);
    history.pushState({}, '', next); setPath(next);
  }
  async function signIn(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault(); const form = new FormData(event.currentTarget); clearIdentity(); setError(''); setNotice(''); setLoading(true);
    try {
      const bootstrap = await request<Session>('/api/session');
      const value = await request<Session>('/api/login', { method: 'POST', body: JSON.stringify({ username: form.get('username'), password: form.get('password') }) }, bootstrap);
      gate.current.invalidate(); setSession(value);
    } catch (e) { setError(String(e)); }
    finally { setLoading(false); }
  }
  async function signOut() {
    const prior = session; clearIdentity(); setSession(null); setError('');
    await gate.current.notifyAfter(() => request('/api/logout', { method: 'POST' }, prior),
      () => setNotice('Signed out. Patient content and unsaved input were cleared.'),
      e => setError(String(e)));
  }
  async function saveDraft(leave = false) {
    if (!draft || !workspace) return;
    const ticket = gate.current.capture();
    try { await request(`/api/patients/${workspace.patient_id}/draft`, { method: 'PUT', body: JSON.stringify(draft) }); if (!gate.current.accepts(ticket)) return; setDirty(false); setNotice('Draft saved. No approval was created.'); if (leave && pendingNavigation) { const next = pendingNavigation; setPendingNavigation(null); navigate(next, true); } }
    catch (e) { if (gate.current.accepts(ticket)) setError(String(e)); }
  }
  function edit(values: Partial<Draft>) { if (draft) { setDraft({ ...draft, ...values }); setDirty(true); setReviewing(false); } }
  function refresh() {
    gate.current.invalidate(); setWorkspace(null);
    if (!session?.principal) { setBooting(true); setBootstrapVersion(value => value + 1); }
    else setRefreshVersion(value => value + 1);
  }
  async function finishApproval(result: { bundle_id: string }, ticket: ReturnType<ContextGate['capture']>) {
    if (!gate.current.accepts(ticket)) return;
    setDirty(false); setPendingApproval(null); setReviewing(false); setNotice('Ordinary synthetic choice and follow-up persisted.'); navigate(`/patients/${route.patient}/history/${result.bundle_id}`, true);
  }
  async function approve() {
    if (!draft?.option || !workspace || pendingApproval) return;
    const ticket = gate.current.capture(); const key = crypto.randomUUID(); setPendingApproval(key); setError('');
    const snapshot = workspace.snapshot;
    const payload = { decision_id: draft.decision_id, mode: 'current', option: draft.option, rationale: draft.rationale, follow_up_at: draft.follow_up_at, purpose: 'ordinary_treatment', expected_patient_version: snapshot.patient_version, expected_state_version: snapshot.state_version, expected_consent_version: snapshot.consent_version, expected_eligibility_version: snapshot.eligibility_version };
    try { const result = await request<{ bundle_id: string }>(`/api/patients/${workspace.patient_id}/approve`, { method: 'POST', body: JSON.stringify(payload), headers: { 'Idempotency-Key': key } }); await finishApproval(result, ticket); }
    catch (e) {
      if (!gate.current.accepts(ticket)) return;
      if (e instanceof RequestFailure && e.status >= 400 && e.status < 500) { setPendingApproval(null); setError(`${e.message}. Refresh current information and review changed state before approving.`); return; }
      setError(`${String(e)}. Checking approval status using the original key.`);
      try { await finishApproval(await request<{ bundle_id: string }>(`/api/patients/${workspace.patient_id}/receipts/${key}`), ticket); }
      catch { if (gate.current.accepts(ticket)) setNotice('Approval status is unconfirmed. Check status before submitting another choice.'); }
    }
  }
  async function checkApproval() { if (!pendingApproval) return; const ticket = gate.current.capture(); try { await finishApproval(await request<{ bundle_id: string }>(`/api/patients/${route.patient}/receipts/${pendingApproval}`), ticket); } catch (e) { if (gate.current.accepts(ticket)) setError(String(e)); } }
  async function recordState(stage: string) {
    if (!workspace) return; const reason = stage === 'ASSIGN-09' ? 'Clinician requests synthetic clinical review' : 'Clinician reviewed prerequisites for ordinary synthetic assessment'; const ticket = gate.current.capture();
    try { await request(`/api/patients/${workspace.patient_id}/state`, { method: 'POST', body: JSON.stringify({ expected_version: workspace.snapshot.patient_version, stage, reason }) }); if (gate.current.accepts(ticket)) { setDirty(false); refresh(); } } catch (e) { if (gate.current.accepts(ticket)) setError(String(e)); }
  }
  async function requestLater() { if (!bundle) return; const ticket = gate.current.capture(); try { const value = await request(`/api/patients/${route.patient}/history/${route.bundle}/later-outcomes`); if (gate.current.accepts(ticket)) setLater(JSON.stringify(value, null, 2)); } catch (e) { if (gate.current.accepts(ticket)) setError(String(e)); } }
  async function saveReport(report: Report, key: string) { const ticket = gate.current.capture(); await request(`/api/patients/${route.patient}/reports`, { method: 'POST', body: JSON.stringify(report), headers: { 'Idempotency-Key': key } }); if (gate.current.accepts(ticket)) { setNotice('Observed report persisted with actual receipt time.'); refresh(); } }
  async function generatePanel(seed: number, count: number, key: string) {
    const ticket = gate.current.capture();
    await request('/api/panels/generate', { method: 'POST', body: JSON.stringify({ seed, count }), headers: { 'Idempotency-Key': key } });
    if (gate.current.accepts(ticket)) { setPanelGroup('latest'); setNotice(`Generated and loaded ${count} fictional patients with seed ${seed}.`); refresh(); }
  }
  async function advanceSimulation(mode: 'day' | 'visit', key: string) {
    if (!workspace || dirty) return;
    const ticket = gate.current.capture();
    setPendingAdvance(true);
    const result = await request<{ day: number }>(`/api/patients/${workspace.patient_id}/advance`, { method: 'POST', body: JSON.stringify({ expected_version: workspace.snapshot.patient_version, mode }), headers: { 'Idempotency-Key': key } });
    if (gate.current.accepts(ticket)) { setPendingAdvance(false); setNotice(`Simulation advanced to day ${result.day}. New observations and delivery records are saved.`); refresh(); }
  }
  const visibleWorkspace = workspace?.patient_id === route.patient && !(route.view === 'history' && route.bundle) && workspace.auth_generation === session?.auth_generation ? workspace : null;
  const visibleBundle = bundle?.patient_id === route.patient && bundle.snapshot_id === route.bundle && route.view === 'history' && bundle.auth_generation === session?.auth_generation ? bundle : null;
  const groups = new Map(panel?.patients.flatMap(patient => patient.state.simulation ? [[patient.state.simulation.panel_id, patient.state.simulation.seed] as const] : []));
  const selectedGroup = panelGroup === 'latest' ? panel?.generated?.panel_id ?? 'fixtures' : panelGroup;
  const panelPatients = panel?.patients.filter(patient => selectedGroup === 'all' || (selectedGroup === 'fixtures' ? !patient.state.simulation : patient.state.simulation?.panel_id === selectedGroup)) ?? [];

  return <><a className="skip" href="#main">Skip to main content</a><header><div className="brand">REMission <span>Synthetic care workspace</span></div>{session?.principal ? <div className="account"><span>{session.principal.name}</span><button className="header-button" onClick={() => void signOut()}>Sign out</button></div> : null}</header><div className="demo-label">Synthetic demonstration · fictional medicines MED_A / MED_B · no acute clinical monitoring</div>
    <main id="main" tabIndex={-1}>{error ? <div className="error" role="alert"><strong>Action needs attention</strong><p>{error}</p><button className="secondary" onClick={() => { setError(''); refresh(); }}>Refresh current information</button></div> : null}{notice ? <p className="notice" role="status">{notice}</p> : null}
    {booting ? <p role="status">Checking session…</p> : !session?.principal ? <section className="signin"><p className="eyebrow">Research demonstration</p><h1>Sign in to your synthetic panel</h1><p>Ordinary clinician choices and immutable history. Observed-only V0 analysis is available for generated patients after day14. Real clinical systems are unavailable.</p><form onSubmit={event => void signIn(event)}><label htmlFor="username">Username</label><input id="username" name="username" autoComplete="username" required/><label htmlFor="password">Password</label><input id="password" name="password" type="password" autoComplete="current-password" required/><button disabled={loading}>{loading ? 'Signing in…' : 'Sign in'}</button></form></section> : <>
    <nav className="topnav" aria-label="Workspace"><NavLink href="/" navigate={navigate}>My panel</NavLink><span>{panel ? `${panel.denominator} owned synthetic patients` : ''}</span></nav>
    {!route.patient ? <PanelGenerator key={session.auth_generation} generate={generatePanel}/> : null}
    {!route.patient && panel?.generated ? <p>Most recently generated: seed {panel.generated.seed} · {panel.generated.count} patients. Select an earlier group below to return to saved patients.</p> : null}
    {pendingNavigation ? <section className="warning" aria-label="Unsaved draft"><h2>Unsaved draft</h2><p>Save, discard or cancel before leaving this patient and decision.</p><div className="actions"><button onClick={() => void saveDraft(true)}>Save draft and leave</button><button className="secondary" onClick={() => { const next = pendingNavigation; setPendingNavigation(null); navigate(next, true); }}>Discard and leave</button><button className="link" onClick={() => setPendingNavigation(null)}>Cancel</button></div></section> : null}
    {loading ? <p role="status">Loading authorized workspace…</p> : null}
    {!route.patient && panel ? <><p className="eyebrow">Your clinical workspace</p><h1>My panel</h1><p>Choose a synthetic patient. State and permissions come from the service; opening a workspace never assigns a treatment.</p>
      <label htmlFor="panel-group">Loaded patient group</label><select id="panel-group" name="panel_group" value={panelGroup} onChange={event => setPanelGroup(event.target.value)}><option value="latest">{panel.generated ? `Latest generated panel · seed ${panel.generated.seed}` : 'Foundation fixtures'}</option>{[...groups].filter(([id]) => id !== panel.generated?.panel_id).map(([id, seed]) => <option key={id} value={id}>Saved panel · seed {seed} · {id.slice(-8)}</option>)}{panel.generated ? <option value="fixtures">Foundation fixtures</option> : null}<option value="all">All owned patients</option></select>
      <p role="status">Showing {panelPatients.length} of {panel.denominator} owned patients.</p>
      <div className="patient-grid">{panelPatients.map(patient => <article key={patient.id}><p className="eyebrow">{patient.id}</p><h2><NavLink href={`/patients/${patient.id}/overview`} navigate={navigate}>{patient.name}</NavLink></h2><p>{patient.state.stage} · {readable(patient.state.workflow.clinical)}</p><p className="muted">Learning: {readable(patient.state.workflow.learning)}{patient.state.simulation ? ` · day ${patient.state.simulation.day}` : ''}</p><span className={patient.state.workflow.clinical === 'clinical_hold' ? 'badge hold' : 'badge'}>{patient.state.workflow.data_readiness}</span></article>)}</div></> : null}
    {visibleBundle ? <HistoricalView bundle={visibleBundle} later={later} requestLater={() => void requestLater()} returnCurrent={() => navigate(`/patients/${route.patient}/overview`)}/> : null}
    {visibleWorkspace ? <><StateBanner workspace={visibleWorkspace} mode="current"/><nav className="tabs" aria-label="Patient views">{['overview', 'current', 'monitoring', 'analysis', 'history'].map(view => <NavLink key={view} href={`/patients/${route.patient}/${view}`} navigate={navigate} current={route.view === view}>{view === 'current' ? 'Current decision' : view[0].toUpperCase() + view.slice(1)}</NavLink>)}</nav>
    {route.view === 'current' ? <LiveHoldPanel key={`${visibleWorkspace.patient_id}:${session?.auth_generation}:${visibleWorkspace.snapshot.record_id}`} workspace={visibleWorkspace} request={request} refresh={refresh} changed={setDirty}/> : null}
    {route.view !== 'history' && visibleWorkspace.simulation ? <SimulationPanel key={`${visibleWorkspace.patient_id}:${session.auth_generation}:${visibleWorkspace.snapshot.record_id}`} workspace={visibleWorkspace} advance={advanceSimulation} dirty={dirty}/> : null}
    {route.view === 'history' ? null : route.view === 'analysis' ? <AnalysisPanel key={visibleWorkspace.patient_id + ':' + session.auth_generation} workspace={visibleWorkspace} request={request}/> : route.view === 'monitoring' ? <><ObservationTable workspace={visibleWorkspace}/>{!visibleWorkspace.simulation ? <ReportForm key={visibleWorkspace.patient_id} save={saveReport}/> : null}</> : route.view === 'overview' ? <><section><h2>Current ordinary plan</h2>{visibleWorkspace.plan ? <><p><strong>{readable(visibleWorkspace.plan.option)}</strong></p><p>{visibleWorkspace.plan.rationale}</p>{visibleWorkspace.plan.effective_at ? <p>Decision: {date(visibleWorkspace.plan.decided_at!)}. Effective: {date(visibleWorkspace.plan.effective_at)}. Actual nightly delivery and adherence are recorded separately.</p> : null}</> : <p>No ordinary treatment choice has been approved.</p>}<h3>Follow-up tasks</h3>{visibleWorkspace.tasks.length ? <ul>{visibleWorkspace.tasks.map(task => <li key={task.id}>{date(task.due_at)} · {task.owner_id} · pending synthetic follow-up</li>)}</ul> : <p>No saved follow-up tasks.</p>}<button onClick={() => navigate(`/patients/${route.patient}/current`)}>Open current decision</button></section><ObservationTable workspace={visibleWorkspace}/></> : <>
      {pendingAdvance ? <p role="status">Resolve the original advancement before editing another decision. You can retry above or reload the saved current state.</p> : null}
      <section><p className="eyebrow">1 · Assess</p><h2>Readiness and clinical review</h2><p>Clinical: {readable(visibleWorkspace.snapshot.workflow.clinical)}. Learning: {readable(visibleWorkspace.snapshot.workflow.learning)}. Data: {visibleWorkspace.snapshot.workflow.data_readiness}.</p><p>Support is {visibleWorkspace.snapshot.workflow.support_mode}; policy {visibleWorkspace.snapshot.workflow.support_policy.id} version {visibleWorkspace.snapshot.workflow.support_policy.version}.</p><div className="actions"><button className="secondary" onClick={() => void recordState('ASSIGN-09')}>Request clinical hold</button>{!visibleWorkspace.permissions.approve_ordinary ? <button className="secondary" onClick={() => void recordState('ASSIGN-02')}>Record prerequisite review</button> : null}</div></section>
      <section><p className="eyebrow">2 · Compare</p><h2>Eligible ordinary options</h2><div className="unavailable"><strong>No statistical comparison is available</strong><p>{visibleWorkspace.estimates.reason}. No superiority ranking or treatment recommendation is supplied.</p></div><details><summary>Inspect basis and engine status</summary><p>{visibleWorkspace.snapshot.outcome}; horizon {visibleWorkspace.snapshot.horizon_days} days. No posterior or interval is available.</p><ul>{Object.entries(visibleWorkspace.engines).map(([name, status]) => <li key={name}>{name}: {status}</li>)}</ul><p>Randomization is unavailable. N-of-1 consent, washout/carryover, escalation and support-policy evidence require their later accepted engines.</p></details></section>
      <fieldset disabled={pendingAdvance} aria-label="Current decision controls">
      <section><p className="eyebrow">3 · Decide and follow up</p><h2>Explicit ordinary synthetic choice</h2>{savedDraft?.draft && savedDraft.base_valid ? <div className="notice"><p>A server draft is available{savedDraft.auth_generation_changed ? ' from an earlier authentication session' : ''}. Review it explicitly before use.</p><button className="secondary" onClick={() => { setDraft(savedDraft.draft); setDirty(true); setSavedDraft(null); }}>Resume saved draft</button></div> : null}
      {!visibleWorkspace.permissions.approve_ordinary ? <p className="warning">No ordinary assignment is due or permitted in this state. Review prerequisites or the relevant future protocol engine.</p> : draft ? <form onSubmit={event => { event.preventDefault(); setReviewing(true); }}><fieldset disabled={Boolean(pendingApproval)}><legend>Choose an eligible option · none is preselected</legend>{visibleWorkspace.options.map(option => <label className="radio" key={option.action}><input type="radio" name="option" checked={draft.option === option.action} disabled={option.status !== 'eligible'} onChange={() => edit({ option: option.action })} required/>{readable(option.action)} {option.status !== 'eligible' ? `· ${option.status}: ${option.reasons.join('; ')}` : ''}</label>)}<label htmlFor="rationale">Preference and rationale</label><textarea id="rationale" value={draft.rationale} onChange={event => edit({ rationale: event.target.value })} required maxLength={1000}/><label htmlFor="follow-up">Follow-up date and time</label><input id="follow-up" type="datetime-local" value={draft.follow_up_at ? new Date(new Date(draft.follow_up_at).getTime() - new Date(draft.follow_up_at).getTimezoneOffset() * 60000).toISOString().slice(0, 16) : ''} onChange={event => edit({ follow_up_at: event.target.value ? new Date(event.target.value).toISOString() : '' })} required/><div className="actions"><button type="submit">Review ordinary choice</button><button type="button" className="secondary" onClick={() => void saveDraft()}>Save draft</button></div></fieldset></form> : null}
      {reviewing && draft?.option ? <div className="confirmation" aria-label="Approval summary"><h3>Confirm ordinary choice</h3><p>{readable(draft.option)} for {visibleWorkspace.name} ({visibleWorkspace.patient_id}).</p><p>{draft.rationale}</p><p>Follow-up: {date(draft.follow_up_at)}. This is ordinary synthetic care, not a randomized assignment.</p><button disabled={Boolean(pendingApproval)} onClick={() => void approve()}>{pendingApproval ? 'Checking approval status…' : 'Confirm and save choice'}</button></div> : null}{pendingApproval ? <button className="secondary" onClick={() => void checkApproval()}>Check approval status</button> : null}</section>
    </fieldset></>}
    {route.view === 'history' || visibleWorkspace.history.length > 0 ? <section><h2>Saved decisions</h2>{visibleWorkspace.history.length ? <ul>{visibleWorkspace.history.map(item => <li key={item.id}><NavLink href={`/patients/${route.patient}/history/${item.id}`} navigate={navigate}>Ordinary choice · {date(item.approved_at)}</NavLink></li>)}</ul> : <p>No saved decisions for this patient.</p>}</section> : null}
    </> : null}
    </>}
    <footer>Engineering foundation only. Human-factors, clinical review and clinical validation remain unexecuted.</footer></main></>;
}

createRoot(document.getElementById('root')!).render(<App/>);
