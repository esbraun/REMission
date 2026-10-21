import sys,tempfile
from pathlib import Path
from datetime import timedelta
sys.path.insert(0,'tests/run_contracts')
from contracts.runs.admission_v2 import verify_export_v2
from contracts.runs.observed_v2 import ExportAuthorityV2
from contracts.runs.common import canonical
source=Path('tests/run_contracts/observed_v2_fixtures.py').read_text()
needle='    cutoff = cutoff or ORIGIN + timedelta(days=1, hours=10)'
extra="""    add('daily_report', ORIGIN+timedelta(days=85,hours=7), version='2.0.0', process='diary_report', recorded_at=(ORIGIN+timedelta(days=85,hours=8,minutes=1)).isoformat(), available_at=(ORIGIN+timedelta(days=85,hours=8,minutes=1)).isoformat(), sleep_quality=6.0, function=5.0, adverse_symptoms=[], diary_sleep_minutes=400.0, goals=[], burden=None, missingness='observed')
"""
for name,code in [('positive-no-day85',source),('forbidden-day85-diary',source.replace(needle,extra+needle))]:
 ns={};exec(compile(code,'own-fixture-variant','exec'),ns)
 with tempfile.TemporaryDirectory() as tmp:
  f=ns['build'](Path(tmp),cutoff=ns['ORIGIN']+timedelta(days=85,hours=10))
  m,p=verify_export_v2(f['raw'],Path(tmp),ExportAuthorityV2.model_validate_json(canonical(f['authority'])))
  print(name,'ACCEPTED',[(r.event_at.isoformat(),r.diary_sleep_minutes) for r in p[0][1].records if r.kind=='daily_report'])
