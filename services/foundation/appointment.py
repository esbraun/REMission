"""Read-only appointment metadata over frozen, accepted summary products.

No posterior is loaded and no model/dispatcher is invoked by this module.
"""
import json
import math
import re

from contracts.domain.analysis import FIXED_SUPPORT_REF, project_history, sha
from contracts.domain.borrowing import parse_input, parse_result
from .store import instant
from .workflow import history


def current_information(db, patient):
    """Use exactly the learner's strict available-at H*, including lineage."""
    try:
        if json.loads(patient['state_json']).get('workflow', {}).get('support_policy') != FIXED_SUPPORT_REF:
            raise ValueError('unsupported current support policy')
        reduced = project_history(history(db, patient['id']).project(instant(patient['cutoff'])))
        value = reduced.model_dump(mode='json')
        return dict(patient_version=patient['version'], cutoff=patient['cutoff'],
            history_sha256=sha(value), provenance_sha256=sha(value['provenance']), reason=None)
    except ValueError:
        # Unsupported current policies/history cannot inherit an old current badge.
        return dict(patient_version=patient['version'], cutoff=patient['cutoff'],
            history_sha256=None, provenance_sha256=None, reason='current_history_unsupported')


def public_summary(value):
    """Numerical seeds and private storage locations stay behind CORE."""
    if isinstance(value, dict):
        return {key: public_summary(item) for key, item in value.items()
            if key not in {'seed', 'seeds', 'fit_seed', 'fit_seeds', 'numerical_seeds',
                'artifact_root', 'posterior', 'posterior_path', 'truth', 'private_parameters'}
                and not key.endswith(('_seed', '_seeds'))}
    if isinstance(value, list):
        return [public_summary(item) for item in value]
    if isinstance(value,str) and re.search(r'(?<!\w)(?:[A-Za-z]:[\\/]|/(?:app|source|tmp|data|home|root|opt|workspace)/)',value):
        return 'Private worker detail withheld; the original is retained with the attempt.'
    return value


def checked_result(row):
    """Validate the stored JSON summary's binding, without reopening private draws.

    Ingest owns file checksum verification. The accepted JSON summary itself is
    the bounded serving artifact; GET never needs a NetCDF/NPZ round-trip.
    """
    try:
        frozen = json.loads(row['request_json'])
        if frozen.get('kind')=='poc_support_s1_input':
            return None, 'cohort_support_is_not_an_individual_visit_effect'
        product = parse_input(row['request_json'])
        if (sha(frozen) != row['input_sha256'] or product.attempt_id != row['job_id']
                or product.request.configuration.model_dump() != json.loads(row['configuration_json'])):
            raise ValueError('input identity')
        if product.kind == 'poc_visit_cohort_input':
            if (product.cohort.manifest.owner_id != row['owner_id']
                    or row['history_sha256'] != product.cohort_sha256
                    or instant(row['cutoff']) != product.cohort.manifest.cutoff):
                raise ValueError('cohort input owner/history/cutoff')
        elif (product.history.patient_id != row['patient_id']
                or row['history_sha256'] != product.history_sha256
                or instant(row['cutoff']) != product.history.cutoff):
            raise ValueError('input patient/history/cutoff')
        if not row['result_json']:
            return None, None
        result = parse_result(row['result_json'])
        if (result.attempt_id != row['job_id'] or result.input_sha256 != row['input_sha256']
                or result.status != row['status'] or result.configuration != product.request.configuration
                or result.estimand != product.request.context.estimand
                or getattr(result, 'source_set_sha256', None) != getattr(product, 'source_set_sha256', None)):
            raise ValueError('result identity')
        if product.kind == 'poc_visit_cohort_input':
            if (result.manifest != product.cohort.manifest
                    or result.manifest_sha256 != product.cohort.manifest_sha256
                    or result.cohort_sha256 != product.cohort_sha256
                    or row['history_sha256'] != product.cohort_sha256):
                raise ValueError('cohort identity')
        elif (result.history_sha256 != product.history_sha256
                or row['history_sha256'] != product.history_sha256
                or result.cutoff != instant(row['cutoff'])):
            raise ValueError('history identity')
        if result.status == 'completed':
            d = result.diagnostics
            names = {a['path'] for a in result.artifacts
                if set(a) == {'path', 'sha256'} and len(a['sha256']) == 64
                and '/' not in a['path'] and '\\' not in a['path']}
            if not d.get('fits') or not d['fits'][-1]['diagnostics'].get('accepted'):
                raise ValueError('fit diagnostics')
            if product.kind == 'poc_visit_cohort_input':
                # Current cohort execution remains closed, including serving.
                from contracts.domain.cohort import require_executable
                require_executable(product)
            else:
                if (not d.get('effect_mcmc', {}).get('accepted')
                        or d.get('integration', {}).get('status') != 'accepted'
                        or 'expected-effect.npz' not in names):
                    raise ValueError('effect diagnostics')
                if product.kind == 'poc_visit_borrow_input':
                    from contracts.domain.borrow_runtime import validate_execution
                    validate_execution(d.get('execution', {}), product,
                        json.loads(row['progress_json']).get('trusted_launch'))
                    if (d.get('bridge_precision', {}).get('status') != 'accepted'
                            or not {'bridge-precision.json', 'bridge-marginals.npz'} <= names):
                        raise ValueError('bridge diagnostics')
        return public_summary(result.model_dump(mode='json')), None
    except (ValueError, KeyError, TypeError, AttributeError, IndexError):
        return None, 'stored_summary_incompatible_or_unaccepted'


def metadata(row, *, stale, reason, result, result_error, current=None):
    accepted = result is not None and result['status'] == 'completed' and result_error is None
    status = 'unavailable' if result_error else ('dated' if stale else 'current') if accepted else (
        'pending' if row['status'] in ('queued', 'running') else
        'failed' if row['status'] == 'failed' else 'unavailable')
    predictive=None
    if accepted:
        raw=result['diagnostics'].get('predictive_endpoint', {})
        intervals=[raw.get('continue_interval'),raw.get('escalate_interval')]
        if all(isinstance(v,list) and len(v)==2 and all(isinstance(n,(int,float))
                and math.isfinite(n) and 0<=n<=28 for n in v) and v[0]<=v[1] for v in intervals):
            predictive=dict(continue_interval=intervals[0],escalate_interval=intervals[1])
    return dict(status=status, summary_available=accepted,
        reason=result_error or reason,
        data_through=row['cutoff'], published_at=row['finished_at'],
        artifact_generated_at=None, generation_time_status='not_recorded',
        current_patient_version=current['patient_version'] if current else None,
        current_history_sha256=current['history_sha256'] if current else None,
        summary_source='validated_stored_result_json',
        predictive_endpoint=predictive,
        supported_pair=['behavioral_continue', 'behavioral_escalate'],
        policy='retain_plans_42_days_fixed_no_prompt')
