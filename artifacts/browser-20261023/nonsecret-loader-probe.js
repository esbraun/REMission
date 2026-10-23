async (page) => {
  const probeMarker = 'NONSECRET_LOADER_ECHO_PROBE_20261023';
  return { probe: 'completed', pageTitle: await page.title(), markerLength: probeMarker.length };
}
