"""Prepare public wire-only positive/reject fixtures in the own output mount."""
from datetime import timedelta
from pathlib import Path
import sys

sys.path.insert(0, 'tests/run_contracts')
from observed_v2_fixtures import build, ORIGIN
from test_observed_v2_repair import variant, report_extra

root = Path('/out/public-v2')
build(root, hold=True)
build(root / 'complete-horizon', complete=True)
needle = 'run_id=run_id, partition_id=partition_id, hold_episode_id='
variant(root / 'foreign-hold', hold=True, replace=[(needle, "run_id='foreign-run', partition_id='foreign-partition', hold_episode_id=")])
variant(root / 'day85-report', extra=report_extra(85), cutoff=ORIGIN + timedelta(days=85, hours=10))
print('Prepared public wire fixtures: ordinary positive, complete85 administrative endpoint, foreign hold and day85 report; no producer qualification')
