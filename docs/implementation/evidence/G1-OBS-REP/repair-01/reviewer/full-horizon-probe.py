"""Independent complete horizon fixture probe; no producer qualification."""
import sys,json,hashlib
from pathlib import Path
from datetime import datetime,timedelta,timezone
from copy import deepcopy
sys.path.insert(0,'tests/run_contracts')
from contracts.runs.common import canonical,sha256
from contracts.domain.evidence_v2 import exact_ref
from contracts.runs.observed_v2 import ExportAuthorityV2
from contracts.runs.admission_v2 import verify_export_v2

OUT=Path('/out/complete-attempt-002'); OUT.mkdir(exist_ok=False)
ORIGIN=datetime(2026,1,1,tzinfo=timezone.utc)
END=ORIGIN+timedelta(days=85,hours=10)
# Independent fixed-calendar expectation: 85 daily09:00 decisions, next-day07:00 endpoints.
EXPECTED=[{'index':d,'decision_at':(ORIGIN+timedelta(days=d,hours=9)).isoformat(),'assessment_at':(ORIGIN+timedelta(days=d+1,hours=7)).isoformat()} for d in range(85)]
(OUT/'independent-calendar.json').write_bytes(canonical(EXPECTED))
source=Path('tests/run_contracts/observed_v2_fixtures.py').read_text()
prior_records=[];prior_entries=[];prior_identities={};all_artifacts={};stage_refs=[];receipt_refs=[];mechanism_refs=[];decisions=[];links=[]
for day in range(85):
 s=source.replace('records, entries, identities = [], [], {}','records, entries, identities = deepcopy(PRIOR_RECORDS), deepcopy(PRIOR_ENTRIES), deepcopy(PRIOR_IDENTITIES)')
 s=s.replace("        identity = RecordIdentityV2.model_validate_json", "        if kind in ('patient','consent') and records:\n            found = next((r for r in history().records if r.kind == kind),None)\n            if found is not None: return found\n        if version == '1.0.0' and kind not in ('patient','consent') and identifier:\n            identifier += '-day-' + str(DAY)\n        identity = RecordIdentityV2.model_validate_json",1)
 # Preallocated v1 IDs referenced outside add() must match the suffixed actual IDs.
 # Avoid double suffix by spelling them at source and keeping add identity untouched.
 s=s.replace("        if version == '1.0.0' and kind not in ('patient','consent') and identifier:\n            identifier += '-day-' + str(DAY)\n",'')
 for ident in ['support-snapshot','historical-approval','fixed-assignment','offered-delivery','fixture-mechanism','completed-stages','persist-before-draw']:
  s=s.replace("'"+ident+"'",repr(ident+'-day-'+str(day)))
 s=s.replace("'ledger-' + stage",repr('ledger-day-'+str(day)+'-')+' + stage')
 s=s.replace('slots[0]',f'slots[{day}]')
 s=s.replace('decision_index=0,','decision_index=DAY,')
 s=s.replace(', local_date=ORIGIN.date().isoformat()',', local_date=(ORIGIN+timedelta(days=DAY)).date().isoformat()')
 s=s.replace('        raw = canonical(value)\n        artifacts[path]',"        path = 'day-' + str(DAY) + '/' + path\n        raw = canonical(value)\n        artifacts[path]",1)
 # Report on day84 is recorded in horizon and arrives day85, so only its link is delayed.
 if day==83:
  s=s.replace("available_at=(slots[83].assessment_at + timedelta(hours=1, minutes=1)).isoformat()","available_at=(ORIGIN+timedelta(days=85,hours=8,minutes=1)).isoformat()")
  s=s.replace('link_time = slots[83].assessment_at + timedelta(hours=2)','link_time = ORIGIN+timedelta(days=85,hours=9)')
 if day==84:
  lines=s.splitlines();s='\n'.join('    report = None' if line.startswith("    report = add('daily_report'") else line for line in lines)+'\n'
  s=s.replace("reward=dict(status='observed', report_ref=exact_ref(report).model_dump(), field='sleep_quality', unit='quality_points', reason=None, evidence_refs=[], definition_refs=[])","reward=dict(status='undefined', report_ref=None, field='sleep_quality', unit='quality_points', reason='outside_generated_horizon', evidence_refs=[], definition_refs=[bindings['protocol'],bindings['timing']])")
 ns={'DAY':day,'PRIOR_RECORDS':prior_records,'PRIOR_ENTRIES':prior_entries,'PRIOR_IDENTITIES':prior_identities,'deepcopy':deepcopy}
 exec(compile(s,'own-fixture-complete-day-'+str(day),'exec'),ns)
 f=ns['build'](OUT/'wire',cutoff=END)
 prior_records=[r.model_dump(mode='json') for r in f['history'].records];prior_entries=f['entries'];prior_identities=f['identities']
 all_artifacts.update(f['artifacts']);p=f['manifest']['partitions'][0]
 stage_refs+=p['stage_ledgers'];receipt_refs+=p['completion_receipts'];mechanism_refs+=p['mechanisms'];decisions.append(f['decision']);links.append(f['link'])
 if day%10==0:print('built day',day,flush=True)
