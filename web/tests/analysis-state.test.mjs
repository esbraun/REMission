import test from 'node:test';
import assert from 'node:assert/strict';
import { analysisMessage, definitiveRejection } from '../src/analysis-state.mjs';

test('interrupted and abstained null-result attempts never claim a learner is working', () => {
  for (const status of ['failed', 'abstained', 'completed']) {
    assert.match(analysisMessage(status), /finished/);
    assert.doesNotMatch(analysisMessage(status), /is working|Waiting/);
  }
  assert.match(analysisMessage('running'), /is working/);
  assert.match(analysisMessage('queued'), /Waiting/);
});

test('refresh after stale-version rejection; preserve original intent for uncertain receipt', () => {
  assert.equal(definitiveRejection({ status: 409 }), true);
  assert.equal(definitiveRejection({ status: 422 }), true);
  for (const error of [new TypeError('Failed to fetch'), { status: 500 }, { status: 503 }, { status: 408 }]) {
    assert.equal(definitiveRejection(error), false);
  }
});
