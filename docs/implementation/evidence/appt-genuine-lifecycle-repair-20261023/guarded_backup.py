"""One backup-helper lifecycle adapter; host stdlib, no implicit recovery/retry.

Only execute after the separately reviewed original read/environment/ACL/stop
gates and root GO. Accepted analysis_lifecycle supplies all watchdog mechanics.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

WORKTREE = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(WORKTREE / 'tooling/foundation'))
import analysis_lifecycle as life

SELECTED = '{"Id":{{json .Id}},"Image":{{json .Image}},"User":{{json .Config.User}},"Path":{{json .Path}},"Args":{{json .Args}},"RestartCount":{{json .RestartCount}},"State":{{json .State}},"Memory":{{json .HostConfig.Memory}},"NanoCpus":{{json .HostConfig.NanoCpus}},"ReadonlyRootfs":{{json .HostConfig.ReadonlyRootfs}},"Privileged":{{json .HostConfig.Privileged}},"CapDrop":{{json .HostConfig.CapDrop}},"CapAdd":{{json .HostConfig.CapAdd}},"SecurityOpt":{{json .HostConfig.SecurityOpt}},"Tmpfs":{{json .HostConfig.Tmpfs}},"NetworkMode":{{json .HostConfig.NetworkMode}},"PortBindings":{{json .HostConfig.PortBindings}},"RestartPolicy":{{json .HostConfig.RestartPolicy}},"AutoRemove":{{json .HostConfig.AutoRemove}},"Mounts":{{json .Mounts}}}'


def load(path):
    return json.loads(Path(path).read_bytes())


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def checked_plan(path):
    plan = load(path)
    if Path.cwd().resolve() != WORKTREE:
        raise ValueError('exclusive assigned worktree required')
    for relative, expected in plan['source_sha256'].items():
        if sha(WORKTREE / relative) != expected:
            raise ValueError('frozen source changed: ' + relative)
    return plan


def no_consumers(plan, allowed=()):
    raw = life.command(['docker', 'ps', '--no-trunc', '-q', '--filter',
                        'volume=' + plan['database_volume']], cap=3).stdout.decode().split()
    ids = [life.require_cid(value) for value in raw]
    if len(ids) != len(set(ids)) or set(ids) - set(allowed):
        raise life.StopUnconfirmed('STOP UNCONFIRMED: another active database consumer')
    return ids


def valid_preflight(plan):
    current = load(plan['preflight_path'])
    reference = load(WORKTREE / plan['terminal_reference'])
    for key in ('protected_tables', 'database_control'):
        if current[key] != reference[key]:
            raise ValueError('first read gate mismatch: ' + key)
    if (current['query_only'] != 1 or current['total_changes'] != 0
            or current['queue'] or current['running']
            or current['terminal_attempt']['owner_matches_expected'] is not True
            or current['terminal_attempt']['result_canonical_sha256'] != plan['result_sha256']):
        raise ValueError('first read gate incomplete')
    return current


def backup_audit(value, cid, plan):
    life.checked_state(value, cid)
    expected = dict(Image=plan['old_image'], User='10001:10001',
        Path='python', Args=['-c', plan['backup_source']], Memory=2147483648,
        NanoCpus=2000000000, ReadonlyRootfs=True, Privileged=False,
        CapDrop=['ALL'], CapAdd=None, SecurityOpt=['no-new-privileges'],
        Tmpfs={'/tmp': 'rw,noexec,nosuid,size=128m'}, NetworkMode='none',
        RestartPolicy={'Name': 'no', 'MaximumRetryCount': 0}, AutoRemove=False)
    if value['State']['Status'] != 'created':
        raise ValueError('helper must be created, never previously started')
    for key, item in expected.items():
        if value.get(key) != item or type(value.get(key)) is not type(item):
            raise ValueError('backup prestart mismatch: ' + key)
    if value.get('PortBindings') not in (None, {}):
        raise ValueError('backup must have no published ports')
    mounts = [m for m in value['Mounts'] if m['Type'] != 'tmpfs']
    database = [m for m in mounts if m['Destination'] == '/data']
    private = [m for m in mounts if m['Destination'] == '/backup']
    def normal(path):
        value = path.replace('\\', '/')
        for prefix in ('/run/desktop/mnt/host/', '/host_mnt/'):
            if value.startswith(prefix):
                value = value[len(prefix)] + ':' + value[len(prefix) + 1:]
        return value.lower()
    if (len(mounts) != 2 or len(database) != 1 or len(private) != 1
            or database[0]['Type'] != 'volume' or database[0]['Name'] != plan['database_volume']
            or database[0]['RW'] is not True or private[0]['Type'] != 'bind'
            or private[0]['RW'] is not True
            or normal(private[0]['Source']) != normal(plan['private_root'])):
        raise ValueError('backup original-volume/private-path mismatch')
    for mount in value['Mounts']:
        if mount['Type'] == 'tmpfs' and (mount['Destination'] != '/tmp' or mount['RW'] is not True):
            raise ValueError('unexpected helper tmpfs')


def barrier(plan, folder, *, success=False, allowed=()):
    """Fresh daemon proof AND reaped handles before every subsequent operation."""
    for name in ('backup-failure.json', 'rename-original.json',
                 'create-replacement.json', 'start-replacement.json', 'recovery.json'):
        path = folder / name
        if path.exists() and load(path).get('status', '').startswith('STOP UNCONFIRMED'):
            raise life.StopUnconfirmed('STOP UNCONFIRMED: retained halt; no later transition/recovery')
    created = load(folder / 'created.json')
    cid = life.require_cid(created['cid'])
    evidence = load(folder / 'lifecycle/supervision.json')
    observed = life.checked_state(life.inspect(cid), cid)
    terminal = life.checked_state(evidence.get('terminal'), cid)
    codes = evidence.get('returncodes', {})
    if (observed != terminal or not life.stopped(observed)
            or observed['State']['Status'] not in ('exited', 'dead')
            or evidence.get('cid') != cid or set(codes) != {'attach', 'watchdog'}
            or any(type(code) is not int for code in codes.values())
            or any('reap_error' in event for event in evidence.get('cleanup', []))):
        raise life.StopUnconfirmed('STOP UNCONFIRMED: helper terminal/reap proof incomplete')
    if success:
        if (evidence.get('failure') is not None or any(codes.values())
                or observed['State']['ExitCode'] != 0 or observed['State']['OOMKilled']
                or observed['State']['Status'] != 'exited'):
            raise RuntimeError('backup did not succeed; forward operations forbidden')
        ready = load(folder / 'lifecycle/watchdog-ready.json')
        life.receipt(folder / 'lifecycle/watchdog-terminal.json', cid,
                     ready['nonce'], evidence['deadline'], observed)
        if load(folder / 'backup-result.json').get('passed') is not True:
            raise RuntimeError('verified backup proof missing')
    consumers = no_consumers(plan, allowed)
    return dict(cid=cid, terminal=observed, reaped_returncodes=codes,
                active_database_consumers=consumers)


def run_backup(plan, folder):
    """One create, one literal CID, one prearmed start; never docker run."""
    before = valid_preflight(plan)
    original = life.inspect(plan['original_cid'])
    if (not life.stopped(original) or original['State']['Status'] != 'exited'
            or original['State']['ExitCode'] != 0 or original['State']['OOMKilled']):
        raise ValueError('original service must already be cleanly stopped')
    no_consumers(plan)
    folder.mkdir(exist_ok=False)
    deadline = time.monotonic() + 60
    cid = None
    failure = None
    try:
        created = life.command(plan['backup_create_argv'], deadline=deadline, cap=10)
        cid = life.require_cid(created.stdout.decode().strip())
        life.save(folder / 'created.json', dict(cid=cid, argv=plan['backup_create_argv'], deadline=deadline))
        observed = json.loads(life.command(['docker', 'inspect', '--format', SELECTED, cid],
                                           deadline=deadline, cap=3).stdout)
        life.save(folder / 'prestart.json', observed)
        backup_audit(observed, cid, plan)
        life.supervise(cid, folder / 'lifecycle', deadline)
        barrier(plan, folder)
        proof = load(folder / 'lifecycle/attach.stdout')
        if proof['integrity_check'] != 'ok':
            raise ValueError('backup integrity failed')
        for table, identity in before['protected_tables'].items():
            if proof['tables'][table] != {k: identity[k] for k in ('rows', 'rows_sha256')}:
                raise ValueError('backup protected table mismatch: ' + table)
        private_backup = Path(plan['private_root']) / 'remission-pre-appt.sqlite'
        if private_backup.stat().st_size != proof['bytes'] or sha(private_backup) != proof['sha256']:
            raise ValueError('private backup byte proof mismatch')
        life.save(folder / 'backup-result.json', dict(passed=True, cid=cid, proof=proof))
        barrier(plan, folder, success=True)
    except BaseException as error:
        failure = repr(error)
        # supervise already stops/inspects/reaps the SAME CID on failure. There
        # is no second helper, restart, discovery cleanup, or fallback here.
        life.save(folder / 'backup-failure.json', dict(failure=failure, cid=cid,
            status='STOP UNCONFIRMED' if cid is None or isinstance(error, life.StopUnconfirmed)
                   else 'failed; recovery requires fresh terminal/reap barrier'))
        raise


def forward(plan, folder, step):
    """Only the three existing forward operations, each independently guarded."""
    if step == 'rename-original':
        argv = ['docker', 'rename', plan['original_cid'], plan['retained_service']]
    elif step == 'create-replacement':
        if load(folder / 'rename-original.json').get('passed') is not True:
            raise ValueError('original rename not confirmed')
        argv = plan['replacement_create_argv']
    elif step == 'start-replacement':
        created = load(folder / 'create-replacement.json')
        if created.get('passed') is not True:
            raise life.StopUnconfirmed('replacement create unconfirmed')
        argv = ['docker', 'start', life.require_cid(created['cid'])]
    else:
        raise ValueError('unsupported forward step')
    proof = barrier(plan, folder, success=True)
    life.save(folder / (step + '-reserved.json'), dict(argv=argv, barrier=proof))
    try:
        result = life.command(argv, cap=15)
        output = dict(passed=True, argv=argv, helper_terminal_reaped=True)
        if step == 'create-replacement':
            output['cid'] = life.require_cid(result.stdout.decode().strip())
        life.save(folder / (step + '.json'), output)
    except BaseException as error:
        life.save(folder / (step + '.json'), dict(passed=False, argv=argv,
                  failure=repr(error), status='STOP UNCONFIRMED; no retry'))
        raise
    finally:
        if step == 'create-replacement':
            Path(plan['temporary_envfile']).unlink(missing_ok=True)


def recover_original(plan, folder):
    """Existing conditional recovery, never an unchecked exception restart."""
    life.save(folder / 'recovery-reserved.json', dict(one_attempt=True))
    events = []
    try:
        create_path = folder / 'create-replacement.json'
        cid = None
        if (folder / 'create-replacement-reserved.json').exists():
            # A killed create client cannot prove no daemon-side replacement.
            created = load(create_path)
            if created.get('passed') is not True:
                raise life.StopUnconfirmed('STOP UNCONFIRMED: replacement create lacks literal CID')
            cid = life.require_cid(created['cid'])
        if cid:
            events.append(dict(before_replacement_stop=barrier(plan, folder, allowed=(cid,))))
            events.append(dict(replacement_stop=life.stop_owned(cid)))
            terminal = life.checked_state(life.inspect(cid), cid)
            if not life.stopped(terminal):
                raise life.StopUnconfirmed('STOP UNCONFIRMED: replacement still active')
            events.append(dict(before_failed_rename=barrier(plan, folder)))
            life.command(['docker', 'rename', cid, plan['failed_replacement']], cap=5)
        renamed = folder / 'rename-original.json'
        if (folder / 'rename-original-reserved.json').exists():
            if not renamed.exists() or load(renamed).get('passed') is not True:
                raise life.StopUnconfirmed('STOP UNCONFIRMED: original rename unconfirmed')
            events.append(dict(before_original_rename=barrier(plan, folder)))
            life.command(['docker', 'rename', plan['original_cid'], plan['service']], cap=5)
        events.append(dict(before_original_restart=barrier(plan, folder)))
        original = life.checked_state(life.inspect(plan['original_cid']), plan['original_cid'])
        if not life.stopped(original) or original['State']['Status'] != 'exited':
            raise life.StopUnconfirmed('STOP UNCONFIRMED: original state changed')
        life.command(['docker', 'start', plan['original_cid']], cap=10)
        life.save(folder / 'recovery.json', dict(passed=True, events=events,
                  database_not_restored_or_replaced=True))
    except BaseException as error:
        life.save(folder / 'recovery.json', dict(passed=False, events=events,
                  failure=repr(error), status='STOP UNCONFIRMED; halt, no rename/restart/retry'))
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', required=True, type=Path)
    parser.add_argument('--execute-after-reviewed-preflight', required=True,
                        choices=['backup', 'rename-original', 'create-replacement', 'start-replacement', 'recover-original'])
    args = parser.parse_args()
    plan = checked_plan(args.plan)
    folder = Path(plan['backup_evidence_root'])
    if args.execute_after_reviewed_preflight == 'backup':
        run_backup(plan, folder)
    elif args.execute_after_reviewed_preflight == 'recover-original':
        recover_original(plan, folder)
    else:
        forward(plan, folder, args.execute_after_reviewed_preflight)


if __name__ == '__main__':
    main()
