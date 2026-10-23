"""Bounded offline TA2 driver. Importing this module performs no numerical work.

Only main() loads the unchanged TA1 runtime, after independent frozen binding
checks. Tests inject scalar fixtures; there is no retry/resume/seed search.
"""
import argparse
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import time

from methods.truth.refinement import (RUNTIME, canonical, digest, reduce_rows,
                                      validate_plan, validate_result)


def write_json(path, value, *, exclusive=False):
    raw = canonical(value)
    if exclusive:
        with path.open('xb') as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
    else:
        temporary = path.with_suffix('.tmp')
        with temporary.open('xb') as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)


def memory():
    # Linux process lifetime high-water, including imports and earlier rows.
    import resource
    value = dict(process_lifetime_peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                 process_scope='Linux RUSAGE_SELF lifetime high-water; not per-evaluation delta',
                 container_cgroup_peak_bytes=None)
    path = Path('/sys/fs/cgroup/memory.peak')
    try:
        value['container_cgroup_peak_bytes'] = int(path.read_text().strip())
    except (OSError, ValueError):
        pass
    return value


def run_rows(plan, expected, output, evaluate_one, *, clock=time.monotonic,
             memory_sample=lambda: {}, startup_seconds=None, operation_seconds=1740):
    validate_plan(plan, expected)
    if operation_seconds != 1740:
        raise ValueError('frozen internal operation cap required')
    output = Path(output)
    output.mkdir(exist_ok=False)
    rows_dir = output/'rows'
    rows_dir.mkdir()
    rows = [dict(key=item['key'], status='pending', reason='not_attempted') for item in plan['workload']]
    started = clock()
    deadline = started+operation_seconds
    write_json(output/'inventory.json', rows, exclusive=True)
    stop_reason = None
    for index, item in enumerate(plan['workload']):
        if clock()+item['seconds'] >= deadline:
            stop_reason = 'internal_operation_cap_no_next_evaluation'
            break
        folder = rows_dir/item['key']
        folder.mkdir(exist_ok=False)
        attempt_started = clock()
        row = dict(key=item['key'], status='running', reason='attempt_started', settings=item,
                   operation_elapsed_at_start=attempt_started-started)
        rows[index] = row
        write_json(folder/'attempt.json', row, exclusive=True)
        write_json(output/'inventory.json', rows)

        def progress(value):
            write_json(folder/'progress.json', value)

        try:
            result = evaluate_one(item, progress)
            write_json(folder/'result.json', result, exclusive=True)
            valid = validate_result(result, item, expected)
            row.update(status='completed' if valid else 'inconclusive',
                       reason=result.get('reason'), result=result)
        except Exception as error:
            row.update(status='failed', reason=type(error).__name__+': '+str(error))
            stop_reason = 'unexpected_evaluation_or_binding_failure'
        elapsed = clock()-attempt_started
        row.update(attempt_elapsed_seconds=elapsed, memory=memory_sample())
        if 'result' in row:
            result = row['result']
            conditioning = result.get('conditioning_seconds')
            evaluator = result.get('elapsed_seconds')
            row['stage_seconds'] = dict(conditioning=conditioning,
                future_rollout_and_evaluator_bookkeeping=(max(0, evaluator-conditioning)
                    if evaluator is not None and conditioning is not None else None),
                evaluator_total=evaluator)
        write_json(folder/'outcome.json', row, exclusive=True)
        write_json(output/'inventory.json', rows)
        if stop_reason:
            break
    reduction_started = clock()
    report = reduce_rows(rows, plan['workload'], expected)
    report.update(stop_reason=stop_reason, source_head=expected['source_head'],
        binding_sha256=digest(canonical(expected)), import_and_startup_seconds=startup_seconds,
        operation_elapsed_before_reduction_seconds=reduction_started-started,
        internal_operation_cap_seconds=operation_seconds, memory=memory_sample(),
        timing_scope=('driver wall time; startup covers main validation and numerical imports; '
                      'top-level stdlib imports/container startup excluded; external lifecycle separate'),
        numerical_execution='attempted', root_admission='closed')
    write_json(output/'reduction.json', report, exclusive=True)
    write_json(output/'timing.json', dict(reduction_and_report_write_seconds=clock()-reduction_started,
        driver_total_seconds=clock()-started, memory=memory_sample()), exclusive=True)
    return report


def load_inputs(plan_path, expected_path, expected_hash, history_path, source_root):
    """Actual file seam; raw integrity and independent semantic binding checks."""
    expected_raw = Path(expected_path).read_bytes()
    if digest(expected_raw) != expected_hash:
        raise ValueError('independent expected binding bytes changed')
    expected = json.loads(expected_raw)
    plan = json.loads(Path(plan_path).read_bytes())
    validate_plan(plan, expected)
    raw = Path(history_path).read_bytes()
    if len(raw) != expected['history_bytes'] or digest(raw) != expected['history_raw_sha256']:
        raise ValueError('raw Hstar integrity mismatch')
    history = json.loads(raw)
    if digest(canonical(history)) != expected['history_sha256'] or history['patient_id'] != expected['patient_id']:
        raise ValueError('canonical Hstar/patient mismatch')
    for relative, item in expected['source_files'].items():
        path = Path(source_root)/relative
        source = path.read_bytes()
        if len(source) != item['bytes'] or digest(source) != item['sha256']:
            raise ValueError('frozen source integrity mismatch: '+relative)
    return plan, expected, raw


def main(argv=None):
    started = time.monotonic()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--expected-binding', type=Path, required=True)
    parser.add_argument('--expected-sha256', required=True)
    parser.add_argument('--history', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    plan, expected, raw = load_inputs(args.plan, args.expected_binding, args.expected_sha256,
                                     args.history, Path.cwd())
    runtime = dict(python=platform.python_version(),
        **{p:importlib.metadata.version(p) for p in ('numpy', 'scipy', 'pydantic')})
    if runtime != RUNTIME:
        raise ValueError('actual runtime differs from root-frozen runtime')
    # The only numerical imports are in this explicitly invoked worker path.
    from contracts.domain.analysis import AnalysisHistory
    from methods.truth.restricted import Settings, evaluate
    history = AnalysisHistory.model_validate_json(raw)

    def evaluate_one(item, progress):
        settings = Settings(**{name:item[name] for name in
            ('particles', 'moves', 'slice_limit', 'batches', 'batch_size', 'seconds')})
        return evaluate(history, settings, expected['namespace'], item['replicate'], progress)

    report = run_rows(plan, expected, args.output, evaluate_one, memory_sample=memory,
                      startup_seconds=time.monotonic()-started)
    print(json.dumps(dict(status=report['status'], counts=report['counts']), allow_nan=False), flush=True)
    # Unresolved scientific precision is not a process failure. Partial inventories are.
    return 0 if report['counts']['completed'] == 128 else 2


if __name__ == '__main__':
    raise SystemExit(main())
