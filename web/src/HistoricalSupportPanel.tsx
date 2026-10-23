import { useEffect, useRef, useState } from 'react';
import { definitiveRejection } from './analysis-state.mjs';
import type { HistoricalSupportWorkspace, SupportHistory, SupportS1Attempt, SupportS1Attempts } from './types';

type Request = <T>(url: string, options?: RequestInit) => Promise<T>;

export function HistoricalSupportPanel({ workspace, request }: { workspace: HistoricalSupportWorkspace; request: Request }) {
  const [mode, setMode] = useState<'S0' | 'S1'>(() => new URLSearchParams(location.search).get('mode') === 'S0' ? 'S0' : 'S1');
  const [day, setDay] = useState<14 | 42 | 84>(() => { const day = Number(new URLSearchParams(location.search).get('cutoff_day')); return day === 42 || day === 84 ? day : 14; });
  const [version, refresh] = useState(0);
  const [value, setValue] = useState<SupportHistory>(workspace.history);
  const [pending, setPending] = useState(false);
  const [failure, setFailure] = useState('');
  const [analyses, setAnalyses] = useState<SupportS1Attempts | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [submitFailure, setSubmitFailure] = useState('');
  const [notice, setNotice] = useState('');
  const intent = useRef<{ key: string; payload: { archive_id: string; mode: 'S1'; cutoff_day: number; configuration: SupportS1Attempts['configuration']; previous_attempt: null } } | null>(null);
  const activeSelection = useRef('');
  activeSelection.current = `${workspace.archive_id}:${mode}:${day}`;

  useEffect(() => {
    const controller = new AbortController(); let active = true;
    history.replaceState({}, '', `${location.pathname}?mode=${mode}&cutoff_day=${day}`);
    setPending(true); setFailure(''); setAnalyses(null); setNotice(''); setSubmitFailure('');
    const url = `/api/patients/${encodeURIComponent(workspace.patient_id)}/observed-archives/${encodeURIComponent(workspace.archive_id)}?mode=${mode}&cutoff_day=${day}`;
    const attemptsUrl = `/api/support-s1-analyses?archive_id=${encodeURIComponent(workspace.archive_id)}&cutoff_day=${day}`;
    void Promise.all([request<SupportHistory>(url, { signal: controller.signal }), mode === 'S1' ? request<SupportS1Attempts>(attemptsUrl, { signal: controller.signal }) : Promise.resolve(null)])
      .then(([result, saved]) => { if (active) { setValue(result); setAnalyses(saved); } })
      .catch(error => { if (active) setFailure(String(error)); })
      .finally(() => { if (active) setPending(false); });
    return () => { active = false; controller.abort(); };
  }, [workspace.patient_id, workspace.archive_id, mode, day, version]);
  const visible = !pending && !failure && value.mode === mode && value.cutoff_day === day ? value : null;
  async function runAnalysis() {
    if (!intent.current) {
      if (!analyses || mode !== 'S1') return;
      intent.current = { key: crypto.randomUUID(), payload: { archive_id: workspace.archive_id, mode: 'S1', cutoff_day: day, configuration: analyses.configuration, previous_attempt: null } };
    }
    const command = intent.current; const selected = activeSelection.current;
    setSubmitting(true); setSubmitFailure(''); setNotice('');
    try {
      await request<SupportS1Attempt>('/api/support-s1-analyses', { method: 'POST', headers: { 'Idempotency-Key': command.key }, body: JSON.stringify(command.payload) });
      intent.current = null;
      if (activeSelection.current === selected) { setNotice(`Cohort S1 submission saved for day ${command.payload.cutoff_day}. Reload saved status to check progress.`); refresh(n => n + 1); }
    } catch (error) {
      const rejected = definitiveRejection(error);
      if (rejected) intent.current = null;
      if (activeSelection.current === selected) setSubmitFailure(`${String(error)}. ${rejected ? 'Refresh the saved archive and status before a new explicit command.' : 'The original command key is retained; resolve it before starting another attempt.'}`);
    }
    finally { setSubmitting(false); }
  }
  const canRun = visible?.mode === 'S1' && visible.receipt.qualification_scope === 'accepted_saved_producer' && analyses !== null;
  const hasPending = analyses?.attempts.some(a => a.status === 'queued' || a.status === 'running') ?? false;
  const reports = visible?.projection.records.filter(r => r.kind === 'daily_report') ?? [];
  return <section aria-label="Historical support research">
    <p className="eyebrow">Synthetic historical research · read only</p><h1>{workspace.name}</h1><p>{workspace.patient_id} · paired S0/S1 member of a 12-member cohort.</p>
    <p>Saved synthetic support observations. Historical approvals and consent describe the original study; this archive grants no current treatment, support or simulation authority. S1 estimation runs only after an explicit cohort research command.</p>
    <label htmlFor="support-mode">Historical support mode</label><select id="support-mode" value={mode} onChange={event => setMode(event.target.value as 'S0' | 'S1')}><option value="S0">S0 · fixed no prompt</option><option value="S1">S1 · micro-randomized support</option></select>
    <label htmlFor="support-cutoff">Historical observation cutoff</label><select id="support-cutoff" value={day} onChange={event => setDay(Number(event.target.value) as 14 | 42 | 84)}>{[14, 42, 84].map(cut => <option key={cut} value={cut}>Day {cut}</option>)}</select>
    <button className="secondary" onClick={() => refresh(n => n + 1)} disabled={pending}>Reload saved history and status</button>
    {pending ? <p role="status">Verifying owned historical proof…</p> : null}{failure ? <p className="error" role="alert">{failure}</p> : null}
    <section aria-label="Cohort S1 analysis">
      <h2>Cohort S1 analysis</h2>
      <p>12-member historical cohort · prompt versus no prompt · next-morning sleep quality points. A positive coefficient means higher quality. This estimate does not establish ISI benefit, an individual prediction or a support policy.</p>
      {mode === 'S0' ? <p>S0 is descriptive. Select S1 to view and explicitly run its randomized cohort analysis.</p> : <>
        <button onClick={() => void runAnalysis()} disabled={submitting || (!intent.current && (!canRun || pending || hasPending))}>{submitting ? 'Saving cohort command…' : intent.current ? `Resolve original day ${intent.current.payload.cutoff_day} submission` : 'Run cohort S1 analysis'}</button>
        {!pending && visible && !canRun ? <p>This archive has no accepted producer qualification for estimation.</p> : null}
        {notice ? <p role="status">{notice}</p> : null}{submitFailure ? <p className="error" role="alert">{submitFailure}</p> : null}
        {!pending && analyses?.attempts.length === 0 ? <p>No saved S1 attempt for day {day}. Navigation does not start estimation.</p> : null}
        {!pending ? analyses?.attempts.filter(a => a.archive_id === workspace.archive_id && a.cutoff_day === day && a.mode === 'S1').map(a => <SupportEstimate key={a.id} attempt={a}/>) : null}
      </>}
    </section>
    {visible ? <><p role="status">{visible.mode} · day {visible.cutoff_day} · {visible.projection.records.length} available records · partition {visible.partition_id}</p>
      <div className="table-wrap"><table><caption>Historical sleep quality reports · available before {visible.projection.cutoff}</caption><thead><tr><th scope="col">Observed</th><th scope="col">Available</th><th scope="col">Sleep quality</th></tr></thead><tbody>{reports.map(r => <tr key={r.record_id}><th scope="row">{r.event_at}</th><td>{r.available_at}</td><td>{r.missingness === 'observed' ? `${r.sleep_quality}/10` : 'Missing report'}</td></tr>)}</tbody></table></div>
      <details><summary>Saved provenance and qualification</summary><p>Qualification scope: {visible.receipt.qualification_scope}. Receipt wall time: {visible.receipt.received_at}. Simulated cutoff: {visible.projection.cutoff}.</p><p>Paired member: {visible.paired_member_id}. Cohort: {visible.cohort_id}.</p><p className="hash">Source {visible.receipt.source_commit}<br/>Original manifest SHA256 {visible.receipt.manifest_sha256}<br/>Admission SHA256 {visible.receipt.admission_sha256}<br/>Original projection SHA256 {visible.projection_sha256}</p></details></> : null}
  </section>;
}


