/** Minimal owner/target-scoped identity; never store credentials or fit inputs. */
export function identityKey(/** @type {string} */ owner, /** @type {string} */ target) {
  return `remission:nof1-analysis:v1:${encodeURIComponent(owner)}:${encodeURIComponent(target)}`;
}

/** @typedef {{version: 1, owner: string, target: string, purpose: 'N0'|'N1', selected_id: string|null, intent: null|{key: string, purpose: 'N0'|'N1'}}} NIdentity */

export function loadIdentity(/** @type {Pick<Storage, 'getItem'>} */ storage, /** @type {string} */ owner, /** @type {string} */ target) {
  const raw = storage.getItem(identityKey(owner, target));
  /** @type {NIdentity} */
  const empty = { version: 1, owner, target, purpose: 'N1', selected_id: null, intent: null };
  if (raw === null) return empty;
  const value = JSON.parse(raw);
  if (value?.version !== 1 || value.owner !== owner || value.target !== target
      || !['N0', 'N1'].includes(value.purpose)
      || !(value.selected_id === null || typeof value.selected_id === 'string')
      || !(value.intent === null || (typeof value.intent?.key === 'string' && value.intent.key.length > 0
          && value.intent.key.length <= 128 && ['N0', 'N1'].includes(value.intent.purpose)))) {
    throw new Error('Saved N analysis identity is invalid. Resolve saved status before a new submission.');
  }
  return /** @type {NIdentity} */ (value);
}

export function saveIdentity(/** @type {Pick<Storage, 'setItem'>} */ storage, /** @type {NIdentity} */ value) {
  storage.setItem(identityKey(value.owner, value.target), JSON.stringify(value));
}

/** Found receipt must match both the stored original purpose and target. */
export function reconcileIdentity(/** @type {NIdentity} */ value,
  /** @type {{status: string, attempt: null|{id: string, target_id: string, purpose: 'N0'|'N1'}}} */ receipt) {
  if (receipt.status === 'unknown' && receipt.attempt === null) return value;
  if (receipt.status !== 'found' || !receipt.attempt || !value.intent
      || receipt.attempt.target_id !== value.target || receipt.attempt.purpose !== value.intent.purpose) {
    throw new Error('Saved receipt identity differs from the original N submission. Keep the original key.');
  }
  return { ...value, purpose: receipt.attempt.purpose, selected_id: receipt.attempt.id, intent: null };
}
