// Official Playwright MCP rendered regression, actual signed-in copied app.
// Supply an owned patient URL at a stable cutoff; the page session is retained.
async (page, patientUrl, expectedPatientName, expectedDay) => {
  await page.goto(patientUrl);
  const patient = page.getByRole('heading', { name: expectedPatientName, exact: true });
  await patient.waitFor({ state: 'visible' });
  const assertWorkspace = async phase => {
    const counts = {
      patient: await patient.count(),
      simulation: await page.getByRole('heading', { name: `Simulation · day ${expectedDay} of 84`, exact: true }).count(),
      advance: await page.getByRole('button', { name: 'Advance to next 14-day visit', exact: true }).count(),
      panelNavigation: await page.getByRole('link', { name: 'My panel', exact: true }).count()
    };
    if (Object.values(counts).some(value => value !== 1)) throw new Error(`${phase}: workspace lost or duplicated ${JSON.stringify(counts)}`);
    return counts;
  };
  const before = await assertWorkspace('before');
  await page.keyboard.press('Tab');
  const skip = page.getByRole('link', { name: 'Skip to main content', exact: true });
  if (!(await skip.evaluate(element => element === document.activeElement))) throw new Error('First keyboard tab must focus skip link');
  await page.keyboard.press('Enter');
  await page.waitForURL(url => url.hash === '#main');
  const skipped = await assertWorkspace('keyboard skip');
  await page.goBack();
  await page.waitForURL(url => !url.hash);
  const back = await assertWorkspace('same-path hash back');
  await page.goForward();
  await page.waitForURL(url => url.hash === '#main');
  const forward = await assertWorkspace('same-path hash forward');
  return { before, skipped, back, forward };
}
