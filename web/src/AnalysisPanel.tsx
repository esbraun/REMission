import { useEffect, useRef, useState } from 'react';
import type { AnalysisAttempt, Workspace } from './types';

type Request = <T>(url: string, options?: RequestInit) => Promise<T>;
const date = (value: string) => new Date(value).toLocaleString();
const number = (value: number) => value.toFixed(2);

function Result({ attempt }: { attempt: AnalysisAttempt }) {
  const result = attempt.result;
  return <article className="analysis-attempt" aria-labelledby={`attempt-${attempt.id}`}>
    <h3 id={`attempt-${attempt.id}`}>{attempt.configuration.id} · {attempt.status}</h3>
    <p className="hash">Attempt {attempt.id}</p>
    <dl><div><dt>Observation cutoff</dt><dd>{date(attempt.cutoff)}</dd></div><div><dt>Stage</dt><dd>{attempt.stage}</dd></div><div><dt>Compatible cohort</dt><dd>{attempt.cohort.join(', ')} · one-patient V0</dd></div></dl>
    {attempt.stale ? <p className="warning"><strong>Earlier cutoff.</strong> This result uses observations available at its saved cutoff. Refit to include the current observations.</p> : null}
    {attempt.previous_attempt ? <p>Deliberate retry of {attempt.previous_attempt}.</p> : null}
    {attempt.failure_reason ? <p className="error">{attempt.failure_reason}. No accepted effect interval is available.</p> : null}
    {result?.effect ? <><p><strong>Expected 42-day ISI difference: {number(result.effect.mean)} points</strong> (escalation minus continuation).</p><p>95% posterior interval {number(result.effect.lower)} to {number(result.effect.upper)} points; posterior SD {number(result.effect.sd)}. Negative values predict lower ISI under escalation. The endpoint averages future nights 29–42, retaining each assigned plan.</p><p>This interval describes uncertainty in the conditional expected effect after integrating future adherence, process and measurement randomness. It is separate from a future outcome predictive interval.</p></> : null}
    {result ? <><ul>{result.limitations.map(text => <li key={text}>{text}</li>)}</ul><details><summary>Actual computation and diagnostics</summary><pre className="source-json">{JSON.stringify(result.diagnostics, null, 2)}</pre></details></> : <p role="status">{attempt.status === 'queued' ? 'Waiting for the local isolated learner dispatcher.' : 'The isolated learner is working. You can review and approve ordinary care while analysis runs.'}</p>}
    <details><summary>Frozen input and configuration identity</summary><p className="hash">H* SHA256 {attempt.history_sha256}</p><p className="hash">Input SHA256 {attempt.input_sha256}</p><p className="hash">Configuration SHA256 {attempt.configuration.sha256}</p><p>EST-VISIT:poc-hstar-v1 · quality/ISI, reporting indicators and typed treatment/delivery history only. Function and diary are excluded from fitting.</p></details>
  </article>;
}

export function AnalysisPanel({ workspace, request }: { workspace: Workspace; request: Request }) {
  const [attempts, setAttempts] = useState<AnalysisAttempt[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [failure, setFailure] = useState('');
  const [revision, setRevision] = useState(0);
  const submitted = useRef<{ key: string; payload: { expected_version: number; previous_attempt: string | null } } | null>(null);
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
        const value = await currentRequest.current<{ attempts: AnalysisAttempt[] }>(`/api/patients/${encodeURIComponent(patient)}/analyses`, { signal: controller.signal });
        if (generation.current !== epoch) return;
        setAttempts(value.attempts); setLoading(false);
        if (value.attempts.some(item => ['queued', 'running'].includes(item.status))) timer = setTimeout(() => void load(), 2000);
      } catch (error) { if (generation.current === epoch && !controller.signal.aborted) { setLoading(false); setFailure(String(error)); } }
    }
    void load();
    return () => { generation.current++; controller.abort(); if (timer) clearTimeout(timer); };
  }, [patient, cutoff, revision]);

  async function submit() {
    const epoch = generation.current;
    submitted.current ??= { key: crypto.randomUUID(), payload: { expected_version: workspace.snapshot.patient_version, previous_attempt: attempts[0]?.id ?? null } };
    setSubmitting(true); setFailure('');
    try {
      const frozen = submitted.current;
      await request<AnalysisAttempt>(`/api/patients/${encodeURIComponent(patient)}/analyses`, { method: 'POST', headers: { 'Idempotency-Key': frozen.key }, body: JSON.stringify(frozen.payload) });
      // A context switch unmounts this component. The new patient's component
      // has independent requests/drafts and never receives this response.
      if (generation.current === epoch) { submitted.current = null; setRevision(value => value + 1); }
    } catch (error) { if (generation.current === epoch) setFailure(`${String(error)}. Retry resolves the original request and key.`); }
    finally { if (generation.current === epoch) setSubmitting(false); }
  }
  const pending = attempts.some(item => ['queued', 'running'].includes(item.status));
  const allowed = Boolean(workspace.simulation && workspace.simulation.day >= 14);
  return <section aria-labelledby="analysis-title"><p className="eyebrow">Observed-only synthetic analysis</p><h2 id="analysis-title">Visit analysis</h2><p>Fit the actual native PyMC model to cumulative available observations. V0 uses the declared prior and this patient only, without external borrowing. Future behavior contrasts two retained plans with fixed no-prompt support. No treatment is selected automatically.</p>
    <button disabled={!allowed || pending || submitting || loading} onClick={() => void submit()}>{submitting ? 'Submitting analysis…' : submitted.current ? 'Retry original analysis request' : attempts.length ? 'Run a new analysis at current cutoff' : 'Run V0 visit analysis'}</button>
    {!allowed ? <p>Generate a v1 patient, choose a behavioral plan and advance to day14 to run this representative.</p> : null}
    {loading ? <p role="status">Loading saved analysis attempts…</p> : null}
    {failure ? <p role="alert" className="error">{failure}</p> : null}
    <div aria-live="polite">{pending ? <p>Analysis {attempts.find(item => ['queued', 'running'].includes(item.status))?.stage}. Ordinary approval remains available.</p> : null}</div>
    {attempts.map(attempt => <Result key={attempt.id} attempt={attempt}/>)}
    {!loading && !attempts.length ? <p>No saved analysis attempts at this patient yet.</p> : null}
  </section>;
}
