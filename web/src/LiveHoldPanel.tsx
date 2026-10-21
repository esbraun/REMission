import React, { useEffect, useRef, useState } from 'react';
import type { Workspace } from './types';

type Ref = { id: string; version: string; sha256: string };
type Evidence = { store: 'archive' | 'event' | 'live_review'; namespace_id: string; partition_id: string | null; record_id: string; payload_sha256: string };
type Obligation = { requirement_id: string; definition: Ref; responsible_role: string; evidence_kinds: string[]; source_ids: string[] };
type Episode = { episode_id: string; generation: number; opened_at: string; reason_codes: string[]; trigger_set_sha256: string; obligation_set_sha256: string; trigger_refs: Evidence[]; obligations: Obligation[]; review_rules: Ref[]; task_ids: string[]; clearance_supported: boolean; blocker: string | null; current_review: { payload: { review_id: string; result: string; current_review_at: string; rationale: string }; payload_sha256: string } | null };
type Holds = { episodes: Episode[]; tasks: { id: string; owner_id: string; due_at: string; payload: { escalation_destination: string }; events: { status: string }[] }[]; available_triggers: { label: string; command: object }[] };
type Requester = <T>(url: string, options?: RequestInit) => Promise<T>;
type Props = { workspace: Workspace; request: Requester; refresh: () => void; changed: (dirty: boolean) => void };

