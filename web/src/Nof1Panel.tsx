import { useEffect, useRef, useState } from 'react';
import type { Nof1, Workspace, Panel, NAnalysisAttempt, NConfiguration, NIdentity } from './types';
import { definitiveRejection } from './analysis-state.mjs';
import { loadIdentity, saveIdentity, reconcileIdentity } from './nof1-analysis-state.mjs';

type Request = <T>(url: string, options?: RequestInit) => Promise<T>;
const date = (value: string) => new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value));
const number = (value: number) => new Intl.NumberFormat(undefined, { maximumFractionDigits: 3 }).format(value);

const assertions = [
  ['both_options_acceptable', 'Both fictional MED_A and MED_B are acceptable'],
  ['stable_regimen_reviewed', 'Stable background regimen and chemotherapy/steroid timing reviewed'],
  ['interactions_reviewed', 'Fictional medication interactions and exclusions reviewed'],
  ['fall_risk_reviewed', 'Fall risk and sedation reviewed'],
  ['rescue_stop_plan_reviewed', 'Rescue and stop/review plan understood'],
  ['patient_agrees', 'Fictional patient agrees to this reversible comparison'],
] as const;

export function Nof1Timeline({ value }: { value: Nof1 }) {
  const loop = value.loop;
  return <section aria-labelledby="nof1-timeline-title"><h2 id="nof1-timeline-title">N-of-1 protocol timeline</h2>
    <p role="status">Status: {loop?.status ?? 'not started'}{loop?.phase ? ` · ${loop.phase} · block ${loop.block} · protocol day ${loop.protocol_day}` : ''}.</p>
    <p>Eight independent fair seven-night blocks, each followed by two washout nights. Reviews at days 36 and 72. Unblinded patient and clinician; no efficacy stopping. Behavioral continuation and no-prompt support stay frozen. Washout can retain exposure and rebound; a missed dose is distinct from assignment cessation.</p>
    <p>Saved N0/N1 analysis is reviewed separately below or in Analysis. Opening a view never starts a fit or selects a winner.</p>
    {loop?.draws.length ? <ol>{loop.draws.map(draw => <li key={draw.assignment_id}>Block {draw.block} · day {draw.day}: assigned <strong>{draw.option}</strong> at noon, probability 0.5 (both options 0.5), before 20:00 delivery. Washout starts day {draw.washout_starts_day}; next block/review boundary day {draw.next_boundary_day}. <details><summary>Saved assignment provenance</summary><p>{draw.assignment_id} · independent assignment seed, block {draw.block}. Assignment does not assert that the dose was taken.</p></details></li>)}</ol> : <p>No randomized medication has been drawn.</p>}
    {loop?.reviews.length ? <ul>{loop.reviews.map(review => <li key={review.day}>Review day {review.protocol_day}: {review.counts.MED_A} A blocks / {review.counts.MED_B} B blocks · {review.analysis_status.replaceAll('_', ' ')}.</li>)}</ul> : null}
    {loop?.deviations.length ? <div className="warning"><h3>Interrupted protocol</h3><ul>{loop.deviations.map((item, index) => <li key={index}>{item.reasons.join('; ')}</li>)}</ul><p>Past assignments remain saved. The original uninterrupted target is not claimed, and this protocol cannot restart automatically.</p></div> : null}
  </section>;
}

