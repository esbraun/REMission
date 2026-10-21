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

test('delayed logout success and failure cannot notify a reauthenticated same-doctor workspace', async () => {
  for (const fails of [false, true]) {
    const gate = new ContextGate(); gate.activate('alice/A/current');
    gate.invalidate(); // sign-out immediately clears local identity
    let resolve, reject;
    const logout = new Promise((yes, no) => { resolve = yes; reject = no; });
    let notice = '', error = '', status = 'signing out';
    const completion = gate.notifyAfter(() => logout,
      () => { notice = 'Signed out'; status = 'signed out'; },
      failure => { error = String(failure); status = 'logout failed'; });
    gate.invalidate(); gate.activate('alice/A/current'); // same doctor, new auth generation
    notice = 'New authenticated workspace'; status = 'authenticated';
    if (fails) reject(new Error('delayed logout failure')); else resolve();
    await completion;
    assert.equal(notice, 'New authenticated workspace');
    assert.equal(error, ''); assert.equal(status, 'authenticated');
    // A current-generation completion must still deliver the normal notification.
    await gate.notifyAfter(() => fails ? Promise.reject(new Error('current failure')) : Promise.resolve(),
      () => { notice = 'Signed out'; }, failure => { error = String(failure); });
    assert.equal(fails ? error : notice, fails ? 'Error: current failure' : 'Signed out');
  }
});
