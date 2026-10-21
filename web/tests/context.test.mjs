import { test } from 'node:test';
import assert from 'node:assert/strict';
import { ContextGate } from '../src/context.mjs';

test('a late response cannot cross patient, task, decision or historical context', async () => {
  const gate = new ContextGate();
  for (const next of ['alice/B/current', 'alice/A/history/decision-2', 'alice/A/current/new-decision']) {
    const old = gate.activate('alice/A/current/decision-1');
    let settle;
    const delayed = new Promise(resolve => { settle = resolve; });
    gate.activate(next); settle({ patient: 'A' });
    await delayed;
    assert.equal(gate.accepts(old), false);
  }
});

test('logout and same-doctor login invalidate every pre-logout response', () => {
  const gate = new ContextGate(); const old = gate.activate('alice/A/current');
  gate.invalidate(); gate.activate('alice/A/current');
  assert.equal(gate.accepts(old), false);
  assert.equal(gate.accepts(gate.capture()), true);
});
