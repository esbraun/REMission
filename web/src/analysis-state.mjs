/** Truthful null-result states, including dispatcher interruption before output. */
export function analysisMessage(/** @type {string} */ status) {
  if (status === 'queued') return 'Waiting for the local isolated learner dispatcher.';
  if (status === 'running') return 'The isolated learner is working. You can review and approve ordinary care while analysis runs.';
  return 'This attempt has finished without an accepted effect interval. Its saved failure or abstention remains available; a deliberate new attempt has its own identity.';
}

/** A definitive client rejection did not commit; transport/5xx remains ambiguous. */
export function definitiveRejection(/** @type {unknown} */ error) {
  return typeof error === 'object' && error !== null && 'status' in error
    && typeof error.status === 'number' && error.status >= 400 && error.status < 500 && error.status !== 408;
}
