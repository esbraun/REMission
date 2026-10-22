// Execute through official Playwright MCP browser_run_code only, after each
// actual visible navigation/advance in analysis-reconciliation.md. No mocks.
async (page, expectedDay, expectedPatientName) => {
  await page.getByRole('heading', { name: `Simulation · day ${expectedDay} of 84`, exact: true }).waitFor({ state: 'visible' });
  const simulation = page.getByRole('heading', { name: /^Simulation · day \d+ of 84$/ });
  const nextVisit = page.getByRole('button', { name: 'Advance to next 14-day visit', exact: true });
  const advanceOne = page.getByRole('button', { name: 'Advance 1 day', exact: true });
  const patient = page.getByRole('heading', { name: expectedPatientName, exact: true });
  const counts = { simulations: await simulation.count(), nextVisits: await nextVisit.count(), advanceDays: await advanceOne.count(), patients: await patient.count() };
  if (Object.values(counts).some(count => count !== 1)) throw new Error(`Duplicate or stale workspace panels: ${JSON.stringify(counts)}`);
  const context = page.getByRole('region', { name: 'Patient context', exact: true });
  if (!(await context.textContent()).includes(expectedPatientName)) throw new Error('Patient context did not switch');
  return { expectedDay, expectedPatientName, counts, simulation: await simulation.allTextContents() };
}
