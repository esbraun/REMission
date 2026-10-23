"""Pure TA2 reductions over independent filter groups; stdlib only.

These are unresolved evaluator diagnostics, never an admitted TruthResponse.
Particle counts and move variants share replicate keys and are not independent
replicates. Missing or failed rows cannot be replaced by successful filters.
"""
import hashlib
import json
import math
from statistics import fmean, stdev

LEVELS = (1024, 4096, 16384)
GROUPS = 32
SCHEMA = 'ta2-restricted-refinement-v1'
NAMESPACE = 'truth-ta2-development-20261023-v1'
RUNTIME = dict(python='3.13.7', numpy='2.5.4', scipy='1.18.1', pydantic='2.14.1')
IMAGE = 'sha256:ce346feace2ae607ebd574e1bb681d594c9b676c06b56f8ba8d50b858a577faa'
TARGET = dict(truth_kind='observed-Hstar-conditional-mean',
    information_set='strict-reduced-Hstar-v1', privileged_information=False,
    production_truth=False, cutoff='2026-01-15T12:00:00+00:00',
    endpoint_absolute_day=56, recall_absolute_nights=[43, 56],
    retained_visits_absolute_days=[28, 42], outcome='rounded-clipped-ISI-total',
    direction='escalate-minus-continue', horizon_nights=42, support='no_prompt')


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def seed(namespace, patient, history_hash, replicate, process):
    """The unchanged TA1 SHA256 truth_seed recipe, without importing its runtime."""
    key = f'{namespace}|restricted-v1|{patient}|{history_hash}|{replicate}|{process}'
    return int.from_bytes(hashlib.sha256(key.encode()).digest()[:16], 'big')


def workload(patient, history_hash):
    rows = []
    for particles, moves in [*((n, 2) for n in LEVELS), (16384, 4)]:
        for replicate in range(GROUPS):
            rows.append(dict(key=f'n{particles}-m{moves}-r{replicate:02}',
                particles=particles, moves=moves, replicate=replicate,
                slice_limit=128, batches=2, batch_size=10000, seconds=60.0,
                seeds={p:seed(NAMESPACE, patient, history_hash, replicate, p)
                       for p in ('conditioning', 'future')}))
    return rows


def validate_plan(plan, expected):
    """Compare to an independently operator-frozen binding, not payload claims.

    The caller must authenticate expected separately. Rehashing an inconsistent
    payload cannot turn it into the independent expected binding.
    """
    if set(plan) != {'binding', 'workload'} or plan['binding'] != expected:
        raise ValueError('independent expected binding mismatch')
    if (expected['data_schema'] != SCHEMA or expected['namespace'] != NAMESPACE or expected['target'] != TARGET
            or expected['runtime'] != RUNTIME or expected['image'] != IMAGE):
        raise ValueError('unsupported TA2 target/runtime/namespace')
    if plan['workload'] != workload(expected['patient_id'], expected['history_sha256']):
        raise ValueError('frozen workload/settings/seed/order mismatch')


def validate_result(result, item, binding):
    for name, value in binding['target'].items():
        if result.get(name) != value:
            raise ValueError('result target mismatch: '+name)
    for name, value in dict(patient_id=binding['patient_id'],
            history_sha256=binding['history_sha256'], namespace=binding['namespace'],
            prng='NumPy-PCG64', replicate=item['replicate'], seeds=item['seeds']).items():
        if result.get(name) != value:
            raise ValueError('result provenance mismatch: '+name)
    if result.get('status') != 'exploratory_unqualified':
        return False
    if result.get('filter_diagnostics', {}).get('severe_weight_collapse') is not False:
        return False
    batches = result.get('batches', [])
    if (result.get('future_trajectories') != 20000 or len(batches) != 2
            or [(b.get('index'), b.get('trajectories')) for b in batches] != [(0, 10000), (1, 10000)]):
        raise ValueError('incomplete/duplicated batch counts')
    for name in ('estimate', 'within_filter_rollout_mcse'):
        value = result.get(name)
        if type(value) not in (int, float) or not math.isfinite(value):
            raise ValueError('nonfinite/missing filter summary')
    if result['within_filter_rollout_mcse'] < 0:
        raise ValueError('negative rollout uncertainty')
    return True


def paired(low, high):
    if len(low) != GROUPS or len(high) != GROUPS:
        raise ValueError('32 paired independent groups required')
    differences = [b-a for a, b in zip(low, high)]
    mean = fmean(differences)
    se = stdev(differences)/math.sqrt(GROUPS)
    return dict(signed_mean_difference=mean, absolute_mean_difference=abs(mean),
                paired_standard_error=se, bound=abs(mean)+1.96*se)


