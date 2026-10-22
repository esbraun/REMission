// Execute through official Playwright MCP after the same actual holder RELEASE.
// The cookie must still be valid and SYN-02 must already have an active hold.
async (page) => {
  const before = await page.evaluate(() => window.bootstrapRegression.sessions.length);
  await page.getByRole('button', { name: 'Refresh current information', exact: true }).click();
  await page.getByRole('heading', { name: 'Synthetic patient 02', exact: true }).waitFor({ state: 'visible' });
  await page.getByText('Hold remains active.', { exact: true }).first().waitFor({ state: 'visible' });
  const result = await page.evaluate(async () => {
    const workspace = await (await fetch('/api/patients/SYN-02')).json();
    return { statuses: window.bootstrapRegression.sessions, identity: document.querySelector('h1')?.textContent,
      stage: workspace.stage, workflow: workspace.snapshot.workflow, permissions: workspace.permissions,
      findings: [...document.querySelectorAll('input[name^="finding-"]')].map(input => input.value),
      selectedOptions: document.querySelectorAll('input[name="option"]:checked').length };
  });
  if (result.statuses.length !== before + 1 || result.statuses.at(-1) !== 200) throw new Error('Visible refresh must repeat GET /api/session once after RELEASE');
  if (result.stage !== 'ASSIGN-09' || result.workflow.data_readiness !== 'stale' || result.workflow.support_mode !== 'paused' || result.permissions.approve_ordinary || result.selectedOptions || result.findings.some(Boolean)) throw new Error('Recovered identity must show current held/unready state and empty local input');
  return { phase: 'same page recovered without reload or sign-in', ...result };
}
