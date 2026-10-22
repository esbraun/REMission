"""One authorized existing8780 service replacement; never claim, fit or ingest."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
import urllib.request

from audit_pa3_native_readiness import SERVICE, GENERATOR, PREFIX, TARGET_SOURCE, CONTAINER_FORMAT, SQL_AUDIT
from capture import run

ROOT = Path('artifacts/pa3/service-maintenance-r1-9e97')
PRIVATE = Path('artifacts/pa3/private-maintenance-r1-9e97').resolve()
OLD = PREFIX + '-service-pre-pa3-4a'
IMAGE = 'sha256:bad33f377d97f52572e182d0973b1f1f56dbc3f1c413de48f20b0458e0906fb7'
COMMON = ['--cpus','2','--memory','2g','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges','--tmpfs','/tmp:rw,noexec,nosuid,size=128m','--user','10001:10001']
EXTRA_FORMAT = '{"WorkingDir":{{json .Config.WorkingDir}},"Cmd":{{json .Config.Cmd}},"Entrypoint":{{json (index .Config "Entrypoint")}},"TaskLabel":{{json (index .Config.Labels "remission.task")}}}'


def save(name, value):
    (ROOT / name).write_text(json.dumps(value, sort_keys=True, indent=2)+'\n', encoding='utf-8')


def command(argv, timeout=60):
    result, metadata = run(argv, ROOT/'commands', timeout_seconds=timeout)
    if result.returncode:
        raise RuntimeError('bounded command failed; see retained stderr '+metadata['streams']['stderr']['path'])
    return result.stdout


def state(name):
    return json.loads(command(['docker','inspect',name,'--format',CONTAINER_FORMAT]))


def database(name):
    return json.loads(command(['docker','exec',name,'python','-c',SQL_AUDIT]))


def equal_database(before, after):
    for key in ['schema_versions','database_control','protected_tables','queue','running','attempt','receipt_identities','panel']:
        assert before[key] == after[key], 'database identity difference: '+key
    for key in ['database','lock']:
        for field in ['device','inode','uid','gid']:
            assert before['file_identities'][key][field] == after['file_identities'][key][field]
    assert after['query_only'] == 1 and after['total_changes'] == 0
    assert all(after['attempt_checks'].values())


def private_env(name):
    # Never route this private read through capture.run or print/error streams.
    result = subprocess.run(['docker','inspect',name,'--format','{{json .Config.Env}}'],capture_output=True)
    if result.returncode:
        raise RuntimeError('private environment read failed; no streams persisted')
    return json.loads(result.stdout)


def env_identity(values):
    return {'count':len(values),'sha256':hashlib.sha256(json.dumps(values,separators=(',',':')).encode()).hexdigest()}


def health():
    with urllib.request.urlopen('http://127.0.0.1:8780/health',timeout=3) as response:
        return json.load(response)


def main():
    ROOT.mkdir(parents=True,exist_ok=False)
    assert PRIVATE.is_dir(), 'private ACL-protected backup directory must be prepared first'
    assert subprocess.check_output(['git','rev-parse','HEAD']).decode().strip() == '9e97f36ca01ab94c3bd9474e1be7310555e907c6'
    before = database(SERVICE)
    reference = json.loads(Path('docs/implementation/evidence/pa3-dispatcher-repair-20261022/readiness-protected-database-snapshot.json').read_text())
    equal_database(reference,before)
    save('pre-database.json',before)
    original = state(SERVICE); generator = state(GENERATOR)
    extra = json.loads(command(['docker','inspect',SERVICE,'--format',EXTRA_FORMAT]))
    save('pre-states.json',{'service':original,'generator':generator,'service_launch':extra})
    assert original['Image'] == 'sha256:35910f5f5d1aa579367a60bf0a6264843b6fca68a8699369c6b7e4a1b863e93e'
    assert generator['Image'] == 'sha256:5d546abd1448e46d5d45ac4a3d98c31899631f968f93d21b163797ff0674ded9'
    assert original['State']['Running'] and generator['State']['Running']
    assert original['User']=='10001:10001' and original['Memory']==2147483648 and original['NanoCpus']==2000000000
    assert original['ReadonlyRootfs'] and original['CapDrop']==['ALL'] and original['SecurityOpt']==['no-new-privileges']
    assert original['Tmpfs']=={'/tmp':'rw,noexec,nosuid,size=128m'} and original['RestartPolicy']=={'Name':'no','MaximumRetryCount':0}
    assert list(original['Networks'])==[PREFIX+'-app']
    assert original['Ports']=={'8765/tcp':[{'HostIp':'127.0.0.1','HostPort':'8780'}]}
    expected_mounts={('/data',PREFIX+'-database',True),('/exports',PREFIX+'-exports',True),('/fixtures',PREFIX+'-fixtures',False)}
    assert {(m['Destination'],m['Name'],m['RW']) for m in original['Mounts']}==expected_mounts
    assert extra['TaskLabel']==PREFIX
    active=command(['docker','ps','-q','--filter','volume='+PREFIX+'-database']).decode().split()
    assert active==[original['Id'][:12]], 'unrelated active database consumer'
    workers=command(['docker','ps','-q','--filter','label=remission.analysis='+PREFIX]).decode().split()
    assert not workers
    assert not command(['docker','ps','-aq','--filter','name=^/'+OLD+'$']).strip()
    assert not Path('artifacts/pa3/app-native-4a').exists()
    values=private_env(SERVICE)
    assert len({v.split('=',1)[0] for v in values})==len(values)
    replacement=[v if not v.startswith('REMISSION_SOURCE_COMMIT=') else 'REMISSION_SOURCE_COMMIT='+TARGET_SOURCE for v in values]
    assert sum(v.startswith('REMISSION_SOURCE_COMMIT=') for v in replacement)==1
    assert all('\n' not in v and '\r' not in v for v in replacement)
    save('environment-identity.json',{'before':env_identity(values),'authorized_after':env_identity(replacement),'only_public_source_override':True,'values_never_captured':True})
    save('pre-health.json',health())
    envfile=PRIVATE/'replacement.env'
    envfile.write_text('\n'.join(replacement)+'\n',encoding='utf-8')
    stopped=False; renamed=False; created=False
    try:
        command(['docker','stop','--time','10',SERVICE],timeout=30)
        stopped=True
        stopped_state=state(SERVICE); save('old-stopped-state.json',stopped_state)
        assert not stopped_state['State']['Running'] and stopped_state['State']['ExitCode']==0 and not stopped_state['State']['OOMKilled']
        print(json.dumps({'actual_step':'old_service_stopped','container':original['Id'],'retained_name_pending':OLD}),flush=True)
        assert not command(['docker','ps','-q','--filter','volume='+PREFIX+'-database']).strip()
        # SQLite Online Backup API reads committed WAL; never copy a raw live DB.
        backup_code = '''import sqlite3,pathlib,hashlib,json
source=sqlite3.connect('file:/data/remission.sqlite?mode=ro',uri=True);source.execute('PRAGMA query_only=ON')
destination=pathlib.Path('/backup/remission-pre-pa3.sqlite');assert not destination.exists()
target=sqlite3.connect(destination);source.backup(target);target.close()
assert source.total_changes==0 and source.execute('PRAGMA query_only').fetchone()[0]==1
source.close()
backup=sqlite3.connect('file:'+str(destination)+'?mode=ro',uri=True);backup.execute('PRAGMA query_only=ON')
assert backup.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
tables={}
def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False)
def sha(v):return hashlib.sha256(canonical(v).encode()).hexdigest()
backup.row_factory=sqlite3.Row
for row in backup.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall():
 name=row[0];records=[]
 for record in backup.execute('SELECT * FROM "'+name.replace('"','""')+'"'):
  records.append(sha({k:({'blob_bytes':len(record[k]),'blob_sha256':hashlib.sha256(record[k]).hexdigest()} if isinstance(record[k],bytes) else record[k]) for k in record.keys()}))
 tables[name]={'rows':len(records),'rows_sha256':sha(sorted(records))}
backup.close();print(canonical({'method':'SQLite Online Backup API from mode=ro/query_only source; committed WAL included','integrity_check':'ok','bytes':destination.stat().st_size,'sha256':hashlib.sha256(destination.read_bytes()).hexdigest(),'tables':tables}))'''
        backup_name=PREFIX+'-pa3-backup-r1-9e97'
        # A writable volume is needed for SQLite WAL shared-memory bookkeeping;
        # the source connection itself remains URI mode=ro/query_only, no SQL writes.
        backup=json.loads(command(['docker','run','--name',backup_name,'--network','none',*COMMON,'--mount','type=volume,source='+PREFIX+'-database,target=/data','--mount','type=bind,source='+str(PRIVATE)+',target=/backup',IMAGE,'python','-c',backup_code]))
        for table,identity in before['protected_tables'].items():
            assert backup['tables'][table]=={k:identity[k] for k in ['rows','rows_sha256']}
        local_backup=PRIVATE/'remission-pre-pa3.sqlite'
        assert hashlib.sha256(local_backup.read_bytes()).hexdigest()==backup['sha256']
        save('backup-proof.json',backup)
        save('backup-container-state.json',state(backup_name))
        print(json.dumps({'actual_step':'consistent_private_backup_verified','sha256':backup['sha256'],'bytes':backup['bytes']}),flush=True)
        command(['docker','rename',SERVICE,OLD]);renamed=True
        create=['docker','create','--name',SERVICE,'--label','remission.task='+PREFIX,'--network',PREFIX+'-app','--publish','127.0.0.1:8780:8765',*COMMON,'--restart','no','--workdir',extra['WorkingDir']]
        for mount in original['Mounts']:
            create += ['--mount','type=volume,source='+mount['Name']+',target='+mount['Destination']+(',readonly' if not mount['RW'] else '')]
        create += ['--env-file',str(envfile),IMAGE]
        create += extra['Cmd'] or []
        new_id=command(create).decode().strip();created=True
        envfile.unlink()
        command(['docker','start',SERVICE]); print(json.dumps({'actual_step':'replacement_started','container':new_id,'image':IMAGE}),flush=True)
        deadline=time.monotonic()+25
        while True:
            try:
                current_health=health()
                assert current_health['capability']=='LIVE-HOLD-01/1.0.0'
                break
            except (OSError,ValueError,AssertionError):
                if time.monotonic()>deadline:raise RuntimeError('replacement health deadline') from None
                time.sleep(.2)
        current=state(SERVICE); current_generator=state(GENERATOR)
        save('post-states.json',{'service':current,'generator':current_generator,'retained_old':state(OLD)})
        assert current['Image']==IMAGE and current['State']['Running']
        for key in ['User','Mounts','Memory','NanoCpus','ReadonlyRootfs','CapDrop','SecurityOpt','Tmpfs','RestartPolicy','Ports']:
            assert original[key]==current[key], 'replacement setting difference: '+key
        assert list(current['Networks'])==list(original['Networks'])
        assert current_generator==generator, 'generator state changed'
        assert private_env(SERVICE)==replacement
        current_extra=json.loads(command(['docker','inspect',SERVICE,'--format',EXTRA_FORMAT]))
        assert current_extra==extra
        save('post-launch-selected.json',current_extra)
        help_bytes=command(['docker','exec',SERVICE,'python','-m','services.foundation.analysis_cli','--help'])
        assert b'bind-execution' in help_bytes
        probe="import pathlib,hashlib,json; paths=['services/foundation/analysis.py','services/foundation/analysis_cli.py','contracts/domain/borrow_runtime.py'];print(json.dumps({p:hashlib.sha256(pathlib.Path('/app',p).read_bytes()).hexdigest() for p in paths},sort_keys=True))"
        actual_files=json.loads(command(['docker','exec',SERVICE,'python','-c',probe]))
        expected_files=json.loads(Path('docs/implementation/evidence/pa3-service-preparation-20261022/source-bindings.json').read_text())
        assert all(actual_files[p]==expected_files[p]['physical']['sha256'] for p in actual_files)
        save('post-copied-files.json',actual_files)
        after=database(SERVICE);equal_database(before,after);save('post-database.json',after)
        save('post-health.json',current_health)
        manifest=json.loads(Path('docs/implementation/evidence/pa3-service-preparation-20261022/deployment-prepared.json').read_text())
        dispatcher=Path('tooling/foundation/analysis_dispatcher.py')
        dispatcher_hash=hashlib.sha256(dispatcher.read_bytes()).hexdigest()
        assert dispatcher_hash=='e4befae1c1b9d1684430f3d375308cee059504799a8087683d117e28766c5e1b'
        manifest.update(status='service_maintained_no_native_job_authorized',service_container_id=new_id,retained_service_container=OLD,retained_service_id=original['Id'],maintenance_observer_commit='9e97f36ca01ab94c3bd9474e1be7310555e907c6',dispatcher={'path':'analysis_dispatcher.py','bytes':dispatcher.stat().st_size,'sha256':dispatcher_hash,'source_commit':'55c07c8ac15d5b55d4d7acdff273570422cd3b01'},backup_sha256=backup['sha256'])
        save('deployment-post-maintenance.json',manifest)
        save('result.json',{'service_replaced':True,'protected_state_equal':True,'authority_same_files':True,'generator_unchanged':True,'private_environment_preserved_except_authorized_public_source':True,'native_claim_fit_ingestion':False})
    except BaseException:
        if created:
            command(['docker','stop','--time','10',SERVICE],timeout=30)
            command(['docker','rename',SERVICE,PREFIX+'-service-failed-pa3-r1-9e97'])
        if renamed:command(['docker','rename',OLD,SERVICE])
        if stopped:command(['docker','start',SERVICE])
        save('rollback.json',{'retained_original_restarted':stopped,'database_not_restored_or_replaced':True,'current':state(SERVICE)})
        raise
    finally:
        if envfile.exists():envfile.unlink()


if __name__=='__main__':
    main()
