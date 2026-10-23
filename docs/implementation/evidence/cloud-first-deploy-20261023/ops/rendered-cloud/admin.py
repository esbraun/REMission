"""Offline administration using the existing service's hash/activation contracts.

Mount this manifest-pinned file read-only into the exact service image. Keep the
service stopped for initialization, provisioning, reset, verification or backup.
No fixture seed, existing database copy, archive, learner or evaluator is used.
"""
import argparse
from datetime import datetime, timezone
import getpass
import hashlib
import json
from pathlib import Path
import re
import sys
import uuid


def read_password(stdin=False):
    if stdin:
        # One pipe/secret descriptor, not an argv/env value or evidence stream.
        password = sys.stdin.readline().removesuffix('\n').removesuffix('\r')
    else:
        if not sys.stdin.isatty():
            raise ValueError('use --password-stdin for an approved secret pipe')
        password = getpass.getpass('New synthetic physician password: ')
        if password != getpass.getpass('Confirm password: '):
            raise ValueError('password_confirmation_mismatch')
    if not 16 <= len(password) <= 256 or password in {
            'Synthetic-Alice-2026!', 'Synthetic-Bob-2026!'}:
        raise ValueError('use a unique 16-256 character password, never a public fixture password')
    return password


def create_account(store, username, display_name, password, hasher):
    if not re.fullmatch(r'[a-z][a-z0-9._-]{2,63}', username):
        raise ValueError('username requires 3-64 lowercase letters, digits, dot, underscore or hyphen')
    if not 1 <= len(display_name) <= 100:
        raise ValueError('display_name requires 1-100 characters')
    encoded = hasher.hash(password)
    with store.transaction(write=True) as db:
        if db.execute('SELECT 1 FROM accounts WHERE username=?', (username,)).fetchone():
            raise ValueError('account_exists_use_reset_password')
        db.execute('INSERT INTO accounts(id,username,display_name,password_hash) VALUES(?,?,?,?)',
                   (str(uuid.uuid4()), username, display_name, encoded))


def initialize(database, bootstrap, deployment):
    """New private synthetic authority with no borrowed archive/source grants."""
    from contracts.service.live_hold import LiveHoldAuthority, ReviewRules
    from services.foundation.cutover import activate_new, bundle_for
    from services.foundation.store import canonical
    # Refuse existing state, including a prior incomplete activation; no reseed.
    if database.exists() or any(bootstrap.iterdir()):
        raise ValueError('initialize_requires_new_empty_database_and_bootstrap')
    service = json.loads(Path('/app/contracts/service/bindings-v1.json').read_bytes())
    runs = json.loads(Path('/app/contracts/runs/bindings-v2.json').read_bytes())
    description = {'kind': 'cloud_simulation_no_archives', 'synthetic': True,
                   'source_commit': deployment['source_commit'],
                   'service_image': deployment['service_image'],
                   'generator_image': deployment['generator_image'],
                   'live_archive_authority_enabled': False}
    identity = hashlib.sha256(canonical(description).encode()).hexdigest()
    def ref(name):
        return dict(id=name, version='1.0.0', sha256=identity)
    authority = LiveHoldAuthority.model_validate(dict(schema_version='1.0.0', contract='LIVE-HOLD-01',
        synthetic=True, authority_id='cloud-simulation-' + uuid.uuid4().hex,
        version=ref('cloud-simulation-no-archives'), service_contract=service['live_hold'],
        schema_binding=service['service_schema_set'], enabled=False,
        observed_binding=runs['observed_representation'], archive_verifier=ref('disabled-archive-verifier'),
        producer=ref('cloud-simulation-no-archives'), source_registry=ref('empty-archive-source-registry'),
        execution='synthetic_service', grants=[], follow_up_amendments=[]))
    rules = ReviewRules.model_validate(dict(schema_version='1.0.0', contract='LIVE-HOLD-01', synthetic=True, rules=[]))
    installed = bundle_for(authority, rules)
    activate_new(database, installed, datetime.now(timezone.utc))
    (bootstrap / 'bundle.json').write_text(installed.model_dump_json(), encoding='utf-8')
    runtime = {'id': 'foundation-qualified-linux-sqlite', 'version': 'Python3.13.7-SQLite3.54.1',
               'sha256': 'ce346feace2ae607ebd574e1bb681d594c9b676c06b56f8ba8d50b858a577faa'}
    (bootstrap / 'runtime.json').write_text(canonical(runtime), encoding='utf-8')
    (bootstrap / 'simulation.json').write_text(canonical(description), encoding='utf-8')
    files = ('bundle.json', 'runtime.json', 'simulation.json')
    checksums = ''.join(hashlib.sha256((bootstrap / name).read_bytes()).hexdigest() + '  ' + name + '\n' for name in files)
    (bootstrap / 'bootstrap.sha256').write_text(checksums, encoding='utf-8')
    for path in bootstrap.iterdir():
        path.chmod(0o444)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['initialize', 'create-account', 'reset-password', 'verify'])
    parser.add_argument('--database', type=Path, default=Path('/data/remission.sqlite'))
    parser.add_argument('--bootstrap', type=Path, default=Path('/fixtures'))
    parser.add_argument('--deployment', type=Path, default=Path('/deployment/deployment.json'))
    parser.add_argument('--username')
    parser.add_argument('--display-name')
    parser.add_argument('--password-stdin', action='store_true')
    args = parser.parse_args()
    if args.command == 'initialize':
        initialize(args.database, args.bootstrap, json.loads(args.deployment.read_bytes()))
    else:
        from contracts.service.live_hold import InstalledBundle
        from services.foundation.store import Store
        installed = InstalledBundle.model_validate_json((args.bootstrap / 'bundle.json').read_bytes())
        store = Store(args.database, installed)
        if args.command != 'verify':
            if not args.username:
                parser.error('--username required')
            password = read_password(args.password_stdin)
            if args.command == 'create-account':
                if not args.display_name:
                    parser.error('--display-name required')
                from services.foundation.app import HASHER
                create_account(store, args.username, args.display_name, password, HASHER)
            else:
                from services.foundation.cli import reset_password
                reset_password(store, args.username, password)
            del password
    # No username, password/hash, cookie, token, database rows or bundle values.
    print(json.dumps({'status': args.command + '_complete', 'synthetic': True}))


if __name__ == '__main__':
    main()
