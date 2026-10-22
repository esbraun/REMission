async (page) => {
  let admitResponse, responseReady;
  const released = new Promise(resolve => { admitResponse = resolve; });
  const ready = new Promise(resolve => { responseReady = resolve; });
  let actualStatus;
  const handler = async route => {
    const actual = await route.fetch();
    actualStatus = actual.status();
    responseReady();
    await released;
    await route.fulfill({ response: actual });
  };
  await page.route('**/api/session', handler);
  try {
    await page.goto('http://127.0.0.1:8771/patients/SYN-02/current');
    await ready;
    if (actualStatus !== 200) throw new Error('Need actual successful authenticated bootstrap response');
    await page.getByText('Checking session…', { exact: true }).waitFor({ state: 'visible' });
    await page.evaluate(() => {
      window.bootstrapPopObserved = false;
      window.addEventListener('popstate', () => { window.bootstrapPopObserved = true; }, { once: true });
      history.pushState({}, '', '/patients/SYN-02/overview');
    });
    await page.goBack();
    await page.waitForFunction(() => window.bootstrapPopObserved === true);
    admitResponse();
    await page.getByRole('heading', { name: 'Sign in to your synthetic panel', exact: true }).waitFor({ state: 'visible' });
    const result = await page.evaluate(() => ({ doctorVisible: document.body.textContent.includes('Dr Alice'), patientVisible: document.body.textContent.includes('Synthetic patient 02'), reviewInputs: document.querySelectorAll('input[name^="finding-"]').length, popObserved: window.bootstrapPopObserved }));
    if (result.doctorVisible || result.patientVisible || result.reviewInputs) throw new Error('Stale bootstrap result crossed invalidated route/identity context');
    return { actualServerStatus: actualStatus, actualResponseWasDelayedNotMocked: true, staleResultDiscarded: true, ...result };
  } finally { admitResponse(); await page.unroute('**/api/session', handler); }
}