export function Nof1Panel({ workspace, commit, dirty, request, ownerId }: { workspace: Workspace; commit: (payload: Record<string, unknown>, key: string) => Promise<void>; dirty: boolean; request: Request; ownerId: string }) {
  const [pending, setPending] = useState(false);
  const [failure, setFailure] = useState('');
  const [confirming, setConfirming] = useState(false);
  const submitted = useRef<{ payload: Record<string, unknown>; key: string } | null>(null);
  const alive = useRef(true);
  useEffect(() => () => { alive.current = false; }, []);
  const value = workspace.nof1;
  if (!value) return null;
  const loop = value.loop;
  const closed = loop?.status === 'completed' || loop?.status === 'stopped';
  const active = loop?.status === 'active';
  const blocked = pending || dirty || workspace.snapshot.workflow.hold_reasons.length > 0;
  async function run(action: string, extra: Record<string, unknown> = {}) {
    const s = workspace.snapshot;
    submitted.current ??= { key: crypto.randomUUID(), payload: { mode: 'current', action, decision_id: s.record_id,
      expected_version: s.patient_version, expected_state_version: s.state_version, expected_consent_version: s.consent_version,
      expected_eligibility_version: s.eligibility_version, rationale: 'Explicit fictional physician review in the synthetic application', ...extra } };
    setPending(true); setFailure('');
    try { await commit(submitted.current.payload, submitted.current.key); if (alive.current) submitted.current = null; }
    catch (error) { if (alive.current) setFailure(String(error)); }
    finally { if (alive.current) setPending(false); }
  }
  return <><Nof1Timeline value={value}/><section aria-labelledby="nof1-controls-title"><h2 id="nof1-controls-title">Explicit fictional N-of-1 authorization</h2>
    <p>These are synthetic engineering review assertions. They do not establish human or clinical validation. Both medication names and kinetics are fictional.</p>
    {value.readiness_reasons.length && !closed && !active ? <ul>{value.readiness_reasons.map(reason => <li key={reason}>{reason}</li>)}</ul> : null}
    {closed ? <p>This saved protocol is closed. Continue reviewing its observations and history.</p> : active ? <button className="secondary" disabled={pending || dirty} onClick={() => void run('withdraw')}>Withdraw component consent and stop future blocks</button> : <fieldset disabled={blocked || Boolean(submitted.current)}>
      <form onSubmit={event => { event.preventDefault(); void run('consent'); }}><h3>1 · Component consent and oversight</h3><label className="radio"><input type="checkbox" required/>Record fictional nof1 consent and approved synthetic oversight for this patient</label><button>Record component consent and oversight</button></form>
      <form onSubmit={event => { event.preventDefault(); const form = new FormData(event.currentTarget); void run('review', { assertions: form.getAll('review') }); }}><h3>2 · Provisional eligibility review</h3>{assertions.map(([id, text]) => <label className="radio" key={id}><input type="checkbox" name="review" value={id} required/>{text}</label>)}<button>Save provisional eligibility review</button></form>
      <form onSubmit={event => { event.preventDefault(); setConfirming(true); }}><h3>3 · Approve the fixed protocol</h3><label className="radio"><input type="checkbox" required/>Explicitly approve MED_A</label><label className="radio"><input type="checkbox" required/>Explicitly approve MED_B</label><label className="radio"><input type="checkbox" required/>Approve template {value.template.id} and frozen behavioral continuation / no-prompt support</label><p>No winner is preselected. Each block is drawn independently only at its start.</p><button>Review fixed protocol approval</button></form>
      {confirming ? <div className="confirmation" aria-label="N-of-1 approval summary"><h3>Confirm both-option protocol</h3><p>{workspace.name} · {workspace.patient_id}. Both MED_A and MED_B, eight 7+2-night blocks, unblinded, reviews 36/72, frozen background and support. This approval does not start a block.</p><button onClick={() => void run('approve', { permitted_options: ['MED_A', 'MED_B'], template: value.template })}>Confirm both options and fixed template</button></div> : null}
      {loop?.approval_id ? <div className="notice"><h3>4 · Separate start</h3><p>Starting persists the fair block draw before delivery or outcomes. Current consent, safety and frozen background are rechecked.</p><button onClick={() => void run('start')}>Start approved N-of-1 protocol</button></div> : null}
    </fieldset>}
    {failure ? <p className="error" role="alert">{failure} Refresh and review stale information. An unresolved retry uses the original payload and key.</p> : null}
    {submitted.current && !pending && failure ? <button onClick={() => void run('retry')}>Retry original protocol command</button> : null}
  </section><Nof1Analysis workspace={workspace} request={request} ownerId={ownerId} context="current"/></>;
}

