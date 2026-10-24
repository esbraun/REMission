import { useEffect, useRef, useState } from 'react';
import type { SupportControllerView, Workspace } from './types';

type Action = 'consent' | 'withdraw' | 'approve' | 'pause';
type Intent = { payload: Record<string, unknown>; key: string };
const label = (value: string) => value.replaceAll('_', ' ');
const date = (value: string) => new Date(value).toLocaleString();

export function SupportPanel({ workspace, request, commit, dirty }: {
  workspace: Workspace;
  request: <T>(url: string, init?: RequestInit) => Promise<T>;
  commit: (payload: Record<string, unknown>, key: string) => Promise<void>;
  dirty: boolean;
}) {
  const [status, setStatus] = useState<SupportControllerView | null>(null);
  const [failure, setFailure] = useState('');
  const [rationale, setRationale] = useState('');
  const [pending, setPending] = useState(false);
  const [intent, setIntent] = useState<Intent | null>(null);
  const current = useRef(true);
  useEffect(() => {
    let active = true;
    current.current = true;
    void request<SupportControllerView>(`/api/patients/${encodeURIComponent(workspace.patient_id)}/support`)
      .then(value => { if (active) setStatus(value); })
      .catch(error => { if (active) setFailure(String(error)); });
    return () => { active = false; current.current = false; };
  }, [request, workspace.patient_id]);
  async function send(action?: Action) {
    if (pending || dirty) return;
    const s = workspace.snapshot;
    const original = intent ?? { key: crypto.randomUUID(), payload: {
      schema_version: 's2-controller-source-1.0.0', mode: 'current', action,
      decision_id: s.record_id, expected_version: s.patient_version,
      expected_state_version: s.state_version, expected_consent_version: s.consent_version,
      expected_eligibility_version: s.eligibility_version, rationale, consent_expires_at: null,
    } };
    setIntent(original); setPending(true); setFailure('');
    try { await commit(original.payload, original.key); if (current.current) setIntent(null); }
    catch (error) { if (current.current) setFailure(String(error)); }
    finally { if (current.current) setPending(false); }
  }
  const last = status?.loop.last_decision;
  const reports = workspace.projection.records.filter(r => r.kind === 'daily_report');
  const missing = reports.filter(r => r.missingness !== 'observed').length;
  return <section aria-labelledby="support-title">
    <h2 id="support-title">Behavioral support</h2>
    <p>Approved support only; no medication choices. A ready saved prediction may guide a future draw. Opening this panel, approving care and advancing time never start or wait for fitting or prediction.</p>
    {!status && !failure ? <p role="status">Loading saved support status…</p> : null}
    {status ? <>
      <p>Envelope: <strong>{label(status.loop.status)}</strong>. Saved prediction: {status.saved.summary_available && status.saved.serving_authority ? 'current and admitted' : label(status.saved.reason ?? 'unavailable')}.</p>
      {!status.execution_available ? <p className="warning">Support assignment is unavailable: {status.activation_gap}. Existing support consent and decisions remain saved.</p> : null}
      {status.attempt ? <p>Saved attempt {status.attempt.job_id}: {label(status.attempt.status)}. Data through {date(status.attempt.cutoff)}; completed {status.attempt.finished_at ? date(status.attempt.finished_at) : 'not completed'}. {status.attempt.failure_reason ?? ''}</p> : <p>No saved prediction attempt. When both actions are eligible, a missing, stale, expired or unready result uses an explicitly recorded 0.5 fallback.</p>}
      {last ? <p>Last immutable decision {date(last.cutoff)}: {label(last.availability)}; final prompt probability {last.probabilities.support_prompt}; no-prompt probability {last.probabilities.no_prompt}. {last.fallback_reason ? `Fallback: ${label(last.fallback_reason)}.` : ''} Later worker output cannot change it.</p> : null}
      <p>{reports.length - missing} of {reports.length} reports observed; {missing} missing. No missing reward is scored as zero. Prompt cap: three in seven nights, with no consecutive prompts. N-of-1 block and washout retain their frozen no-prompt policy; restarting support requires a new explicit review.</p>
      <label htmlFor="support-rationale">Support review rationale</label>
      <textarea id="support-rationale" value={rationale} onChange={event => setRationale(event.target.value)} required maxLength={1000} disabled={pending || Boolean(intent) || dirty}/>
      <fieldset disabled={pending || Boolean(intent) || dirty || !rationale.trim()}>
        <legend>Separate component permission and support approval</legend>
        <div className="actions">
          <button className="secondary" onClick={() => void send('consent')}>Record synthetic support consent</button>
          <button disabled={!status.execution_available} onClick={() => void send('approve')}>Approve both support options</button>
          <button className="secondary" onClick={() => void send('pause')}>Pause support</button>
          <button className="secondary" onClick={() => void send('withdraw')}>Withdraw support consent</button>
        </div>
      </fieldset>
    </> : null}
    {dirty ? <p role="status">Save or discard your decision draft before a support command.</p> : null}
    {failure ? <p role="alert" className="error">{failure}</p> : null}
    {intent ? <p role="status">Keep the original command until its outcome is confirmed. <button disabled={pending} onClick={() => void send()}>{pending ? 'Checking saved command…' : 'Retry original support command'}</button></p> : null}
  </section>;
}
