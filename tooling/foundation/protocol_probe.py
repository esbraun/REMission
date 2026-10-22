"""Copied public-only protocol consumer probe. Does not import an estimator."""
import importlib.util
import json
import os
from pathlib import Path
import urllib.error
import urllib.request

from contracts.domain.analysis import sha
from contracts.domain.protocol_request import ProtocolInput,require_executable


def main():
    assert os.getuid()==10002
    assert importlib.util.find_spec('services.generator') is None and not Path('/app/services/generator').exists(),'private source exposed'
    assert importlib.util.find_spec('services.foundation') is None,'service implementation exposed'
    assert not Path('/data/remission.sqlite').exists() and not Path('/var/run/docker.sock').exists()
    mounts=[line.split() for line in Path('/proc/self/mountinfo').read_text().splitlines()]
    assert any(p[4]=='/input' and 'ro' in p[5].split(',') for p in mounts),'public input is not read-only'
    value=ProtocolInput.model_validate_json(Path('/input/input.json').read_bytes())
    text=json.dumps([h.model_dump(mode='json') for h in value.histories])
    assert all(('"'+key+'"') not in text for key in ['function','diary_sleep_minutes','source','raw_sha256','payload_sha256','state_json','simulation','seed','index','truth','replay'])
    try:require_executable(value)
    except ValueError as error:assert 'not executable' in str(error)
    else:raise AssertionError('boundary fixture must not execute')
    network={'reachable':False}
    try:
        with urllib.request.urlopen(os.environ['P1_GENERATOR_URL'],timeout=1) as response:network.update(reachable=True,http_status=response.status)
    except urllib.error.HTTPError as error:network.update(reachable=True,http_status=error.code)
    except (urllib.error.URLError,TimeoutError,ConnectionError) as error:network['denial_type']=type(error).__name__
    print(json.dumps({'generator_reachability':network}),flush=True)
    assert not network['reachable'],'private generator reached'
    print(json.dumps({'status':'passed','purpose':value.purpose,'family':value.family,'input_sha256':sha(value.model_dump(mode='json')),
        'history_sha256':value.history_sha256,'cohort_count':len(value.cohort),'configuration':value.request.configuration.model_dump(),'execution_admitted':False},sort_keys=True))


if __name__=='__main__':main()