export function Nof1Analysis({ workspace, request, ownerId, context }: { workspace: Workspace; request: Request; ownerId: string; context: 'current' | 'saved_decision' }) {
  const patient = workspace.patient_id;
  const [initial] = useState(() => {
    try { return { value: loadIdentity(localStorage, ownerId, patient), error: '' }; }
    catch (error) { return { value: null, error: String(error) }; }
  });
  const [identity, setIdentity] = useState<NIdentity | null>(initial.value);
  const [attempts, setAttempts] = useState<NAnalysisAttempt[]>([]);
  const [patients, setPatients] = useState<Panel['patients']>([]);
  const [selected, setSelected] = useState<string[]>([patient]);
  const [configurations, setConfigurations] = useState<Record<'N0' | 'N1', NConfiguration> | null>(null);
  const [approved, setApproved] = useState(false);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [failure, setFailure] = useState(initial.error);
  const [notice, setNotice] = useState('');
  const [revision, setRevision] = useState(0);
  const live = useRef(true);
  const generation = useRef(0);
  const currentRequest = useRef(request); currentRequest.current = request;
  const currentIdentity = useRef(identity); currentIdentity.current = identity;
  const cutoff = workspace.snapshot.cutoff;
  useEffect(() => { live.current = true; return () => { live.current = false; }; }, []);
  function persist(value: NIdentity) {
    saveIdentity(localStorage, value); currentIdentity.current = value; setIdentity(value);
  }
  useEffect(() => {
    const epoch = ++generation.current; const controller = new AbortController();
    setLoading(true);
    let timer: ReturnType<typeof setTimeout> | undefined;
    async function load() {
      try {
        const original = currentIdentity.current;
        const receiptUrl = original?.intent ? `/api/nof1-analyses/receipt?target_id=${encodeURIComponent(patient)}&key=${encodeURIComponent(original.intent.key)}` : null;
        const [saved, panel, options, receipt] = await Promise.all([
          currentRequest.current<{ attempts: ({ kind: string } | NAnalysisAttempt)[] }>(`/api/patients/${encodeURIComponent(patient)}/analyses`, { signal: controller.signal }),
          context === 'current' ? currentRequest.current<Panel>('/api/patients', { signal: controller.signal }) : Promise.resolve(null),
          context === 'current' ? currentRequest.current<{ configurations: Record<'N0' | 'N1', NConfiguration> }>(`/api/patients/${encodeURIComponent(patient)}/nof1-analysis-options`, { signal: controller.signal }) : Promise.resolve(null),
          receiptUrl ? currentRequest.current<{ status: string; attempt: NAnalysisAttempt | null }>(receiptUrl, { signal: controller.signal }) : Promise.resolve(null),
        ]);
        if (generation.current !== epoch) return;
        const values = saved.attempts.filter((item): item is NAnalysisAttempt => item.kind === 'nof1_analysis');
        setAttempts(values);
        if (panel) setPatients(panel.patients.filter(p => p.state.simulation?.panel_id === workspace.simulation?.panel_id && p.state.simulation?.law_version === 'poc-longitudinal-v2'));
        if (options) setConfigurations(options.configurations);
        if (original?.intent && receipt) {
          const resolved = reconcileIdentity(original, receipt);
          persist(resolved);
          setNotice(resolved.intent ? 'Submission outcome remains unknown. Keep the original key and recheck saved status; no new fit will be submitted.' : 'Original submission found in saved status.');
        }
        setLoading(false);
        if (values.some(a => a.status === 'queued' || a.status === 'running')) timer = setTimeout(() => void load(), 2000);
      } catch (error) { if (generation.current === epoch && !controller.signal.aborted) { setFailure(String(error)); setLoading(false); } }
    }
    void load();
    return () => { generation.current++; controller.abort(); if (timer) clearTimeout(timer); };
  }, [patient, cutoff, context, revision]);

  const purpose = identity?.purpose ?? 'N1';
  const targeted = attempts.filter(a => a.target_id === patient && a.purpose === purpose);
  const selectedAttempt = targeted.find(a => a.id === identity?.selected_id) ?? targeted[0];
  const pending = attempts.some(a => a.status === 'queued' || a.status === 'running');
  const unresolved = Boolean(identity?.intent);
  const locked = submitting || unresolved || !identity;
  const members = patients.filter(p => selected.includes(p.id));
  const canSubmit = context === 'current' && configurations && identity && approved && !loading && !locked && !pending
    && members.length === selected.length && selected.includes(patient)
    && !workspace.snapshot.workflow.hold_reasons.length;

  function choosePurpose(value: 'N0' | 'N1') {
    if (!identity) return;
    try { persist({ ...identity, purpose: value, selected_id: null }); setApproved(false); }
    catch (error) { setFailure(String(error)); }
  }
  async function submit() {
    if (!canSubmit || !identity || !configurations) return;
    const original: NIdentity = { ...identity, intent: { key: crypto.randomUUID(), purpose } };
    const previous = targeted.find(a => (a.status === 'failed' || a.status === 'abstained')
      && new Date(a.cutoff).valueOf() === new Date(cutoff).valueOf()
      && a.cohort.length === selected.length && a.cohort.every(id => selected.includes(id)));
    setFailure(''); setNotice('');
    try { persist(original); }
    catch (error) { setFailure(`Cannot persist the original analysis identity: ${String(error)}. No request was sent.`); return; }
    setSubmitting(true);
    try {
      const result = await request<NAnalysisAttempt>('/api/nof1-analyses', { method: 'POST',
        headers: { 'Idempotency-Key': original.intent!.key }, body: JSON.stringify({ purpose, target_id: patient,
          cohort_id: `N-${workspace.simulation?.panel_id}`, patient_versions: Object.fromEntries(members.map(p => [p.id, p.version])),
          cutoff, configuration: configurations[purpose], previous_attempt: previous?.id ?? null }) });
      // Save the result identity even when navigation unmounted this view.
      const latest = loadIdentity(localStorage, ownerId, patient);
      const resolved = latest.intent?.key === original.intent!.key ? { ...latest, selected_id: result.id, intent: null } : latest;
      saveIdentity(localStorage, resolved);
      if (live.current) { currentIdentity.current = resolved; setIdentity(resolved); setApproved(false); setRevision(v => v + 1); }
    } catch (error) {
      if (definitiveRejection(error)) {
        try {
          const rejected = { ...original, intent: null }; saveIdentity(localStorage, rejected);
          if (live.current) { currentIdentity.current = rejected; setIdentity(rejected); setApproved(false); }
        } catch (storageError) { if (live.current) setFailure(`Original receipt identity could not be updated: ${String(storageError)}. Keep and reconcile its key.`); return; }
      }
      if (live.current) setFailure(`${String(error)}. ${definitiveRejection(error) ? 'Refresh patient information and review the cohort before a new command.' : 'The saved original key must be reconciled before another command.'}`);
    } finally { if (live.current) { setSubmitting(false); setRevision(v => v + 1); } }
  }
  return <section aria-labelledby="nof1-analysis-title"><h2 id="nof1-analysis-title">Saved N-of-1 analysis</h2>
    <p>Expected next-seven-night reported quality, assigned MED_A minus MED_B, in quality points. Positive values favor higher expected quality under A. N0 uses current taken indicators; N1 uses fixed 0.5 medication carryover. Both retain rebound, adherence, shared priors and the same restricted history. No automatic winner or treatment approval follows.</p>
    {context === 'saved_decision' ? <p className="history-notice">Separate saved analysis objects, generated independently of the original decision display. This historical view is read only and grants no new approval authority.</p> : null}
    <fieldset disabled={locked}><legend>Saved analysis purpose</legend>
      {(['N0', 'N1'] as const).map(value => <label className="radio" key={value}><input type="radio" name="nof1-purpose" checked={purpose === value} onChange={() => choosePurpose(value)}/>{value} · {value === 'N0' ? 'current taken indicator' : 'fixed medication carryover'}</label>)}
    </fieldset>
    {context === 'current' ? <><fieldset disabled={locked || loading || pending}><legend>Explicit owned cohort · target {patient}</legend>
      <p>Select this patient alone or a compatible owned cohort before viewing outcomes for the comparison. The service rechecks all members, versions, consent, holds, exposures, common cutoff and protocol-relative review 36/72.</p>
      {patients.map(p => <label className="radio hash" key={p.id}><input type="checkbox" checked={selected.includes(p.id)} disabled={p.id === patient} onChange={event => { setApproved(false); setSelected(ids => event.target.checked ? [...ids, p.id] : ids.filter(id => id !== p.id)); }}/>{p.name} · {p.id} · version {p.version} · {date(p.cutoff)}</label>)}
      <p>Target {patient}. Cutoff {date(cutoff)}. Configuration {configurations?.[purpose].id ?? 'loading'}.</p>
      <label className="radio"><input type="checkbox" checked={approved} onChange={event => setApproved(event.target.checked)}/>Confirm this explicit target, complete selected cohort, cutoff and configuration for one background analysis.</label>
    </fieldset><button disabled={!canSubmit} onClick={() => void submit()}>{submitting ? 'Saving analysis command…' : `Queue ${purpose} analysis`}</button></> : null}
    <button className="secondary" disabled={loading || submitting} onClick={() => { setFailure(initial.error); setRevision(v => v + 1); }}>Reload saved status{unresolved ? ' and reconcile original submission' : ''}</button>
    {loading ? <p role="status">Loading saved N analysis…</p> : null}{failure ? <p className="error" role="alert">{failure}</p> : null}{notice ? <p role="status">{notice}</p> : null}
    {unresolved ? <p className="warning">Original {identity?.intent?.purpose} submission outcome is unresolved. Reload uses its persisted receipt key; it never submits another fit.</p> : null}
    {targeted.length ? <><label htmlFor="nof1-saved-attempt">Saved review, cutoff and attempt</label><select id="nof1-saved-attempt" value={selectedAttempt?.id ?? ''} onChange={event => { if (identity) { try { persist({ ...identity, selected_id: event.target.value }); } catch (error) { setFailure(String(error)); } } }}>{targeted.map(a => <option key={a.id} value={a.id}>Review {a.review_day} · {date(a.cutoff)} · {a.status} · {a.id}</option>)}</select></> : !loading ? <p>No saved {purpose} attempt for this target. Opening or switching views does not queue analysis.</p> : null}
    {selectedAttempt ? <Nof1Estimate attempt={selectedAttempt}/> : null}
  </section>;
}

