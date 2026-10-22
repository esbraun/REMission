import { useEffect, useRef, useState } from 'react';
import type { AnalysisAttempt, AnalysisComparison, Workspace } from './types';
import { definitiveRejection } from './analysis-state.mjs';

type Request = <T>(url: string, options?: RequestInit) => Promise<T>;
const formatter = new Intl.NumberFormat(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const number = (value: number | null) => value === null ? 'Unavailable' : formatter.format(value);

export function ResearchPanel({ workspace, request }: { workspace: Workspace; request: Request }) {
  const [attempts, setAttempts] = useState<AnalysisAttempt[]>([]);
  const [comparisons, setComparisons] = useState<AnalysisComparison[]>([]);
  const [left, setLeft] = useState(''); const [right, setRight] = useState('');
  const [failure, setFailure] = useState(''); const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false); const [revision, setRevision] = useState(0);
  const currentRequest = useRef(request); currentRequest.current = request;
  const generation = useRef(0);
  const submitted = useRef<{ key: string; left: string; right: string } | null>(null);
  const patient = workspace.patient_id; const cutoff = workspace.snapshot.cutoff;
  useEffect(() => {
    const epoch = ++generation.current; const controller = new AbortController();
    void Promise.all([
      currentRequest.current<{ attempts: AnalysisAttempt[] }>(`/api/patients/${encodeURIComponent(patient)}/analyses`, { signal: controller.signal }),
      currentRequest.current<{ comparisons: AnalysisComparison[] }>(`/api/patients/${encodeURIComponent(patient)}/analysis-comparisons`, { signal: controller.signal })
    ]).then(([a, c]) => { if (epoch === generation.current) { setAttempts(a.attempts); setComparisons(c.comparisons); setLoading(false); } })
      .catch(error => { if (epoch === generation.current && !controller.signal.aborted) { setFailure(String(error)); setLoading(false); } });
    return () => { generation.current++; controller.abort(); };
  }, [patient, cutoff, revision]);

  async function save() {
    const epoch = generation.current; submitted.current ??= { key: crypto.randomUUID(), left, right };
    const intent = submitted.current; setSaving(true); setFailure('');
    try {
      await request(`/api/patients/${encodeURIComponent(patient)}/analysis-comparisons`, { method: 'POST', headers: { 'Idempotency-Key': intent.key }, body: JSON.stringify({ left: intent.left, right: intent.right }) });
      if (generation.current === epoch) { submitted.current = null; setRevision(value => value + 1); }
    } catch (error) { if (generation.current === epoch) { if (definitiveRejection(error)) submitted.current = null; setFailure(String(error)); } }
    finally { if (generation.current === epoch) setSaving(false); }
  }
  const terminal = attempts.filter(attempt => !['queued', 'running'].includes(attempt.status));
  const label = (attempt: AnalysisAttempt) => `${attempt.configuration.id} · ${new Date(attempt.cutoff).toLocaleDateString()} · ${attempt.status} · ${attempt.id}`;
  return <section aria-labelledby="research-title"><p className="eyebrow">Synthetic research · saved actual computations</p><h2 id="research-title">Paired borrowing comparison</h2>
    <p>Pair V0 and V1 attempts with identical patient H*, cutoff and protocol. Joint attempts must also share the exact twelve-member manifest. The service checks identities and saves an immutable comparison artifact. Joint results retain twelve separate expected effects. Estimates, uncertainty and observed runtime are descriptive; independent conditional truth and recovery accuracy belong to the later PA6 study.</p>
    <p>Carryover/N-of-1 and support-policy ablations remain deferred PA4/PA5 work. This view currently compares borrowing only.</p>
    <button className="secondary" disabled={loading || saving || Boolean(submitted.current)} onClick={() => { setLoading(true); setFailure(''); setRevision(value => value + 1); }}>Refresh attempts and comparisons</button>
    <fieldset disabled={saving || Boolean(submitted.current)}><legend>Choose actual finished attempts</legend>
      <label htmlFor="comparison-v0">V0 attempt</label><select id="comparison-v0" name="comparison-v0" autoComplete="off" value={left} onChange={event => setLeft(event.target.value)}><option value="">Choose V0</option>{terminal.filter(attempt => ['poc-visit-v1','poc-visit-cohort-v1'].includes(attempt.configuration.id)).map(attempt => <option key={attempt.id} value={attempt.id}>{label(attempt)}</option>)}</select>
      <label htmlFor="comparison-v1">V1 attempt</label><select id="comparison-v1" name="comparison-v1" autoComplete="off" value={right} onChange={event => setRight(event.target.value)}><option value="">Choose V1</option>{terminal.filter(attempt => ['poc-visit-borrow-v1', 'poc-visit-borrow-tau2-v1','poc-visit-cohort-borrow-v1'].includes(attempt.configuration.id)).map(attempt => <option key={attempt.id} value={attempt.id}>{label(attempt)}</option>)}</select>
    </fieldset>
    <button disabled={!left || !right || saving || loading} onClick={() => void save()}>{saving ? 'Saving comparison…' : submitted.current ? 'Retry original comparison request' : 'Save paired comparison'}</button>
    {loading ? <p role="status">Loading actual attempts and saved comparisons…</p> : null}
    <div aria-live="polite">{saving ? <p>Saving the immutable paired comparison…</p> : null}</div>
    {failure ? <p role="alert" className="error">{failure}</p> : null}
    {comparisons.map(comparison => comparison.kind === 'poc_cohort_v0_v1_comparison' ? <article key={comparison.id} className="analysis-attempt"><h3>Saved joint cohort comparison · {new Date(comparison.cutoff).toLocaleString()}</h3><p className="hash">{comparison.id}<br/>Manifest SHA256 {comparison.manifest_sha256}<br/>Cohort H* SHA256 {comparison.cohort_sha256}</p><p>One joint posterior per attempt, with separate patient effects. The worker duration is shared by all twelve rows; it is not a per-patient fit duration.</p>
      <div className="table-wrap"><table><caption>Per-patient expected next 42-day ISI contrast: escalation minus continuation</caption><thead><tr><th>Joint attempt / configuration</th><th>Patient</th><th>Status</th><th>Mean</th><th>95% posterior interval</th><th>Width</th><th>Joint worker seconds</th></tr></thead><tbody>{comparison.attempts.flatMap(attempt => attempt.patients?.length ? attempt.patients.map(patient => <tr key={`${attempt.id}:${patient.patient_id}`}><td className="hash">{attempt.id}<br/>{attempt.configuration.id}</td><td className="hash">{patient.patient_id}</td><td>{patient.status}{patient.reason ? ` · ${patient.reason}` : ''}</td><td>{patient.effect ? number(patient.effect.mean) : 'No accepted estimate'}</td><td>{patient.effect ? `${number(patient.effect.lower)} to ${number(patient.effect.upper)}` : 'Unavailable'}</td><td>{patient.effect ? number(patient.effect.upper-patient.effect.lower) : 'Unavailable'}</td><td>{number(attempt.worker_seconds)}</td></tr>) : [<tr key={attempt.id}><td className="hash">{attempt.id}<br/>{attempt.configuration.id}</td><td colSpan={6}>{attempt.status} · {attempt.failure_reason ?? 'No accepted cohort estimates'}</td></tr>])}</tbody></table></div>
      <ul>{comparison.limitations.map(text => <li key={text}>{text}</li>)}</ul><details><summary>Frozen complete cohort comparison</summary><pre className="source-json">{JSON.stringify(comparison,null,2)}</pre></details>
    </article> : <article key={comparison.id} className="analysis-attempt"><h3>Saved comparison · {new Date(comparison.cutoff).toLocaleString()}</h3><p className="hash">{comparison.id}<br/>H* SHA256 {comparison.history_sha256}</p>
      <div className="table-wrap"><table><caption>Expected next 42-day ISI contrast: escalation minus continuation</caption><thead><tr><th>Actual attempt/configuration</th><th>Status</th><th>Posterior mean</th><th>95% posterior interval</th><th>Width</th><th>Worker seconds</th></tr></thead><tbody>{comparison.attempts.map(attempt => <tr key={attempt.id}><td><span className="hash">{attempt.id}</span><br/>{attempt.configuration.id}</td><td>{attempt.status}{attempt.failure_reason ? ` · ${attempt.failure_reason}` : ''}</td><td>{attempt.effect ? number(attempt.effect.mean) : 'No accepted estimate'}</td><td>{attempt.effect ? `${number(attempt.effect.lower)} to ${number(attempt.effect.upper)}` : 'Unavailable'}</td><td>{number(attempt.interval_width)}</td><td>{number(attempt.worker_seconds)}</td></tr>)}</tbody></table></div>
      <ul>{comparison.limitations.map(text => <li key={text}>{text}</li>)}</ul><details><summary>Frozen comparison artifact</summary><pre className="source-json">{JSON.stringify(comparison, null, 2)}</pre></details>
    </article>)}
    {!loading && !comparisons.length ? <p>No paired comparison has been saved for this patient.</p> : null}
  </section>;
}
