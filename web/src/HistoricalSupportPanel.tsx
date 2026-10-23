import { useEffect, useState } from 'react';
import type { HistoricalSupportWorkspace, SupportHistory } from './types';

type Request = <T>(url: string, options?: RequestInit) => Promise<T>;

export function HistoricalSupportPanel({ workspace, request }: { workspace: HistoricalSupportWorkspace; request: Request }) {
  const [mode, setMode] = useState<'S0' | 'S1'>(() => new URLSearchParams(location.search).get('mode') === 'S0' ? 'S0' : 'S1');
  const [day, setDay] = useState<14 | 42 | 84>(() => { const day = Number(new URLSearchParams(location.search).get('cutoff_day')); return day === 42 || day === 84 ? day : 14; });
  const [version, refresh] = useState(0);
  const [value, setValue] = useState<SupportHistory>(workspace.history);
  const [pending, setPending] = useState(false);
  const [failure, setFailure] = useState('');
  useEffect(() => {
    const controller = new AbortController(); let active = true;
    history.replaceState({}, '', `${location.pathname}?mode=${mode}&cutoff_day=${day}`);
    setPending(true); setFailure('');
    const url = `/api/patients/${encodeURIComponent(workspace.patient_id)}/observed-archives/${encodeURIComponent(workspace.archive_id)}?mode=${mode}&cutoff_day=${day}`;
    void request<SupportHistory>(url, { signal: controller.signal })
      .then(result => { if (active) setValue(result); })
      .catch(error => { if (active) setFailure(String(error)); })
      .finally(() => { if (active) setPending(false); });
    return () => { active = false; controller.abort(); };
  }, [workspace.patient_id, workspace.archive_id, mode, day, version]);
  const visible = !pending && !failure && value.mode === mode && value.cutoff_day === day ? value : null;
  const reports = visible?.projection.records.filter(r => r.kind === 'daily_report') ?? [];
  return <section aria-label="Historical support research">
    <p className="eyebrow">Synthetic historical research · read only</p><h1>{workspace.name}</h1><p>{workspace.patient_id} · paired S0/S1 member of a 12-member cohort.</p>
    <p>Saved synthetic support observations. Historical approvals and consent describe the original study; this archive grants no current treatment, support or simulation authority. Statistical estimation is a later gate.</p>
    <label htmlFor="support-mode">Historical support mode</label><select id="support-mode" value={mode} onChange={event => setMode(event.target.value as 'S0' | 'S1')}><option value="S0">S0 · fixed no prompt</option><option value="S1">S1 · micro-randomized support</option></select>
    <label htmlFor="support-cutoff">Historical observation cutoff</label><select id="support-cutoff" value={day} onChange={event => setDay(Number(event.target.value) as 14 | 42 | 84)}>{[14, 42, 84].map(cut => <option key={cut} value={cut}>Day {cut}</option>)}</select>
    <button className="secondary" onClick={() => refresh(n => n + 1)} disabled={pending}>Reload saved history</button>
    {pending ? <p role="status">Verifying owned historical proof…</p> : null}{failure ? <p className="error" role="alert">{failure}</p> : null}
    {visible ? <><p role="status">{visible.mode} · day {visible.cutoff_day} · {visible.projection.records.length} available records · partition {visible.partition_id}</p>
      <div className="table-wrap"><table><caption>Historical sleep quality reports · available before {visible.projection.cutoff}</caption><thead><tr><th scope="col">Observed</th><th scope="col">Available</th><th scope="col">Sleep quality</th></tr></thead><tbody>{reports.map(r => <tr key={r.record_id}><th scope="row">{r.event_at}</th><td>{r.available_at}</td><td>{r.missingness === 'observed' ? `${r.sleep_quality}/10` : 'Missing report'}</td></tr>)}</tbody></table></div>
      <details><summary>Saved provenance and qualification</summary><p>Qualification scope: {visible.receipt.qualification_scope}. Receipt wall time: {visible.receipt.received_at}. Simulated cutoff: {visible.projection.cutoff}.</p><p>Paired member: {visible.paired_member_id}. Cohort: {visible.cohort_id}.</p><p className="hash">Source {visible.receipt.source_commit}<br/>Original manifest SHA256 {visible.receipt.manifest_sha256}<br/>Admission SHA256 {visible.receipt.admission_sha256}<br/>Original projection SHA256 {visible.projection_sha256}</p></details></> : null}
  </section>;
}
