"""Controlled server-side expiry for this isolated synthetic browser fixture only.

No browser script/domain mutation and no public expiry or trust bypass endpoint.
The existing service Store gate serializes the administrative test setup. The
request still traverses actual cookie/session expiry validation and CSRF.
"""
from pathlib import Path
import sys
sys.path.insert(0, str(Path.cwd()))
from tooling.foundation.capture import run

code = '''
import json
from services.foundation.configuration import environment_settings
from services.foundation.store import Store
s=environment_settings()
store=Store(s.database,s.installed)
with store.transaction(write=True) as db:
    before=[dict(row) for row in db.execute("SELECT token_hash,expires_at,revoked FROM sessions WHERE account_id='alice' AND revoked=0")]
    active_before=[dict(row) for row in db.execute("SELECT id,generation,status FROM live_hold_episodes ORDER BY id,generation")]
    expired_at=store.clock().timestamp()-1
    count=db.execute("UPDATE sessions SET expires_at=? WHERE account_id='alice' AND revoked=0",(expired_at,)).rowcount
    after=[dict(row) for row in db.execute("SELECT token_hash,expires_at,revoked FROM sessions WHERE account_id='alice' AND revoked=0")]
    active_after=[dict(row) for row in db.execute("SELECT id,generation,status FROM live_hold_episodes ORDER BY id,generation")]
    assert active_before==active_after
print(json.dumps(dict(test_setup='controlled_server_expiry_not_revocation',count=count,before=before,after=after,expired_at=expired_at,episodes_unchanged=True)))
'''
result,metadata=run(['docker','exec','remission-g1-live-hold-20261021-799f2981-service','python','-c',code],Path(__file__).parent/'c')
sys.stdout.buffer.write(result.stdout)
sys.stderr.buffer.write(result.stderr)
print(metadata['exit'])
raise SystemExit(result.returncode)