# Use independent calendar expectations, not derive_slots output, for the assertions.
for expected,d,l in zip(EXPECTED,decisions,links):
 assert d.decision_index==expected['index'] and d.event_at.isoformat()==expected['decision_at']
 assert l.assessment_at.isoformat()==expected['assessment_at'] and d.outcome_window.assessment_at==l.assessment_at
assert len(decisions)==85 and len(links)==85
reports=[r for r in f['history'].records if r.kind=='daily_report']
assert len(reports)==84 and max(r.event_at for r in reports)==ORIGIN+timedelta(days=84,hours=7)
delayed=next(r for r in reports if r.event_at==ORIGIN+timedelta(days=84,hours=7))
assert delayed.recorded_at==ORIGIN+timedelta(days=84,hours=8,minutes=1) and delayed.available_at==ORIGIN+timedelta(days=85,hours=8,minutes=1)
assert links[-1].reward.status=='undefined' and links[-1].reward.reason=='outside_generated_horizon'
coverage=deepcopy(f['coverage'])
coverage.update(status='complete',execution_status='complete',endpoint_status='complete',first_decision_index=0,last_decision_index=84,first_decision_at=EXPECTED[0]['decision_at'],last_decision_at=EXPECTED[-1]['decision_at'])
for row,d,l in zip(coverage['slots'],decisions,links):
 row.update(status='available',endpoint_status='available',decision_ref=exact_ref(d).model_dump(mode='json'),outcome_ref=exact_ref(l).model_dump(mode='json'))
# Fixture authority attests complete fixed schedule and explicit empty stage ledgers.
# This is synthetic hand-authored evidence, never actual producer qualification.
receipt=json.loads(all_artifacts[receipt_refs[-1]['path']])
receipt.update(id='fixture-complete-horizon',process='fixture-horizon-bookkeeping',time_start=ORIGIN.isoformat(),time_end=END.isoformat(),completed_at=END.isoformat(),recorded_at=END.isoformat(),published_at=END.isoformat(),available_at=END.isoformat(),stage_ledgers=[],output_counts={},accepted_configuration=[f['manifest']['bindings']['protocol'],f['manifest']['bindings']['timing']],output_artifacts=[],dependency_manifests=[])
def artifact(id,path,value,role='configuration'):
 raw=canonical(value);all_artifacts[path]=raw
 return dict(id=id,path=path,sha256=sha256(raw),bytes=len(raw),role=role,media_type='application/json')
a=artifact('fixture-complete-horizon','receipts/full-horizon.json',receipt);receipt_refs.append(a)
receipt_ref=dict(id=a['id'],version='2.0.0',sha256=a['sha256'])
coverage.update(completion_receipt=receipt_ref,no_terminal_event_evidence=receipt_ref)
p.update(stage_ledgers=stage_refs,completion_receipts=receipt_refs,mechanisms=mechanism_refs)
p['coverage']=artifact('coverage','coverage/partition.json',coverage)
p['history']=artifact('history','observed/obs2-fixture-run/obs2-partition.json',f['history'].model_dump(mode='json'),'observed')
p['replay']=artifact('replay','replay/obs2-fixture-run/obs2-partition.json',dict(schema_version='2.0.0',synthetic=True,kind='observed_replay_batch',contract_version='2.0.0',run_id='obs2-fixture-run',partition_id='obs2-partition',patient_id='SYN-02',entries=prior_entries),'replay')
m=f['manifest'];m['status']='complete';m['partitions']=[p];raw=canonical(m)
auth=f['authority'];auth['export_sha256']=sha256(raw);t=auth['partitions'][0]
t.update(coverage_sha256=p['coverage']['sha256'],stage_ledger_hashes={a['id']:a['sha256'] for a in stage_refs},completion_receipt_hashes={a['id']:a['sha256'] for a in receipt_refs},mechanism_hashes={a['id']:a['sha256'] for a in mechanism_refs})
for path,data in all_artifacts.items():
 dest=OUT/'wire'/path;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
(OUT/'wire/manifest.json').write_bytes(raw);(OUT/'wire/authority.json').write_bytes(canonical(auth))
admitted,partitions=verify_export_v2(raw,OUT/'wire',ExportAuthorityV2.model_validate_json(canonical(auth)))
print('PASS complete wire: 85 decisions day0..84;85 next-morning link lineages;84 generated reports day1..84; day84 report arrives day85; day85 administrative endpoint undefined;170 independently fixture-attested empty stage ledgers; no actual producer qualification',flush=True)