const number = new Intl.NumberFormat(undefined, { maximumFractionDigits: 4 });
const date = new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' });
function SupportEstimate({ attempt }: { attempt: SupportS1Attempt }) {
  const result = attempt.result; const output = result?.output; const wcls = result?.diagnostics.wcls;
  return <article aria-label={`Saved cohort S1 attempt ${attempt.id}`}>
    <h3>Day {attempt.cutoff_day} · {attempt.status}</h3>
    <p className="hash">Attempt {attempt.id} · cohort {attempt.cohort_id}</p>
    <p>Data through {date.format(new Date(attempt.cutoff))}. Generated {result ? date.format(new Date(result.generated_at)) : 'not yet available'}.</p>
    {attempt.stale ? <p role="status">Saved result unavailable: {attempt.staleness_reason}. Reload the archive before a new explicit command.</p> : null}
    {attempt.status === 'queued' || attempt.status === 'running' ? <p role="status">{attempt.stage}. Reload saved status to check progress; no automatic retry.</p> : null}
    {attempt.status === 'failed' || attempt.status === 'abstained' ? <p role="status">{result?.reason || attempt.failure_reason || 'No accepted estimate or interval is available.'}</p> : null}
    {attempt.status === 'completed' && !result ? <p role="status">The saved summary is unavailable or unaccepted. Reload the archive and status.</p> : null}
    {!attempt.stale && output ? <p><strong>{number.format(output.coefficient)} quality points</strong> · participant-clustered 95% interval [{number.format(output.interval[0])}, {number.format(output.interval[1])}] · df {output.df}.</p> : null}
    {!attempt.stale && output ? <p>The primary estimate uses complete observed rewards under the synthetic independent 10% MCAR reporting law; it is not an identified adjustment for outcome- or action-dependent missingness.</p> : null}
    {wcls ? <><p>{wcls.counts.observed} observed rewards · {wcls.counts.missing} missing rewards · {wcls.counts.participants} contributing participant clusters.{wcls.counts.eligible_counts_complete ? '' : ' Eligible/missing counts are incomplete because missing-only context was unavailable.'}</p>
      <p>Missing-reward sensitivity: {wcls.sensitivity_status === 'available' && wcls.sensitivity_range ? `nine assumption-driven R1 point estimates; range ${number.format(wcls.sensitivity_range[0])} to ${number.format(wcls.sensitivity_range[1])}. No sensitivity interval or MNAR identification.` : `unavailable: ${wcls.sensitivity_reason || 'required context unavailable'}.`}</p>
      {wcls.sensitivity.length ? <details><summary>Inspect nine sensitivity points</summary><div className="table-wrap"><table><caption>Assumption-driven point sensitivity only</caption><thead><tr><th scope="col">No-prompt delta</th><th scope="col">Prompt delta</th><th scope="col">Quality points</th></tr></thead><tbody>{wcls.sensitivity.map(cell => <tr key={`${cell.delta0}:${cell.delta1}`}><td>{cell.delta0}</td><td>{cell.delta1}</td><td>{number.format(cell.estimate)}</td></tr>)}</tbody></table></div></details> : null}</> : null}
  </article>;
}