function Nof1Estimate({ attempt }: { attempt: NAnalysisAttempt }) {
  const result = attempt.result; const effect = result?.effect;
  return <article aria-label={`Saved ${attempt.purpose} analysis ${attempt.id}`}>
    <h3>{attempt.purpose} · {attempt.status} · {attempt.readiness}</h3>
    <p className="hash">Attempt {attempt.id}<br/>Target {attempt.target_id}<br/>Cohort {attempt.cohort_id}: {attempt.cohort.join(', ')}<br/>Configuration {attempt.configuration.id}</p>
    <p>Protocol-relative review {attempt.review_day}; data through {date(attempt.cutoff)}. {result ? `Generated ${date(result.generated_at)}.` : 'No saved result yet.'}</p>
    {attempt.stale ? <p className="warning">Dated saved analysis: {attempt.staleness_reason}. Its original target, cutoff and forecast remain fixed; it is unavailable as a current result.</p> : null}
    {attempt.serving.reason ? <p role="status">{attempt.serving.reason.replaceAll('_', ' ')}.</p> : null}
    {attempt.status === 'queued' || attempt.status === 'running' ? <p role="status">{attempt.stage}. The isolated background worker has not published an accepted interval.</p> : null}
    {attempt.failure_reason ? <p className="warning">{attempt.failure_reason}. No accepted interval is supplied.</p> : null}
    {effect && attempt.serving.saved_summary_available ? <><p><strong>Expected mean quality A minus B: {number(effect.mean)} points.</strong></p><p>95% posterior interval {number(effect.lower)} to {number(effect.upper)} points; posterior SD {number(effect.sd)}. This is uncertainty about the conditional expected assignment contrast after integrating future exposure, rebound, adherence, AR and measurement randomness.</p><p>Future quality trajectories and their availability are saved separately. Their predictive variability is not this expected-effect interval.</p></> : null}
    {result ? <ul>{result.limitations.map(text => <li key={text}>{text}</li>)}</ul> : null}
    <details><summary>Saved history identity, arm information and diagnostics</summary><p className="hash">H* SHA256 {attempt.history_sha256}<br/>Input SHA256 {attempt.input_sha256}<br/>Configuration SHA256 {attempt.configuration.sha256}</p><pre className="source-json">{JSON.stringify({ members: attempt.members, arm_blocks: attempt.arm_blocks, diagnostics: result?.diagnostics ?? null }, null, 2)}</pre></details>
  </article>;
}
