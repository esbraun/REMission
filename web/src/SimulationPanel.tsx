import { useRef, useState } from 'react';
import type { ProjectionRecord, Simulation, Workspace } from './types';

const label = (value: string) => value.replaceAll('_', ' ');
const date = (value: string) => new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short', timeZone: 'UTC' }).format(new Date(value));

export function PanelGenerator({ generate }: { generate: (seed: number, count: number, key: string, family: string) => Promise<void> }) {
  const [pending, setPending] = useState(false);
  const [failure, setFailure] = useState('');
  const submitted = useRef<{ seed: number; count: number; key: string; family: string } | null>(null);
  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const values = new FormData(event.currentTarget);
    submitted.current ??= { seed: Number(values.get('seed')), count: Number(values.get('count')), key: crypto.randomUUID(), family: String(values.get('family')) };
    setPending(true); setFailure('');
    try { await generate(submitted.current.seed, submitted.current.count, submitted.current.key, submitted.current.family); submitted.current = null; }
    catch (error) { setFailure(String(error)); }
    finally { setPending(false); }
  }
  return <section aria-labelledby="generate-title">
    <h2 id="generate-title">Generate a synthetic panel</h2>
    <p>Create fictional patients and explore your own decisions over 84 simulated days. The seed reproduces patient content and noise on the pinned runtime. Earlier generated patients and their history remain saved.</p>
    <form onSubmit={event => void submit(event)}>
      <label htmlFor="panel-family">Synthetic patient family</label><select id="panel-family" name="family" disabled={pending || Boolean(submitted.current)}><option value="visit">Ordinary behavioral care · v1</option><option value="nof1_med">Fictional N-of-1 medication protocol · v2</option></select>
      <fieldset disabled={pending || Boolean(submitted.current)}><div className="generator-fields"><div><label htmlFor="panel-seed">Panel seed</label><input id="panel-seed" name="seed" type="number" min="0" max="2147483647" step="1" defaultValue="20261021" inputMode="numeric" autoComplete="off" required/></div><div><label htmlFor="panel-count">Patient count · 2–24</label><input id="panel-count" name="count" type="number" min="2" max="24" step="1" defaultValue="12" inputMode="numeric" autoComplete="off" required/></div></div></fieldset>
      <button type="submit" disabled={pending}>{pending ? 'Generating panel…' : submitted.current ? 'Retry original panel request' : 'Generate and load panel'}</button>
    </form>
    {failure ? <p className="error" role="alert">{failure} Retry uses the original seed, count and request key.</p> : null}
  </section>;
}

function dayAt(record: ProjectionRecord, simulation: Simulation) {
  return (new Date(record.event_at).getTime() - new Date(simulation.origin).getTime()) / 86400000;
}

function Trend({ title, maximum, records, simulation, value }: { title: string; maximum: number; records: ProjectionRecord[]; simulation: Simulation; value: (r: ProjectionRecord) => number | null; }) {
  const segments: string[] = [];
  let segment = '';
  const points: { x: number; y: number; id: string }[] = [];
  for (const record of records) {
    const observed = value(record);
    if (observed === null) { if (segment) segments.push(segment); segment = ''; continue; }
    const x = 42 + Math.max(0, dayAt(record, simulation)) / 84 * 620;
    const y = 115 - observed / maximum * 90;
    points.push({ x, y, id: record.record_id });
    segment += `${x},${y} `;
  }
  if (segment) segments.push(segment);
  return <figure className="trend"><figcaption>{title} · 0–{maximum}</figcaption><svg viewBox="0 0 700 150" role="img" aria-label={`${title}. Observed points by simulated day, with missing daily reports left as gaps. Values appear in the observation table.`}><line x1="42" x2="662" y1="115" y2="115" className="chart-axis"/><line x1="42" x2="42" y1="25" y2="115" className="chart-axis"/><text x="18" y="120">0</text><text x="12" y="30">{maximum}</text>{[0, 14, 28, 42, 56, 70, 84].map(day => <text key={day} x={42 + day / 84 * 620} y="138" textAnchor="middle">{day}</text>)}{maximum === 10 ? segments.map((part, index) => <polyline key={index} points={part} fill="none" className="chart-series"/>) : null}{points.map(point => <circle key={point.id} cx={point.x} cy={point.y} r="3.4" className="chart-point"/>)}</svg></figure>;
}

