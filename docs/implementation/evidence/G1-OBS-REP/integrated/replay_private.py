"""Re-admit immutable independent private day84/day85 wire bytes on the merge."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import tempfile

from contracts.runs.common import Authority, sha256
from contracts.runs.observed_v2 import ExportAuthorityV2
from contracts.runs.private_v2 import AuthorityV2, verify_run_v2, verify_result_v2

OUT = Path(__file__).resolve().parent
manifest = json.loads((OUT / 'ready-manifest.json').read_bytes())
with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    for path, item in manifest['files'].items():
        prefix = 'independent-private-wire/'
        if not path.startswith(prefix): continue
        relative = PurePosixPath(path.removeprefix(prefix))
        assert not relative.is_absolute() and '..' not in relative.parts
        raw = (OUT / 'b' / item['git_blob']).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == item['sha256']
        target = root.joinpath(*relative.parts); target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(raw)
    for day in [84, 85]:
        case = root / ('day'+str(day))
        run_raw = (case / 'run.json').read_bytes(); result_raw = (case / 'result.json').read_bytes()
        authority = AuthorityV2.model_validate_json((case / 'run-authority.json').read_bytes())
        run, _ = verify_run_v2(run_raw, case, authority)
        result_data = json.loads(result_raw)
        public = ExportAuthorityV2.model_validate_json((case / 'export-authority.json').read_bytes())
        evaluator = Authority.model_validate_json((case / 'calibration-authority.json').read_bytes())
        policies = {item['id']: (evaluator, item['sha256']) for item in result_data['calibration']}
        try:
            _, partitions = verify_result_v2(result_raw, case, run, authority, sha256(result_raw),
                    export_authorities={item['id']: public for item in result_data['observed_exports']}, calibration_policies=policies)
        except ValueError as error:
            assert day == 85 and str(error) == 'generated event outside accepted local horizon -14..84', str(error)
            print('PASS: immutable independent private day85 wire rejects for exact horizon reason')
        else:
            assert day == 84 and len(partitions) == 1
            print('PASS: immutable independent private delayed day84 wire admitted; fixture authority only')
