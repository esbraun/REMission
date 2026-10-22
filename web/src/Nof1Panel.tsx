import { useEffect, useRef, useState } from 'react';
import type { Nof1, Workspace } from './types';

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
    <p className="unavailable">N0/N1 analysis is unavailable pending accepted methods. No estimated winner or successful fit is supplied.</p>
    {loop?.draws.length ? <ol>{loop.draws.map(draw => <li key={draw.assignment_id}>Block {draw.block} · day {draw.day}: assigned <strong>{draw.option}</strong> at noon, probability 0.5 (both options 0.5), before 20:00 delivery. Washout starts day {draw.washout_starts_day}; next block/review boundary day {draw.next_boundary_day}. <details><summary>Saved assignment provenance</summary><p>{draw.assignment_id} · independent assignment seed, block {draw.block}. Assignment does not assert that the dose was taken.</p></details></li>)}</ol> : <p>No randomized medication has been drawn.</p>}
    {loop?.reviews.length ? <ul>{loop.reviews.map(review => <li key={review.day}>Review day {review.protocol_day}: {review.counts.MED_A} A blocks / {review.counts.MED_B} B blocks · {review.analysis_status.replaceAll('_', ' ')}.</li>)}</ul> : null}
    {loop?.deviations.length ? <div className="warning"><h3>Interrupted protocol</h3><ul>{loop.deviations.map((item, index) => <li key={index}>{item.reasons.join('; ')}</li>)}</ul><p>Past assignments remain saved. The original uninterrupted target is not claimed, and this protocol cannot restart automatically.</p></div> : null}
  </section>;
}

export function Nof1Panel({ workspace, commit, dirty }: { workspace: Workspace; commit: (payload: Record<string, unknown>, key: string) => Promise<void>; dirty: boolean }) {
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
  </section></>;
}
