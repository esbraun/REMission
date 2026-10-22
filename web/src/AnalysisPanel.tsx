import { useEffect, useRef, useState } from 'react';
import type { AnalysisAttempt, CohortPreview, CohortSelection, Panel, StudyBundle, Workspace } from './types';
import { analysisMessage, definitiveRejection } from './analysis-state.mjs';

type Request = <T>(url: string, options?: RequestInit) => Promise<T>;
const date = (value: string) => new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'long' }).format(new Date(value));
const number = (value: number) => new Intl.NumberFormat(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(value);

function AnalysisProvenance({ attempt }: { attempt: AnalysisAttempt }) {
  return <><p><strong>Saved analysis: {attempt.serving.status}.</strong> Data through {date(attempt.serving.data_through)}. {attempt.serving.published_at ? `Published ${date(attempt.serving.published_at)}.` : 'No result published yet.'} Artifact generation time is not separately recorded.</p>
    {attempt.serving.reason ? <p className="warning">{attempt.serving.reason.replaceAll('_', ' ')}. Current model advice is unavailable for an incompatible history or unaccepted summary.</p> : null}
    <details><summary>Saved result provenance</summary><p>Queued {date(attempt.created_at)}. {attempt.started_at ? `Worker started ${date(attempt.started_at)}.` : 'Worker has not started.'}</p><p className="hash">Current patient version {attempt.serving.current_patient_version ?? 'See cohort member identities'}<br/>Current H* SHA256 {attempt.serving.current_history_sha256 ?? 'Unavailable or recorded per cohort member'}<br/>Source {attempt.serving.summary_source}<br/>Policy {attempt.serving.policy}</p></details>
  </>;
}

export function SourceDetails({ bundle }: { bundle: StudyBundle }) {
  return <details><summary>Source studies and population assumptions · {bundle.bundle_id}</summary>
    <p>These are fictional randomized studies. Each starts untreated, retains its assigned plan at source days 14/28 and reports source day 42 ISI recalling nights 29–42, with fixed no-prompt support. Their endpoint clock is separate from this patient's forecast.</p>
    <p>The fitted bridge assumes shared source/target population, adherence, process and measurement laws and independent normal baseline/treatment hierarchies. Source randomization identifies the source average contrast; transport to this patient still depends on these assumptions. The synthetic generator can differ from the fitted hierarchy.</p>
    <div className="table-wrap"><table><caption>Observed escalation minus continuation summaries, ISI points</caption><thead><tr><th>Study / underlying dataset</th><th>Participants C / E</th><th>Observed difference</th><th>Sampling SE</th><th>Available at</th></tr></thead><tbody>{bundle.studies.map(study => <tr key={study.study_id}><td><span className="hash">{study.study_id}<br/>{study.dataset_id}</span></td><td>{study.n_continue} / {study.n_escalate}</td><td>{number(study.d)}</td><td>{number(study.se)}</td><td>{date(study.available_at)}</td></tr>)}</tbody></table></div>
    <p>Two summaries constrain one marginal contrast. They do not separately identify both treatment effects, adherence, heterogeneity or an individual response. Robust mixture responsibilities are not effective patient counts; absent local outcomes cannot establish source/target conflict.</p><p className="hash">Source set SHA256 {bundle.source_set_sha256}</p>
  </details>;
}

export function AnalysisResultView({ attempt }: { attempt: AnalysisAttempt }) {
  if (attempt.kind === 'cohort_visit_analysis') return <article className="analysis-attempt" aria-labelledby={`attempt-${attempt.id}`}>
    <h3 id={`attempt-${attempt.id}`}>{attempt.configuration.id} · {attempt.status} · joint twelve-patient analysis</h3>
    <AnalysisProvenance attempt={attempt}/>
    <p className="hash">Attempt {attempt.id}<br/>Cohort {attempt.manifest.cohort_id}<br/>Manifest SHA256 {attempt.manifest_sha256}</p>
    <p>One shared posterior, observation cutoff {date(attempt.cutoff)}. Each patient retains a separate conditional expected contrast; no average replaces these effects.</p>
    {attempt.sources ? <SourceDetails bundle={attempt.sources}/> : <p>V0 uses the original prior and the twelve selected available histories, without external summaries.</p>}
    {attempt.stale ? <p className="warning">One or more current member versions or cutoffs differ from this frozen cohort. This is an earlier cohort result.</p> : null}
    {attempt.failure_reason ? <p className="error">{attempt.failure_reason}. No accepted effect interval is available.</p> : null}
    {attempt.result ? <><div className="table-wrap"><table><caption>Expected next 42-day ISI contrast, escalation minus continuation, by patient</caption><thead><tr><th>Patient</th><th>Status</th><th>Mean</th><th>95% posterior interval</th></tr></thead><tbody>{attempt.result.patients.map(patient => <tr key={patient.patient_id}><td className="hash">{patient.patient_id}</td><td>{patient.status}{patient.reason ? ` · ${patient.reason}` : ''}</td><td>{patient.effect ? number(patient.effect.mean) : 'No accepted estimate'}</td><td>{patient.effect ? `${number(patient.effect.lower)} to ${number(patient.effect.upper)}` : 'Unavailable'}</td></tr>)}</tbody></table></div><ul>{attempt.result.limitations.map(text => <li key={text}>{text}</li>)}</ul><details><summary>Actual joint and per-patient diagnostics</summary><pre className="source-json">{JSON.stringify(attempt.result.diagnostics, null, 2)}</pre></details></> : <p role="status">{analysisMessage(attempt.status)}</p>}
    <details><summary>Frozen twelve-member identity and current information status</summary><pre className="source-json">{JSON.stringify(attempt.member_information, null, 2)}</pre><pre className="source-json">{JSON.stringify(attempt.manifest, null, 2)}</pre><p className="hash">Input SHA256 {attempt.input_sha256}<br/>Cohort H* SHA256 {attempt.cohort_sha256}</p></details>
  </article>;
  const result = attempt.result;
  return <article className="analysis-attempt" aria-labelledby={`attempt-${attempt.id}`}>
    <h3 id={`attempt-${attempt.id}`}>{attempt.configuration.id} · {attempt.status}</h3>
    <AnalysisProvenance attempt={attempt}/>
    <p className="hash">Attempt {attempt.id}</p>
    <dl><div><dt>Observation cutoff</dt><dd>{date(attempt.cutoff)}</dd></div><div><dt>Stage</dt><dd>{attempt.stage}</dd></div><div><dt>Local cohort</dt><dd className="hash">{attempt.cohort.join(', ')} · one patient</dd></div></dl>
    {attempt.forecast_endpoint_day !== undefined ? <p>Local cutoff day {attempt.cutoff_day}: forecast the next 42 days through local day {attempt.forecast_endpoint_day}, recalling local nights {attempt.recall_first_night}–{attempt.recall_last_night}.</p> : null}
    {attempt.sources ? <SourceDetails bundle={attempt.sources}/> : <p>V0: original prior and this patient's available observations; no external sources.</p>}
    {attempt.stale ? <p className="warning"><strong>Dated analysis.</strong> Current history, lineage, policy or cutoff differs or cannot be verified. This result retains its saved forecast origin and endpoint. Refresh analysis to request a new background fit.</p> : null}
    {attempt.previous_attempt ? <p>Deliberate retry of {attempt.previous_attempt}.</p> : null}
    {attempt.failure_reason ? <p className="error">{attempt.failure_reason}. No accepted effect interval is available.</p> : null}
    {result?.effect ? <><p><strong>Expected 42-day ISI difference: {number(result.effect.mean)} points</strong> (escalation minus continuation).</p><p>95% posterior interval {number(result.effect.lower)} to {number(result.effect.upper)} points; posterior SD {number(result.effect.sd)}. Negative values predict lower ISI under escalation. The endpoint averages future nights 29–42, retaining each assigned plan.</p><p>This interval describes uncertainty in the conditional expected effect after integrating future adherence, process and measurement randomness. It is separate from a future outcome predictive interval.</p></> : null}
    {attempt.serving.predictive_endpoint ? <div className="table-wrap"><table><caption>Saved 95% future ISI predictive intervals, including future outcome randomness</caption><thead><tr><th>Retained plan</th><th>ISI points</th></tr></thead><tbody><tr><th scope="row">Continuation</th><td>{attempt.serving.predictive_endpoint.continue_interval.map(number).join(' to ')}</td></tr><tr><th scope="row">Escalation</th><td>{attempt.serving.predictive_endpoint.escalate_interval.map(number).join(' to ')}</td></tr></tbody></table><p>These intervals describe future outcomes, separately from uncertainty in the expected contrast above.</p></div> : null}
    {result ? <><ul>{result.limitations.map(text => <li key={text}>{text}</li>)}</ul><details><summary>Actual computation and diagnostics</summary><pre className="source-json">{JSON.stringify(result.diagnostics, null, 2)}</pre></details></> : <p role="status">{analysisMessage(attempt.status)}</p>}
    <details><summary>Frozen input and configuration identity</summary><p className="hash">H* SHA256 {attempt.history_sha256}</p><p className="hash">Input SHA256 {attempt.input_sha256}</p><p className="hash">Configuration SHA256 {attempt.configuration.sha256}</p><p>EST-VISIT:poc-hstar-v1 · quality/ISI, reporting indicators and typed treatment/delivery history only. Function and diary are excluded from fitting.</p></details>
  </article>;
}

export function AnalysisPanel({ workspace, request, refresh }: { workspace: Workspace; request: Request; refresh: () => void }) {
  const [attempts, setAttempts] = useState<AnalysisAttempt[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [failure, setFailure] = useState('');
  const [revision, setRevision] = useState(0);
  const [needsRefresh, setNeedsRefresh] = useState(false);
  const [mode, setMode] = useState<'v0' | 'borrow' | 'tau2'>('v0');
  const [bundles, setBundles] = useState<StudyBundle[]>([]);
  const [source, setSource] = useState('');
  const submitted = useRef<{ key: string; payload: { expected_version: number; previous_attempt: string | null; mode: string; source_bundle_id: string | null } } | null>(null);
  const generation = useRef(0);
  const currentRequest = useRef(request);
  currentRequest.current = request;
  const patient = workspace.patient_id;
  const cutoff = workspace.snapshot.cutoff;
  useEffect(() => {
    const epoch = ++generation.current;
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout> | undefined;
    async function load() {
      try {
        const [value, sources] = await Promise.all([
          currentRequest.current<{ attempts: AnalysisAttempt[] }>(`/api/patients/${encodeURIComponent(patient)}/analyses`, { signal: controller.signal }),
          currentRequest.current<{ bundles: StudyBundle[] }>(`/api/patients/${encodeURIComponent(patient)}/analysis-sources`, { signal: controller.signal })
        ]);
        if (generation.current !== epoch) return;
        setAttempts(value.attempts); setBundles(sources.bundles); setLoading(false);
        if (value.attempts.some(item => ['queued', 'running'].includes(item.status))) timer = setTimeout(() => void load(), 2000);
      } catch (error) { if (generation.current === epoch && !controller.signal.aborted) { setLoading(false); setFailure(String(error)); } }
    }
    void load();
    return () => { generation.current++; controller.abort(); if (timer) clearTimeout(timer); };
  }, [patient, cutoff, revision]);

  async function submit() {
    const epoch = generation.current;
    const config = mode === 'v0' ? 'poc-visit-v1' : mode === 'tau2' ? 'poc-visit-borrow-tau2-v1' : 'poc-visit-borrow-v1';
    const previous = attempts.find(attempt => ['failed', 'abstained'].includes(attempt.status) && attempt.cutoff === cutoff && attempt.configuration.id === config && (attempt.sources?.bundle_id ?? null) === (mode === 'v0' ? null : source));
    submitted.current ??= { key: crypto.randomUUID(), payload: { expected_version: workspace.snapshot.patient_version, previous_attempt: previous?.id ?? null, mode, source_bundle_id: mode === 'v0' ? null : source } };
    setSubmitting(true); setFailure('');
    try {
      const frozen = submitted.current;
      await request<AnalysisAttempt>(`/api/patients/${encodeURIComponent(patient)}/analyses`, { method: 'POST', headers: { 'Idempotency-Key': frozen.key }, body: JSON.stringify(frozen.payload) });
      // A context switch unmounts this component. The new patient's component
      // has independent requests/drafts and never receives this response.
      if (generation.current === epoch) { submitted.current = null; setRevision(value => value + 1); }
    } catch (error) { if (generation.current === epoch) {
      if (definitiveRejection(error)) {
        submitted.current = null; setNeedsRefresh(true);
        setFailure(`${String(error)}. The request was rejected. Refresh patient information before submitting a new intent.`);
      } else setFailure(`${String(error)}. Retry resolves the original request and key.`);
    } }
    finally { if (generation.current === epoch) setSubmitting(false); }
  }
  const pending = attempts.some(item => ['queued', 'running'].includes(item.status));
  const pendingAttempt = attempts.find(item => ['queued', 'running'].includes(item.status));
  const latest = attempts[0];
  const allowed = Boolean(workspace.simulation && workspace.simulation.day >= 14);
  const selectedBundle = bundles.find(bundle => bundle.bundle_id === source);
  const config = mode === 'v0' ? 'poc-visit-v1' : mode === 'tau2' ? 'poc-visit-borrow-tau2-v1' : 'poc-visit-borrow-v1';
  const compatible = attempts.filter(attempt => attempt.kind === 'visit_analysis' && attempt.configuration.id === config && (attempt.sources?.bundle_id ?? null) === (mode === 'v0' ? null : source) && attempt.serving.summary_available);
  const saved = compatible.find(attempt => attempt.serving.status === 'current') ?? compatible[0];
  const locked = pending || submitting || Boolean(submitted.current);
  return <section aria-labelledby="analysis-title"><p className="eyebrow">Observed-only synthetic analysis</p><h2 id="analysis-title">Visit analysis</h2><p>Opening this view reads saved summaries. Refresh analysis queues a frozen-cutoff background fit of the native PyMC model. V0 uses the original prior and this patient; V1 adds two approved fictional study summaries. Both predict the next 42 days under retained plans and fixed no-prompt support. You can continue eligible decisions and simulation while analysis is pending. No treatment is selected automatically.</p>
    <fieldset disabled={locked || loading}><legend>Analysis configuration</legend>
      <label className="radio"><input type="radio" name="analysis-mode" checked={mode === 'v0'} onChange={() => setMode('v0')}/>V0 · no external borrowing</label>
      <label className="radio"><input type="radio" name="analysis-mode" checked={mode === 'borrow'} onChange={() => setMode('borrow')}/>V1 · normalized robust source mixture, tau HalfNormal(1)</label>
      <label className="radio"><input type="radio" name="analysis-mode" checked={mode === 'tau2'} onChange={() => setMode('tau2')}/>V1 sensitivity · tau HalfNormal(2)</label>
      {mode !== 'v0' ? <><label htmlFor="source-bundle">Approved source bundle</label><select id="source-bundle" value={source} onChange={event => setSource(event.target.value)}><option value="">Choose a fictional bundle</option>{bundles.map(bundle => <option key={bundle.bundle_id} value={bundle.bundle_id}>{bundle.label} · {bundle.bundle_id}</option>)}</select></> : null}
    </fieldset>
    {mode !== 'v0' && selectedBundle ? <SourceDetails bundle={selectedBundle}/> : null}
    <button disabled={!allowed || pending || submitting || loading || needsRefresh || (mode !== 'v0' && !source)} onClick={() => void submit()}>{submitting ? 'Queuing analysis…' : submitted.current ? 'Retry original analysis request' : 'Refresh analysis'}</button>
    {needsRefresh ? <button className="secondary" onClick={refresh}>Refresh patient information</button> : null}
    {!allowed ? <p>Generate a v1 patient, choose a behavioral plan and advance to day 14 to run this representative.</p> : null}
    <details><summary>Joint visit analysis of twelve explicitly selected patients</summary><CohortSetup workspace={workspace} request={request} bundles={bundles} refresh={refresh} submitted={() => setRevision(value => value + 1)}/></details>
    {loading ? <p role="status">Loading saved analysis attempts…</p> : null}
    {failure ? <p role="alert" className="error">{failure}</p> : null}
    <div aria-live="polite">{pendingAttempt ? <p>Analysis {pendingAttempt.stage} for data through {date(pendingAttempt.cutoff)}. Ordinary approval and simulation remain available when eligible.</p> : latest && ['failed', 'abstained'].includes(latest.status) ? <p className="warning">Latest refresh {latest.status}: {latest.failure_reason ?? 'No accepted effect interval'}. Earlier saved results retain their original cutoff.</p> : null}</div>
    {!loading ? <section aria-labelledby="saved-analysis-title"><h3 id="saved-analysis-title">Saved result for this configuration</h3>{saved ? <><p>{saved.serving.status === 'current' ? 'Current available H* matches this accepted stored summary.' : 'Only dated accepted information is available. Current model advice is unavailable.'} A pending or failed refresh does not replace this saved result.</p><AnalysisResultView attempt={saved}/></> : <p>No compatible accepted stored summary is available. Refresh analysis can queue a new attempt; it does not provide immediate model advice.</p>}</section> : null}
    {attempts.length ? <details><summary>All saved analysis attempts ({attempts.length})</summary>{attempts.filter(attempt => attempt.id !== saved?.id).map(attempt => <AnalysisResultView key={attempt.id} attempt={attempt}/>)}</details> : null}
    {!loading && !attempts.length ? <p>No saved analysis attempts at this patient yet.</p> : null}
  </section>;
}

function CohortSetup({ workspace, request, bundles, refresh, submitted }: { workspace: Workspace; request: Request; bundles: StudyBundle[]; refresh: () => void; submitted: () => void }) {
  const [patients, setPatients] = useState<Panel['patients']>([]);
  const [selected, setSelected] = useState<string[]>([]);
  const [cohortId, setCohortId] = useState(() => `cohort-${crypto.randomUUID()}`);
  const [cutoff, setCutoff] = useState(workspace.snapshot.cutoff);
  const [research, setResearch] = useState(false); const [run, setRun] = useState('');
  const [source, setSource] = useState(''); const [mode, setMode] = useState<'v0' | 'borrow'>('v0');
  const [preview, setPreview] = useState<{ value: CohortPreview; selection: CohortSelection } | null>(null);
  const [approved, setApproved] = useState(false); const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false); const [failure, setFailure] = useState('');
  const intent = useRef<{ key: string; payload: CohortSelection & { approved_manifest_sha256: string; previous_attempt: null } } | null>(null);
  const active = useRef(true);
  const currentRequest = useRef(request); currentRequest.current = request;
  useEffect(() => {
    active.current = true; const controller = new AbortController();
    void currentRequest.current<Panel>('/api/patients', { signal: controller.signal }).then(value => { if (active.current && !controller.signal.aborted) { setPatients(value.patients); setLoading(false); } })
      .catch(error => { if (active.current && !controller.signal.aborted) { setFailure(String(error)); setLoading(false); } });
    return () => { active.current = false; controller.abort(); };
  }, []); // Parent is keyed by patient, authentication generation and snapshot.
  function invalidate() { setPreview(null); setApproved(false); setFailure(''); }
  async function refreshOwned() {
    invalidate(); setLoading(true);
    try { const value = await request<Panel>('/api/patients'); if (active.current) { setPatients(value.patients); setSelected(ids => ids.filter(id => value.patients.some(patient => patient.id === id))); } }
    catch (error) { if (active.current) setFailure(String(error)); }
    finally { if (active.current) setLoading(false); }
  }
  async function review() {
    const selection: CohortSelection = { cohort_id: cohortId, cutoff, research_run_id: research ? run : null, source_bundle_id: mode === 'v0' ? null : source,
      patient_versions: Object.fromEntries(patients.filter(patient => selected.includes(patient.id)).map(patient => [patient.id, patient.version])) };
    setBusy(true); setFailure(''); setApproved(false);
    try { const value = await request<CohortPreview>('/api/cohort-analyses/preview', { method: 'POST', body: JSON.stringify(selection) }); if (active.current) setPreview({ value, selection }); }
    catch (error) { if (active.current) { setPreview(null); setFailure(String(error)); } }
    finally { if (active.current) setBusy(false); }
  }
  async function submit() {
    if (!preview || !approved || !preview.value.executable) return;
    intent.current ??= { key: crypto.randomUUID(), payload: { ...preview.selection, approved_manifest_sha256: preview.value.manifest_sha256, previous_attempt: null } };
    setBusy(true); setFailure('');
    try { const frozen = intent.current; await request('/api/cohort-analyses', { method: 'POST', headers: { 'Idempotency-Key': frozen.key }, body: JSON.stringify(frozen.payload) }); if (active.current) { intent.current = null; invalidate(); submitted(); } }
    catch (error) { if (active.current) { if (definitiveRejection(error)) { intent.current = null; setPreview(null); setApproved(false); } setFailure(String(error)); } }
    finally { if (active.current) setBusy(false); }
  }
  const locked = busy || Boolean(intent.current);
  const ready = selected.length === 12 && selected.includes(workspace.patient_id) && (!research || Boolean(run)) && (mode === 'v0' || Boolean(source));
  return <section aria-labelledby="cohort-title"><h3 id="cohort-title">Review a joint twelve-patient cohort</h3>
    <p>Include this patient and eleven other owned patients at one reached observation cutoff. The service checks panel/run compatibility, ownership, versions and every reduced history. Research membership requires a separately trusted, registered export; entering a run ID does not register or authenticate it.</p>
    <button className="secondary" disabled={locked || loading} onClick={() => void refreshOwned()}>Refresh owned patient versions</button>
    <fieldset disabled={locked || loading}><legend>Explicit cohort membership · {selected.length} of 12 selected</legend>
      {patients.map(patient => <label className="radio" style={{ overflowWrap: 'anywhere' }} key={patient.id}><input type="checkbox" checked={selected.includes(patient.id)} disabled={selected.length >= 12 && !selected.includes(patient.id)} onChange={event => { invalidate(); setSelected(value => event.target.checked ? [...value, patient.id] : value.filter(id => id !== patient.id)); }}/>{patient.name} · {patient.id} · version {patient.version} · cutoff {date(patient.cutoff)}</label>)}
      <label htmlFor="cohort-id">Cohort ID</label><input id="cohort-id" name="cohort-id" autoComplete="off" spellCheck={false} value={cohortId} onChange={event => { invalidate(); setCohortId(event.target.value); }}/>
      <label htmlFor="cohort-cutoff">Common observation cutoff, with UTC offset</label><input id="cohort-cutoff" name="cohort-cutoff" autoComplete="off" spellCheck={false} value={cutoff} onChange={event => { invalidate(); setCutoff(event.target.value); }}/>
      <label className="radio" style={{ overflowWrap: 'anywhere' }}><input type="checkbox" checked={research} onChange={event => { invalidate(); setResearch(event.target.checked); }}/>Use an already registered research cohort</label>
      {research ? <><label htmlFor="cohort-run">Registered research run ID</label><input id="cohort-run" name="cohort-run" autoComplete="off" spellCheck={false} value={run} onChange={event => { invalidate(); setRun(event.target.value); }}/></> : null}
      <label htmlFor="cohort-mode">Joint model</label><select id="cohort-mode" value={mode} onChange={event => { invalidate(); setMode(event.target.value as 'v0' | 'borrow'); }}><option value="v0">V0 · original prior, no external summaries</option><option value="borrow">V1 · two approved summaries once, tau HalfNormal(1)</option></select>
      {mode === 'borrow' ? <><label htmlFor="cohort-source">Approved source bundle</label><select id="cohort-source" value={source} onChange={event => { invalidate(); setSource(event.target.value); }}><option value="">Choose a fictional source bundle</option>{bundles.map(bundle => <option key={bundle.bundle_id} value={bundle.bundle_id}>{bundle.label ?? bundle.bundle_id}</option>)}</select></> : null}
    </fieldset>
    <button className="secondary" disabled={!ready || locked || loading} onClick={() => void review()}>{busy ? 'Checking cohort…' : 'Review the complete frozen cohort'}</button>
    {loading ? <p role="status">Loading owned patients…</p> : null}
    {preview ? <><p className="hash">Manifest SHA256 {preview.value.manifest_sha256}<br/>Cohort H* SHA256 {preview.value.cohort_sha256}<br/>Configuration {preview.value.configuration.id}<br/>Source set {preview.value.source_set_sha256 ?? 'None'}</p><details><summary>All twelve reviewed members and history identities</summary><pre className="source-json">{JSON.stringify(preview.value.manifest, null, 2)}</pre></details>
      {!preview.value.executable ? <p role="status" className="warning">Analysis unavailable: {preview.value.unavailable_reason}. No cohort job has been submitted.</p> : null}
      <label className="radio" style={{ overflowWrap: 'anywhere' }}><input type="checkbox" disabled={locked || !preview.value.executable} checked={approved} onChange={event => setApproved(event.target.checked)}/>I approve this exact twelve-member manifest, cutoff and model configuration.</label>
      <button disabled={!approved || !preview.value.executable || busy} onClick={() => void submit()}>{intent.current ? 'Retry the original cohort request' : 'Submit this approved joint analysis'}</button></> : null}
    {failure ? <p role="alert" className="error">{failure}. <button className="secondary" disabled={locked} onClick={() => { refresh(); void refreshOwned(); }}>Refresh patient information</button></p> : null}
  </section>;
}
