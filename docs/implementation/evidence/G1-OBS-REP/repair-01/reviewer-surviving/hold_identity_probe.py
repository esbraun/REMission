import sys,tempfile
from pathlib import Path
sys.path.insert(0,'tests/run_contracts')
from contracts.runs.admission_v2 import verify_export_v2
from contracts.runs.observed_v2 import ExportAuthorityV2
from contracts.runs.common import canonical
source=Path('tests/run_contracts/observed_v2_fixtures.py').read_text()
needle='run_id=run_id, partition_id=partition_id, hold_episode_id='
assert source.count(needle)==2
for name,code in [('positive',source),('foreign-hold-run-partition',source.replace(needle,"run_id='foreign-run', partition_id='foreign-partition', hold_episode_id="))]:
 ns={};exec(compile(code,'own-fixture-variant','exec'),ns)
 with tempfile.TemporaryDirectory() as tmp:
  f=ns['build'](Path(tmp),hold=True)
  a=ExportAuthorityV2.model_validate_json(canonical(f['authority']))
  m,parts=verify_export_v2(f['raw'],Path(tmp),a)
  bundles=[r for r in parts[0][1].records if r.kind=='hold_transition_bundle']
  print(name,'ACCEPTED',m.run_id,parts[0][0].id,[(b.run_id,b.partition_id) for b in bundles],flush=True)
