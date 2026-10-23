import test from 'node:test';
import assert from 'node:assert/strict';
import { identityKey, loadIdentity, saveIdentity, reconcileIdentity } from '../src/nof1-analysis-state.mjs';

function storage() {
  const values = new Map();
  return { getItem: key => values.get(key) ?? null, setItem: (key, value) => values.set(key, value) };
}

test('N identity survives navigation/reload and isolates owners and target patients', () => {
  const saved = storage();
  const original = { ...loadIdentity(saved, 'alice', 'patient-b'), intent: { key: 'original-command', purpose: 'N0' } };
  saveIdentity(saved, original);
  assert.deepEqual(loadIdentity(saved, 'alice', 'patient-b'), original);
  assert.equal(loadIdentity(saved, 'bob', 'patient-b').intent, null);
  assert.equal(loadIdentity(saved, 'alice', 'patient-a').intent, null);
  assert.equal(JSON.stringify(original).includes('patient_versions'), false);
});

test('unknown receipt retains original intent; found persisted job resolves it', () => {
  const original = { ...loadIdentity(storage(), 'alice', 'b'), intent: { key: 'unknown-transport', purpose: 'N1' } };
  assert.equal(reconcileIdentity(original, { status: 'unknown', attempt: null }), original);
  const found = reconcileIdentity(original, { status: 'found', attempt: { id: 'saved-job', target_id: 'b', purpose: 'N1' } });
  assert.equal(found.selected_id, 'saved-job'); assert.equal(found.intent, null);
  for (const attempt of [{ id: 'wrong-target', target_id: 'a', purpose: 'N1' }, { id: 'wrong-purpose', target_id: 'b', purpose: 'N0' }]) {
    assert.throws(() => reconcileIdentity(original, { status: 'found', attempt }), /differs/);
  }
});

test('corrupt or unavailable identity storage cannot silently permit another fit', () => {
  const saved = storage(); saved.setItem(identityKey('alice', 'b'), '{broken');
  assert.throws(() => loadIdentity(saved, 'alice', 'b'));
  const blocked = { setItem() { throw new Error('storage denied'); } };
  assert.throws(() => saveIdentity(blocked, loadIdentity(storage(), 'alice', 'b')), /storage denied/);
});