function localTime(value: string) { return new Date(value).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' }); }

export function LiveHoldPanel({ workspace, request, refresh, changed }: Props) {
  const [holds, setHolds] = useState<Holds | null>(null);
  const [error, setError] = useState('');
  const [pending, setPending] = useState(false);
  const [evidence, setEvidence] = useState<unknown>(null);
  const [entry, setEntry] = useState('');
  const alive = useRef(true);
  const original = useRef<{ url: string; value: unknown; key: string } | null>(null);
  const url = `/api/patients/${encodeURIComponent(workspace.patient_id)}`;
  useEffect(() => {
    alive.current = true;
    void request<Holds>(`${url}/live-holds`).then(value => { if (alive.current) setHolds(value); }).catch(reason => { if (alive.current) setError(String(reason)); });
    return () => { alive.current = false; };
  }, [url, workspace.snapshot.record_id]);

  async function submit(path: string, value: unknown) {
    const command = original.current ?? { url: path, value, key: crypto.randomUUID() };
    original.current = command; setPending(true); setError('');
    try {
      await request(command.url, { method: 'POST', headers: { 'Idempotency-Key': command.key }, body: JSON.stringify(command.value) });
      if (alive.current) { original.current = null; changed(false); refresh(); }
    } catch (reason) { if (alive.current) setError(`${String(reason)}. Refresh current information and review changed facts. Retry uses the original operation key.`); }
    finally { if (alive.current) setPending(false); }
  }
  function current(episode: Episode) {
    const s = workspace.snapshot;
    return { schema_version: '1.0.0', contract: 'LIVE-HOLD-01', synthetic: true, mode: 'current', decision_id: s.record_id,
      expected_patient_version: s.patient_version, expected_state_version: s.state_version, expected_consent_version: s.consent_version,
      expected_eligibility_version: s.eligibility_version, expected_episode_generation: episode.generation,
      trigger_set_sha256: episode.trigger_set_sha256, review_rules: episode.review_rules };
  }
  async function showEvidence(reference: Evidence) {
    try {
      if (reference.store === 'archive') {
        const value = await request<{ entries: { record: { record_id: string }; raw_source: string }[] }>(`${url}/observed-archives/${encodeURIComponent(reference.namespace_id)}`);
        if (alive.current) setEvidence(value.entries.filter(item => item.record.record_id === reference.record_id));
      } else if (reference.store === 'event') {
        const value = await request(`${url}/events/${encodeURIComponent(reference.record_id)}`);
        if (alive.current) setEvidence(value);
      }
    } catch (reason) { if (alive.current) setError(String(reason)); }
  }
  function review(event: React.FormEvent<HTMLFormElement>, episode: Episode) {
    event.preventDefault(); const form = new FormData(event.currentTarget);
    const items = episode.obligations.map((obligation, i) => ({ requirement_id: obligation.requirement_id, definition: obligation.definition,
      finding: String(form.get(`finding-${i}`)), result: String(form.get(`result-${i}`)),
      evidence_refs: episode.trigger_refs.filter((_ref, n) => form.has(`evidence-${i}-${n}`)) }));
    void submit(`${url}/live-holds/${encodeURIComponent(episode.episode_id)}/reviews`, { ...current(episode), rationale: String(form.get('review-rationale')), items, current_assessment_attested: true });
  }

  return <section aria-labelledby="live-hold-title" className="live-holds"><h2 id="live-hold-title">Independent safety review</h2>
    <p>Synthetic structural workflow. The owning doctor reviews exact evidence and changed facts. No automatic readiness or protocol restoration follows clearance.</p>
    {error ? <div role="alert" className="error"><p>{error}</p><button className="secondary" onClick={refresh}>Refresh safety information</button>{original.current ? <button disabled={pending} onClick={() => { const command = original.current; if (command) void submit(command.url, command.value); }}>Retry original safety operation</button> : null}</div> : null}
    {!holds ? <p role="status">Loading owned holds and review tasks…</p> : <>
      {holds.episodes.length ? holds.episodes.map(episode => {
        const tasks = holds.tasks.filter(item => episode.task_ids.includes(item.id));
        return <article key={`${episode.episode_id}:${episode.generation}`} className="hold-episode"><h3>{episode.reason_codes.join(', ').replaceAll('_', ' ')} · episode generation {episode.generation}</h3>
          <p><strong>Hold remains active.</strong> Entered {localTime(episode.opened_at)}.</p>
          <h4>Owned review follow-ups</h4><ul>{tasks.map(task => <li key={task.id}>Review owner: {task.owner_id}; due {localTime(task.due_at)}. Status: {task.events.at(-1)?.status ?? 'unavailable'}. Escalation: {task.payload.escalation_destination}.</li>)}</ul>
          <p>Assignments and ordinary approval are blocked. Previous estimates may be inapplicable. Support remains paused.</p>
          <h4>Exact triggering evidence</h4><ul>{episode.trigger_refs.map(reference => <li key={reference.record_id}><button className="link evidence-link" onClick={() => void showEvidence(reference)}>Inspect {reference.record_id}</button><span className="hash">SHA256 {reference.payload_sha256}</span></li>)}</ul>
          {!episode.clearance_supported ? <p className="warning"><strong>{episode.blocker}</strong>: an accepted clearance criterion is unavailable for one or more active obligations. The whole episode remains held; there is no timer or default clearance.</p> : null}
          <details><summary>Installed review rules and all active obligations</summary><ul>{episode.review_rules.map(rule => <li key={rule.id}>{rule.id} {rule.version}<span className="hash">{rule.sha256}</span></li>)}</ul><ul>{episode.obligations.map(item => <li key={item.requirement_id}>{item.requirement_id} · {item.definition.id} {item.definition.version} · {item.responsible_role}</li>)}</ul></details>
          {episode.review_rules.length ? <form onSubmit={event => review(event, episode)} onChange={() => changed(true)}><fieldset disabled={pending || Boolean(original.current)}><legend>Record a current authenticated assessment</legend>
            {episode.obligations.map((item, i) => <div key={item.requirement_id} className="review-obligation"><label htmlFor={`${episode.episode_id}-finding-${i}`}>{item.requirement_id}: finding and changed facts</label><input id={`${episode.episode_id}-finding-${i}`} name={`finding-${i}`} required maxLength={256} autoComplete="off"/>
              <label htmlFor={`${episode.episode_id}-result-${i}`}>Requirement result</label><select id={`${episode.episode_id}-result-${i}`} name={`result-${i}`} defaultValue="pending"><option value="pending">Pending review</option><option value="satisfied">Satisfied under the installed rule</option></select>
              <p>Select the exact evidence supporting this requirement:</p>{episode.trigger_refs.map((reference, n) => <label className="radio" key={reference.record_id}><input type="checkbox" name={`evidence-${i}-${n}`}/><span className="hash">{reference.record_id}</span></label>)}</div>)}
            <label htmlFor={`${episode.episode_id}-rationale`}>Current assessment rationale and documented follow-up</label><textarea id={`${episode.episode_id}-rationale`} name="review-rationale" required maxLength={1000} autoComplete="off"/>
            <label className="radio"><input type="checkbox" name="current-assessment" required/>I have reviewed the entire active trigger and obligation set and attest this current assessment.</label>
            <button type="submit">{pending ? 'Recording assessment…' : 'Save current review; keep hold active'}</button></fieldset></form> : null}
          {episode.current_review ? <div className="notice"><h4>Saved authenticated review</h4><p>{localTime(episode.current_review.payload.current_review_at)} · {episode.current_review.payload.result}. {episode.current_review.payload.rationale}</p>
            {episode.clearance_supported && episode.current_review.payload.result === 'satisfied' ? <><p>Explicit clearance closes this episode generation and requests re-entry through assessment. Other active episodes remain held.</p><button disabled={pending || Boolean(original.current)} onClick={() => void submit(`${url}/live-holds/${encodeURIComponent(episode.episode_id)}/clearance`, { ...current(episode), review_id: episode.current_review?.payload.review_id, review_sha256: episode.current_review?.payload_sha256 })}>Clear this episode and re-enter assessment</button></> : <p>Pending or unsupported review cannot clear the hold.</p>}</div> : null}
        </article>;
      }) : <p>No independent live episode is active. Ordinary eligibility and other clinical holds are checked separately.</p>}
      {evidence ? <details open><summary>Selected evidence · original archived source</summary><pre className="source-json">{JSON.stringify(evidence, null, 2)}</pre></details> : null}
      {holds.available_triggers.length ? <div><h3>Record a configured synthetic concern</h3><p>This fixture demonstrates authenticated hold entry independently of a refit. Select an explicitly installed source package.</p><label htmlFor="configured-concern">Authorized source concern · none preselected</label><select id="configured-concern" value={entry} onChange={event => setEntry(event.target.value)}><option value="">Choose a configured concern</option>{holds.available_triggers.map((trigger, i) => <option key={i} value={String(i)}>{trigger.label} · source {i + 1}</option>)}</select><button disabled={!entry || pending || Boolean(original.current)} onClick={() => { if (entry) void submit(`${url}/live-holds`, holds.available_triggers[Number(entry)].command); }}>Record selected concern and hold</button></div> : null}
    </>}
  </section>;
}
