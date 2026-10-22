import hashlib,json,shutil
from pathlib import Path

roots=[Path('artifacts/pa3/native-maintenance-pre-9e97'),Path('artifacts/pa3/service-maintenance-9e97'),Path('artifacts/pa3/service-maintenance-r1-9e97')]
success=roots[-1]
curated=Path('docs/implementation/evidence/pa3-service-maintenance-20261022')
curated.mkdir(parents=True,exist_ok=False)
def sha(raw):return hashlib.sha256(raw).hexdigest()
def save(path,value):path.write_text(json.dumps(value,sort_keys=True,indent=2)+'\n',encoding='utf-8')
for name in ['maintain_pa3_service_once.py','verify_pa3_continuity_once.py','analysis_dispatcher.py','audit_pa3_native_readiness.py']:
    shutil.copyfile(Path('tooling/foundation')/name,success/name)
helpers={name:{'bytes':(success/name).stat().st_size,'sha256':sha((success/name).read_bytes())} for name in ['maintain_pa3_service_once.py','verify_pa3_continuity_once.py']}
manifest=json.loads((success/'deployment-post-maintenance.json').read_text())
manifest['maintenance_helpers']={'source_state':'exact physical one-off bytes at execution; uncommitted on observer9e97, now frozen for candidate review','files':helpers}
manifest['activation_requires']='independent actual maintenance acceptance, then root explicit ONE native-job authorization and fresh oldest/no-unrelated-work check'
save(success/'deployment-post-maintenance.json',manifest)
rollback={'first_recovery':'Stop and retain replacement; rename original retained container back to canonical name; start original against SAME original files. No database restore or inode replacement.','commands':[['docker','stop','--time','10','remission-poc13-ac8e16e0-service'],['docker','rename','remission-poc13-ac8e16e0-service','remission-poc13-ac8e16e0-service-held-for-recovery'],['docker','rename','remission-poc13-ac8e16e0-service-pre-pa3-4a','remission-poc13-ac8e16e0-service'],['docker','start','remission-poc13-ac8e16e0-service']],'successful_maintenance_rollback_executed':False,'first_failed_attempt_rollback':'Actually restarted same original cdb12d7 container; retained raw rollback.json','private_backup':'ACL current account+SYSTEM; outside HTTP/web/fixtures/exports trees, no backup DB payload in evidence'}
save(success/'rollback-instructions.json',rollback)
save(success/'failure-chronology.json',{'first_maintenance':'clean stop exit0; read-only source volume caused SQLite Online Backup API unable-to-open; zero-byte private destination retained; same original container immediately restarted, no DB restore','repair':'new root/helper/private destination; source volumeRW for SQLite WAL/shm bookkeeping only; source URI mode=ro/query_only with asserted total_changes0; all protected table backup hashes verified','continuity_first_pilot':'uncaptured tool chunk63d41e failed KeyError job_id after successful normal login and history reads; API contract is id. No original raw stream was reconstructed.','continuity_second_pilot':'captured failed equality of service_control after auth; actual only last_receipt_at advanced. Existing Store.transaction/write->live_journal.receive explains authorized auth effect.','continuity_final':'captured PASS, verifies exact single-field clock delta against private backup, monotonicity, all other protected rows and authority equality','private_failed_file':{'bytes':0,'sha256':sha(b'')},'initial_helper_source':'full first-attempt helper bytes not separately archived before repair; actual captured commands and physical source hash in command metadata remain original. Exact final r1 helper bytes frozen.'})
all_commands=[]; raw_roots=[]
for root in roots:
    for path in sorted(root.rglob('*.json')):
        value=json.loads(path.read_text())
        if 'command' in value and 'streams' in value:
            entry={k:v for k,v in value.items() if k!='source_snapshot'}
            entry.update(raw_metadata=str(path).replace('\\','/'),raw_metadata_sha256=sha(path.read_bytes()),source_snapshot_sha256=sha(json.dumps(value.get('source_snapshot',{}),sort_keys=True,separators=(',',':')).encode()))
            all_commands.append(entry)
    if not (root/'raw-manifest.json').exists():
        files={str(p.relative_to(root)).replace('\\','/'):{'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in sorted(root.rglob('*')) if p.is_file()}
        save(root/'raw-manifest.json',{'files':files,'files_count':len(files),'status':'frozen; no more writes'})
    raw_roots.append({'path':str(root).replace('\\','/'),'files':len(list(root.rglob('*')))-sum(p.is_dir() for p in root.rglob('*')),'manifest_sha256':sha((root/'raw-manifest.json').read_bytes())})
    for path in sorted(root.glob('*.json')):
        shutil.copyfile(path,curated/(root.name+'--'+path.name))
for path in sorted(success.glob('*.py')):shutil.copyfile(path,curated/path.name)
for label,folder in [('failed-api','api-control-command'),('passed-api','api-control-command-r1'),('private-acl','private-acl-check')]:
    for path in sorted((success/folder).glob('*')):
        if path.suffix in ['.stdout','.stderr']:shutil.copyfile(path,curated/(label+'--'+path.name))
failed=roots[1]/'commands'/'41dd449cf6f34be7a8cdbffefb350956.stderr'
shutil.copyfile(failed,curated/'first-backup-failure.stderr')
save(curated/'commands-selected-index.json',all_commands)
save(curated/'raw-roots.json',raw_roots)
shutil.copyfile(__file__,curated/'freeze-evidence.py')
files={str(p.relative_to(curated)).replace('\\','/'):{'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in sorted(curated.rglob('*')) if p.is_file()}
save(curated/'curated-manifest.json',{'files':files,'files_count':len(files),'no_private_database_or_environment_values':True})
print(json.dumps({'raw_roots':raw_roots,'curated_files':len(files)+1,'curated_manifest_sha256':sha((curated/'curated-manifest.json').read_bytes())},sort_keys=True))
