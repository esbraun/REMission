"""TA1 offline day14 estimate. Output is never an admitted TruthResponse.

Invoke with an immutable reduced history, both its raw and canonical hashes,
and explicit patient selection. There is no generation-seed/DB/HTTP input path.
"""
import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import platform
import resource
import time

import numpy as np
import scipy

from contracts.domain.analysis import AnalysisHistory, sha
from methods.truth.restricted import Settings, evaluate


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--history', type=Path, required=True)
    parser.add_argument('--raw-sha256', required=True)
    parser.add_argument('--history-sha256', required=True)
    parser.add_argument('--patient', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--namespace', required=True)
    parser.add_argument('--replicate', type=int, default=0)
    parser.add_argument('--particles', type=int, default=1024)
    parser.add_argument('--moves', type=int, default=2)
    parser.add_argument('--slice-limit', type=int, default=128)
    parser.add_argument('--batches', type=int, default=2)
    parser.add_argument('--seconds', type=float, default=240)
    args = parser.parse_args(argv)
    started = time.monotonic()
    raw = args.history.read_bytes()
    if hashlib.sha256(raw).hexdigest() != args.raw_sha256:
        raise ValueError('immutable reduced history file hash mismatch')
    history = AnalysisHistory.model_validate_json(raw)
    if sha(history.model_dump(mode='json')) != args.history_sha256 or history.patient_id != args.patient:
        raise ValueError('selected patient/canonical Hstar hash mismatch')
    settings = Settings(particles=args.particles, moves=args.moves, slice_limit=args.slice_limit,
                        batches=args.batches, seconds=args.seconds)
    args.output.mkdir(parents=True, exist_ok=False)

    def progress(value):
        (args.output/'progress.json').write_text(json.dumps(value, allow_nan=False, indent=2)+'\n')

    result = evaluate(history, settings, args.namespace, args.replicate, progress)
    result.update(settings=asdict(settings), raw_history_sha256=args.raw_sha256,
                  runtime=dict(python=platform.python_version(), numpy=np.__version__, scipy=scipy.__version__),
                  peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                  cli_seconds=time.monotonic()-started)
    encoded = json.dumps(result, allow_nan=False, indent=2)+'\n'
    (args.output/'result.json').write_text(encoded)
    print(json.dumps(dict(status=result['status'], reason=result['reason'], estimate=result.get('estimate'),
                          elapsed_seconds=result['elapsed_seconds'], result_sha256=hashlib.sha256(encoded.encode()).hexdigest())), flush=True)
    return 0 if result['status'] == 'exploratory_unqualified' else 2


if __name__ == '__main__':
    raise SystemExit(main())