export function SimulationPanel({ workspace, advance, dirty }: { workspace: Workspace; advance: (mode: 'day' | 'visit', key: string) => Promise<void>; dirty: boolean }) {
  const [pending, setPending] = useState(false);
  const [failure, setFailure] = useState('');
  const submitted = useRef<{ mode: 'day' | 'visit'; key: string } | null>(null);
  const simulation = workspace.simulation;
  if (!simulation) return null;
  const reports = workspace.projection.records.filter(r => r.kind === 'daily_report');
  const assessments = workspace.projection.records.filter(r => r.kind === 'isi');
  const deliveries = workspace.projection.records.filter(r => r.kind === 'delivery');
  const missing = reports.filter(r => r.missingness !== 'observed').length;
  const blocked = pending || dirty || simulation.day >= 84 || workspace.snapshot.workflow.hold_reasons.length > 0;
  async function step(mode: 'day' | 'visit') {
    submitted.current ??= { mode, key: crypto.randomUUID() };
    setPending(true); setFailure('');
    try { await advance(submitted.current.mode, submitted.current.key); submitted.current = null; }
    catch (error) { setFailure(String(error)); }
    finally { setPending(false); }
  }
  const lastISI = assessments.at(-1);
  return <section aria-labelledby="simulation-title">
    <p className="eyebrow">Generated synthetic patient · UTC fictional clock</p><h2 id="simulation-title">Simulation · day {simulation.day} of 84</h2>
    <p>Seed {simulation.seed}. Next visit: day {Math.min(84, (Math.floor(simulation.day / 14) + 1) * 14)}. Fixed support: no prompt. Daily reports describe one night; scheduled ISI describes the preceding 14 nights. Neither is a fitted treatment-effect estimate.</p>
    {lastISI ? <p>Latest scheduled ISI: <strong>{lastISI.items?.reduce((a, b) => a + b, 0)}/28</strong> · 14-day recall from {date(lastISI.recall_start!)} to {date(lastISI.recall_end!)} UTC.</p> : null}
    <div className="actions">
      <button disabled={blocked || submitted.current?.mode === 'visit'} onClick={() => void step('day')}>{pending ? 'Advancing…' : submitted.current?.mode === 'day' ? 'Retry original advancement' : 'Advance 1 day'}</button>
      <button className="secondary" disabled={blocked || submitted.current?.mode === 'day'} onClick={() => void step('visit')}>{submitted.current?.mode === 'visit' ? 'Retry original advancement' : 'Advance to next 14-day visit'}</button>
    </div>
    {dirty ? <p role="status">Save or discard your decision draft before advancing.</p> : null}
    {simulation.day >= 84 ? <p role="status">The 84-day demonstration is complete. Observations and saved decisions remain available.</p> : null}
    {failure ? <p role="alert" className="error">{failure} Retry uses the original advancement and request key to resolve its saved status.</p> : null}
    <p>{reports.length - missing} of {reports.length} daily reports observed; {missing} missing. Missing values remain gaps.</p>
    {reports.length ? <><Trend title="Reported sleep quality" maximum={10} records={reports} simulation={simulation} value={r => r.sleep_quality ?? null}/><Trend title="Reported function" maximum={10} records={reports} simulation={simulation} value={r => r.function ?? null}/></> : <p className="empty">No prospective daily reports yet. Confirm a plan and advance time to observe its consequences.</p>}
    <Trend title="Scheduled ISI · lower scores indicate fewer symptoms" maximum={28} records={assessments} simulation={simulation} value={r => r.items?.reduce((a, b) => a + b, 0) ?? null}/>
    <p className="muted">Horizontal axes show simulated days 0–84. ISI points are separate assessments; no continuous daily ISI is implied. Exact values appear in observations below.</p>
    <details><summary>Plan and delivery timeline · {simulation.actions.length} decisions, {deliveries.length} delivery records</summary>
      {simulation.actions.length ? <ol>{simulation.actions.map(action => <li key={action.assignment_id}>Day {action.day}: approved {label(action.option)} at noon; effective 20:00 UTC before the following night. Remains assigned until a later approved change.</li>)}</ol> : <p>No plan is assigned. No treatment is delivered by opening this page.</p>}
      <div className="table-wrap"><table><caption>Actual simulated delivery and adherence, distinct from approval</caption><thead><tr><th scope="col">Delivery time · UTC</th><th scope="col">Assigned plan</th><th scope="col">Actual stage</th><th scope="col">Adherence</th></tr></thead><tbody>{deliveries.map(record => <tr key={record.record_id}><th scope="row">{date(record.event_at)}</th><td>{label(record.option ?? '')}</td><td>{label(record.stage ?? '')}</td><td>{record.adherence === null ? 'Unknown' : record.adherence === 1 ? 'Yes' : 'No'}</td></tr>)}</tbody></table></div>
    </details>
  </section>;
}