def reduce_rows(rows, inventory, binding, *, matched_se=None, quadrature_change=None):
    """Require the whole frozen inventory, including explicit pending rows."""
    validate_plan(dict(binding=binding, workload=inventory), binding)
    expected = {item['key']:item for item in inventory}
    actual = {row['key']:row for row in rows}
    if len(expected) != 128 or len(actual) != len(rows) or actual.keys() != expected.keys():
        raise ValueError('missing/duplicate/unexpected workload keys')
    states = ('pending', 'running', 'completed', 'inconclusive', 'failed')
    if any(row['status'] not in states for row in rows):
        raise ValueError('unknown attempt status')
    for key, row in actual.items():
        if row['status'] == 'completed' and not validate_result(row['result'], expected[key], binding):
            raise ValueError('inconclusive/collapsed filter cannot count as completed')
    draw_counts = [row.get('result', {}).get('future_trajectories', 0) for row in rows]
    if any(type(count) is not int or not 0 <= count <= 20000 for count in draw_counts):
        raise ValueError('invalid attempted trajectory count')
    counts = {state:sum(row['status'] == state for row in rows) for state in states}
    report = dict(status='unresolved', production_truth=False, counts=counts,
        independent_replicate_groups=GROUPS, expected_evaluations=128,
        total_recorded_future_trajectories=sum(draw_counts),
        levels=[], refinements=[], moves_stability=None,
        full_conditioning_qualification='unresolved', finite_grid_discrepancy_bound=None,
        matched_estimator_se=matched_se, quadrature_change=quadrature_change)
    complete = {}
    for n, moves in [*((n, 2) for n in LEVELS), (16384, 4)]:
        group = [actual[item['key']] for item in inventory
                 if item['particles'] == n and item['moves'] == moves]
        level = dict(particles=n, moves=moves, status='incomplete',
            completed=sum(r['status'] == 'completed' for r in group), expected=GROUPS)
        if all(row['status'] == 'completed' for row in group):
            means = [row['result']['estimate'] for row in group]
            ses = [row['result']['within_filter_rollout_mcse'] for row in group]
            if any(type(x) not in (int, float) or not math.isfinite(x) for x in means+ses) or min(ses) < 0:
                raise ValueError('invalid completed filter summary')
            if any(row['result'].get('future_trajectories') != 20000 for row in group):
                raise ValueError('completed filter has wrong draw count')
            complete[n, moves] = means
            level.update(status='complete', mean=fmean(means),
                within_filter_mcse=math.sqrt(math.fsum(x*x for x in ses))/GROUPS,
                between_filter_mcse=stdev(means)/math.sqrt(GROUPS),
                future_trajectories=GROUPS*20000)
        report['levels'].append(level)
    for low, high in zip(LEVELS, LEVELS[1:]):
        value = dict(low=low, high=high, status='incomplete')
        if (low, 2) in complete and (high, 2) in complete:
            value.update(status='complete', **paired(complete[low, 2], complete[high, 2]))
        report['refinements'].append(value)
    if (16384, 2) in complete and (16384, 4) in complete:
        report['moves_stability'] = paired(complete[16384, 2], complete[16384, 4])
    if matched_se is not None and (type(matched_se) not in (int, float)
            or not math.isfinite(matched_se) or matched_se < 0):
        raise ValueError('invalid matched estimator SE')
    if quadrature_change is not None and (not math.isfinite(quadrature_change) or quadrature_change < 0):
        raise ValueError('invalid reduced quadrature change')
    epsilon = min(.05, .1*matched_se) if matched_se is not None and matched_se > 0 else .05
    report.update(epsilon=epsilon, budget_basis='matched_positive_SE' if matched_se else 'provisional_absolute_only',
        zero_se_requires_analytic_truth=matched_se == 0, budget_diagnostics=None)
    if len(complete) == 4 and quadrature_change is not None:
        final = report['levels'][2]
        allowances = [quadrature_change, max(r['bound'] for r in report['refinements']),
                      final['within_filter_mcse'], final['between_filter_mcse']]
        report['budget_diagnostics'] = dict(allowances=allowances,
            each_within_quarter=all(v <= epsilon/4 for v in allowances),
            sum_within_epsilon=math.fsum(allowances) <= epsilon,
            moves_within_quarter=report['moves_stability']['bound'] <= epsilon/4)
    return report
