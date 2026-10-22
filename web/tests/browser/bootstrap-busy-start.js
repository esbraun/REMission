// Execute through the official Playwright MCP browser_run_code tool only.
// A real separate process must already hold this deployment's admission flock.
async (page) => {
  await page.addInitScript(() => {
    if (window.bootstrapRegression) return;
    window.bootstrapRegression = { sessions: [] };
    const fetchOriginal = window.fetch;
    window.fetch = async (...args) => {
      const response = await fetchOriginal(...args);
      if (String(args[0]) === '/api/session') window.bootstrapRegression.sessions.push(response.status);
      return response;
    };
  });
  await page.goto('http://127.0.0.1:8771/patients/SYN-02/current');
  await page.getByRole('button', { name: 'Refresh current information', exact: true }).waitFor({ state: 'visible' });
  const before = await page.evaluate(() => ({ statuses: window.bootstrapRegression.sessions, text: document.body.textContent }));
  if (before.statuses.join(',') !== '503' || before.text.includes('Dr Alice')) throw new Error('Bootstrap must refuse under the actual gate without restoring identity');
  // Retrying before RELEASE must remain fail-closed and keep a usable retry.
  await page.getByRole('button', { name: 'Refresh current information', exact: true }).click();
  await page.getByRole('button', { name: 'Refresh current information', exact: true }).waitFor({ state: 'visible' });
  const after = await page.evaluate(() => ({ statuses: window.bootstrapRegression.sessions, text: document.body.textContent }));
  if (after.statuses.join(',') !== '503,503' || after.text.includes('Dr Alice')) throw new Error('Busy bootstrap retry must issue a request and remain unauthenticated');
  return { phase: 'real gate still held', sessionStatuses: after.statuses, refreshVisible: true, identityVisible: false };
}
