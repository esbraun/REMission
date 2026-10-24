"""Trusted live S2 exports and ordinary receipted jobs; SOURCE PREP only.

Caller owns the normal authenticated Store transaction. No Store/scientific
module is imported at module load; scalar s2_data.prepare owns row semantics.
"""
from datetime import datetime, timezone
import json
import secrets
import uuid
from contracts.domain.analysis import canonical, reference, sha
from contracts.domain.boundaries import lineage_heads, visible_records
from contracts.domain.protocol import LAW_REF, SUPPORT_REF
from contracts.domain.support_s2 import HSTAR_REF
from contracts.domain.support_s2_fit import CONFIG_REF as FIT_CONFIG_REF, DEFINITIONS
from contracts.domain.support_s2_app import (CONFIG_REF, POSTERIOR_SCHEMA_REF,
    SEED_POLICY_REF, INITIAL_PROCESS, S2Selection, SelectionIdentity, SelectionReceipt, S2Submission,
    S2Export, S2FitInput, FitSeedRecord, source_projection_sha256, require_executable)


def instant(value):
    at = value if isinstance(value, datetime) else datetime.fromisoformat(value.replace('Z', '+00:00'))
    if at.tzinfo is None or at.utcoffset() is None:
        raise ValueError('aware_S2_time_required')
    return at.astimezone(timezone.utc)


def timestamp(value):
    return instant(value).isoformat()


def public_history(db, patient):
    from .workflow import history
    return history(db, patient)


def public_histories(db, owner, ids, cutoff):
    from .protocol import export_histories
    return export_histories(db, owner, ids, cutoff)


def store_identity(db):
    control = db.execute('SELECT database_instance_id,authority_generation,enabled FROM service_control WHERE singleton=1').fetchone()
    if control is None or not control['enabled']:
        raise ValueError('admitted_enabled_same_Store_required')
    return control['database_instance_id'], control['authority_generation']


def patient_rows(db, owner, members, cutoff, *, advancing=False):
    result = []
    panels, origins = set(), set()
    for member in members:
        row = db.execute('SELECT * FROM patients WHERE id=? AND owner_id=?', (member.patient_id, owner)).fetchone()
        if row is None:
            raise ValueError('owned_live_S2_member_required')
        current = instant(row['cutoff'])
        if ((row['version'] < member.patient_version if advancing else row['version'] != member.patient_version)
                or (current < cutoff if advancing else current != cutoff)):
            raise ValueError('S2_member_version_or_common_cutoff_changed')
        state = json.loads(row['state_json'])
        simulation = state.get('simulation', {})
        workflow = state.get('workflow', {})
        if (simulation.get('law') != LAW_REF or simulation.get('protocol') != SUPPORT_REF
                or simulation.get('law_version') != LAW_REF['id'] or simulation.get('family') != 'support'
                or not simulation.get('panel_id') or simulation.get('research_run_id') is not None
                or state.get('historical_read_only') or state.get('observed_archive')):
            raise ValueError('one_compatible_genuine_live_support_panel_required')
        if (workflow.get('hold_reasons') or workflow.get('clinical') == 'clinical_hold'
                or workflow.get('support_mode') not in ('fixed', 'mrt', 'adaptive')):
            raise ValueError('current_support_authority_held_or_frozen')
        full = public_history(db, row['id'])
        heads = lineage_heads(visible_records(full.records, current, inclusive=True))
        consents = [r for r in heads if r.kind == 'consent' and r.component == 'mrt_bandit']
        consent = max(consents, key=lambda r: (r.available_at, r.recorded_at, r.revision, r.record_id), default=None)
        if consent is None or consent.record_status == 'retracted' or not consent.permits('mrt_bandit', current):
            raise ValueError('current_support_consent_and_oversight_required')
        # Pending reconstruction boundary: do not revive old fitted evidence by
        # hiding a later correction behind the original as-of cutoff hash.
        if advancing and any(r.event_at < cutoff <= r.available_at <= current
                and (r.supersedes is not None or r.record_status == 'retracted') for r in full.records):
            raise ValueError('corrected_fitted_evidence_requires_new_fit; reconstruction_coverage_pending')
        panels.add(simulation['panel_id'])
        origins.add(instant(simulation['origin']))
        result.append(row)
    if len(result) != 12 or len(panels) != 1 or len(origins) != 1:
        raise ValueError('complete_twelve_common_origin_generation_required')
    panel = next(iter(panels))
    complete = db.execute("SELECT id FROM patients WHERE owner_id=? AND json_extract(state_json,'$.simulation.panel_id')=? ORDER BY id", (owner, panel)).fetchall()
    if [r['id'] for r in complete] != [m.patient_id for m in members]:
        raise ValueError('full_predeclared_panel_required_no_peer_reselection')
    return result, panel, next(iter(origins))


def receipt_rows(db, owner, key):
    if not key or len(key) > 128:
        raise ValueError('bounded_original_S2_receipt_key_required')
    return db.execute('SELECT * FROM receipts WHERE owner_id=? AND key=?', (owner, key)).fetchall()


def select(db, current, key, payload, *, now):
    """Explicit day0 support-analysis selection, not a treatment assignment.

    selected_at is the synthetic protocol clock; recorded_at is wall receipt
    time. No outcome inspection, model execution or assignment RNG occurs.
    """
    selection = S2Selection.model_validate_json(canonical(payload))
    payload = selection.model_dump(mode='json')
    prior = receipt_rows(db, current['account_id'], key)
    if prior:
        if len(prior) != 1 or prior[0]['payload_sha256'] != sha(payload) or not prior[0]['scope'].startswith('support-s2-selection:'):
            raise ValueError('S2_selection_original_receipt_conflict')
        saved = SelectionReceipt.model_validate_json(prior[0]['response'])
        if saved.owner_id != current['account_id'] or saved.selection != selection:
            raise ValueError('S2_selection_receipt_owner_or_content_changed')
        return saved.model_dump(mode='json')
    first = db.execute('SELECT * FROM patients WHERE id=? AND owner_id=?', (selection.target_id, current['account_id'])).fetchone()
    if first is None:
        raise ValueError('existing_real_S2_target_required')
    cutoff = instant(first['cutoff'])
    rows, generation, origin = patient_rows(db, current['account_id'], selection.members, cutoff)
    if cutoff != origin or any(json.loads(r['state_json'])['simulation']['day'] != 0 for r in rows):
        raise ValueError('explicit_S2_target_selection_must_be_day0_before_outcomes')
    if any(r.kind == 'support_outcome_link' or r.kind == 'daily_report' and r.event_at > origin
            for patient in rows for r in public_history(db, patient['id']).records):
        raise ValueError('S2_target_selection_cannot_follow_recorded_support_outcomes')
    scope = 'support-s2-selection:' + generation
    if db.execute('SELECT 1 FROM receipts WHERE owner_id=? AND scope=?', (current['account_id'], scope)).fetchone():
        raise ValueError('generation_already_has_immutable_S2_selection')
    store, authority = store_identity(db)
    content = dict(schema_version='s2-app-source-1.0.0', owner_id=current['account_id'], store_id=store,
        authority_generation=authority, generation_id=generation, origin=timestamp(origin),
        selected_at=timestamp(cutoff), recorded_at=timestamp(now), selection=payload)
    content = SelectionIdentity.model_validate_json(canonical(content)).model_dump(mode='json')
    product = SelectionReceipt.model_validate_json(canonical(dict(content,
        reference=reference('poc-support-s2-preoutcome-selection-v1', content))))
    db.execute('INSERT INTO receipts VALUES(?,?,?,?,?,?)', (current['account_id'], current['token_hash'], key,
        scope, sha(payload), product.model_dump_json()))
    return product.model_dump(mode='json')


def selected(db, owner, key):
    rows = receipt_rows(db, owner, key)
    if len(rows) != 1:
        raise ValueError('unknown_S2_selection_receipt_reconcile_original_key')
    saved = SelectionReceipt.model_validate_json(rows[0]['response'])
    if (saved.owner_id != owner or rows[0]['scope'] != 'support-s2-selection:' + saved.generation_id
            or rows[0]['payload_sha256'] != sha(saved.selection.model_dump(mode='json'))
            or (saved.store_id, saved.authority_generation) != store_identity(db)):
        raise ValueError('S2_selection_custody_or_Store_authority_changed')
    return saved


def export(db, owner, selection_key, members, cutoff, *, source_commit, advancing=False):
    """Owned same-Store metadata and original rows; never creates seeds/jobs."""
    from methods.support.s2_data import prepare as prepare_rows
    from contracts.domain.support_s2_app import MemberVersion
    members = tuple(MemberVersion.model_validate(m) for m in members)
    saved = selected(db, owner, selection_key)
    if [m.patient_id for m in members] != [m.patient_id for m in saved.selection.members]:
        raise ValueError('S2_membership_changed_since_preoutcome_selection')
    cutoff = instant(cutoff)
    rows, generation, origin = patient_rows(db, owner, members, cutoff, advancing=advancing)
    if generation != saved.generation_id or origin != saved.origin:
        raise ValueError('S2_generation_or_origin_changed')
    histories = tuple(public_histories(db, owner, [m.patient_id for m in members], cutoff))
    bindings = []
    for history, member in zip(histories, members):
        activations = [r for r in history.records if r.kind == 'protocol_snapshot' and r.family == 'support']
        if len(activations) != 1:
            raise ValueError('one_frozen_support_activation_required; reactivation_coverage_pending')
        activation = activations[0]
        bindings.append(dict(patient_id=member.patient_id, patient_version=member.patient_version,
            history_sha256=sha(history.model_dump(mode='json')),
            revisions_sha256=sha([r.model_dump(mode='json') for r in sorted(history.provenance, key=lambda r: r.record_id)]),
            source_projection_sha256=source_projection_sha256(history),
            activation_ref=dict(record_id=activation.record_id, projection_sha256=sha(activation.model_dump(mode='json')))))
    provenance = dict(schema_version='s2-fit-source-1.0.0', purpose='EST-POLICY:poc-support-refresh-v1', synthetic=True,
        owner_id=owner, store_id=saved.store_id, generation_id=generation, cohort_id=saved.selection.cohort_id,
        export_id='s2-export-' + sha(dict(selection=saved.reference.model_dump(), cutoff=timestamp(cutoff), members=bindings))[:32],
        source_commit=source_commit, target_id=saved.selection.target_id, origin=timestamp(origin), cutoff=timestamp(cutoff),
        cutoff_day=int((cutoff-origin).total_seconds()/86400), members=bindings,
        membership_sha256=sha(bindings), histories_sha256=sha([h.model_dump(mode='json') for h in histories]),
        law=LAW_REF, protocol=SUPPORT_REF, hstar=HSTAR_REF, configuration=FIT_CONFIG_REF,
        definitions=DEFINITIONS, serving_authority=False)
    from contracts.domain.support_s2_fit import S2FitProvenance
    provenance = S2FitProvenance.model_validate_json(canonical(provenance))
    data = prepare_rows(histories, provenance)
    content = dict(schema_version='s2-app-source-1.0.0', selection=saved.model_dump(mode='json'),
        provenance=provenance.model_dump(mode='json'), histories=[h.model_dump(mode='json') for h in histories],
        counts=[dict(patient_id=m.patient_id, observed=m.observed_counts, missing=m.missing_counts,
            prior_hierarchy_only=m.prior_hierarchy_only) for m in data.members],
        contribution_sha256=data.contribution_sha256, configuration=CONFIG_REF)
    return S2Export.model_validate_json(canonical(dict(content,
        reference=reference('poc-support-s2-trusted-export-v1', content))))


def frozen(row):
    product = S2FitInput.model_validate_json(row['request_json'])
    p = product.export.provenance
    if (row['job_id'] != product.attempt_id or row['patient_id'] != p.target_id or row['owner_id'] != p.owner_id
            or json.loads(row['cohort_json']) != [m.patient_id for m in p.members]
            or row['input_sha256'] != sha(product.model_dump(mode='json'))
            or row['history_sha256'] != p.histories_sha256 or instant(row['cutoff']) != p.cutoff
            or json.loads(row['configuration_json']) != CONFIG_REF):
        raise ValueError('stored_S2_attempt_binding_changed')
    return product


def submission_for(product, selection_key):
    p = product.export.provenance
    return S2Submission.model_validate_json(canonical(dict(schema_version='s2-app-source-1.0.0',
        kind='support_s2_fit_submission', selection_key=selection_key,
        members=[dict(patient_id=m.patient_id, patient_version=m.patient_version) for m in p.members],
        cutoff=timestamp(p.cutoff), approved_export=product.export.reference.model_dump(), configuration=CONFIG_REF)))


def revalidate(db, row, selection_key, *, source_commit):
    product = frozen(row)
    p = product.export.provenance
    current = export(db, row['owner_id'], selection_key,
        [dict(patient_id=m.patient_id, patient_version=m.patient_version) for m in p.members], p.cutoff,
        source_commit=source_commit, advancing=True)
    if current != product.export:
        raise ValueError('S2_fitted_asof_contributions_or_authority_changed')
    return product


def view(row, *, verified=False, reason=None):
    product = frozen(row)
    p = product.export.provenance
    return dict(id=product.attempt_id, kind='support_s2_fit_analysis', patient_id=p.target_id,
        cohort=[m.patient_id for m in p.members], cutoff=timestamp(p.cutoff), status=row['status'], stage=row['stage'],
        configuration=CONFIG_REF, input_sha256=row['input_sha256'], history_sha256=p.histories_sha256,
        stale=not verified, staleness_reason=reason, execution_available=False,
        serving=dict(summary_available=False, saved_summary_available=False, status='unavailable',
            reason='S2_production_execution_and_serving_not_qualified'), result=None)


def submit(db, current, key, payload, *, now, source_commit):
    """Normal mutation transaction/receipt, with enqueue closed before writes."""
    submission = S2Submission.model_validate_json(canonical(payload))
    payload = submission.model_dump(mode='json')
    prior = receipt_rows(db, current['account_id'], key)
    if prior:
        if len(prior) != 1 or prior[0]['scope'] != 'support-s2-fit:' + submission.selection_key or prior[0]['payload_sha256'] != sha(payload):
            raise ValueError('S2_original_submission_receipt_conflict')
        row = db.execute('SELECT * FROM analysis_attempts WHERE job_id=? AND owner_id=?',
            (json.loads(prior[0]['response'])['id'], current['account_id'])).fetchone()
        if row is None:
            raise ValueError('original_S2_attempt_unavailable_no_resubmit')
        return view(row)
    product_export = export(db, current['account_id'], submission.selection_key,
        submission.members, submission.cutoff, source_commit=source_commit)
    if product_export.reference != submission.approved_export:
        raise ValueError('approved_S2_export_changed')
    # Same cohort/cutoff/config has one immutable attempt even when another
    # real target tries to act as FK anchor. Caller holds BEGIN IMMEDIATE.
    for row in db.execute("SELECT * FROM analysis_attempts WHERE owner_id=? AND json_extract(request_json,'$.kind')='poc_support_s2_app_fit_input'", (current['account_id'],)):
        other = frozen(row)
        if (other.export.selection.reference == product_export.selection.reference
                and other.export.provenance.cutoff == product_export.provenance.cutoff
                and other.configuration.model_dump() == CONFIG_REF):
            raise ValueError('one_S2_cohort_cutoff_configuration_attempt_reconcile_original_receipt')
    ids = [m.patient_id for m in product_export.provenance.members]
    for row in db.execute("SELECT job_id,cohort_json FROM analysis_attempts WHERE status IN ('queued','running')"):
        if set(ids).intersection(json.loads(row['cohort_json'])):
            raise ValueError('S2_cohort_member_already_pending')
    require_executable(product_export)
    # Future independently qualified source must reopen the contract gate;
    # merely selecting an unknown kind never reaches a generic worker.
    job = 'analysis-' + uuid.uuid4().hex
    seed_key = dict(namespace='fit', protocol=SUPPORT_REF['id'], scenario=job,
        replicate=secrets.randbelow(2147483647), patient=product_export.provenance.target_id,
        time_index=product_export.provenance.cutoff_day, process=INITIAL_PROCESS)
    seed = FitSeedRecord.model_validate_json(canonical(dict(record_id='fit-seed-' + uuid.uuid4().hex,
        attempt_id=job, owner_id=current['account_id'], created_at=timestamp(now), policy=SEED_POLICY_REF,
        key=seed_key, sampler_seed=int(sha(seed_key)[:8], 16) % 2147483647)))
    product = S2FitInput.model_validate_json(canonical(dict(schema_version='s2-app-source-1.0.0',
        kind='poc_support_s2_app_fit_input', purpose='EST-POLICY:poc-support-refresh-v1', attempt_id=job,
        export=product_export.model_dump(mode='json'), seed_record=seed.model_dump(mode='json'),
        configuration=CONFIG_REF, posterior_schema=POSTERIOR_SCHEMA_REF, executable=False)))
    p = product.export.provenance
    value = product.model_dump(mode='json')
    db.execute('INSERT INTO pending_work VALUES(?,?,?,?)', (job, p.target_id, 'queued', 'S2 fit queued'))
    db.execute('INSERT INTO analysis_attempts(job_id,patient_id,owner_id,previous_attempt,request_json,input_sha256,history_sha256,cutoff,configuration_json,cohort_json,status,stage,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',
        (job, p.target_id, current['account_id'], None, canonical(value), sha(value), p.histories_sha256,
            timestamp(p.cutoff), canonical(CONFIG_REF), canonical(ids), 'queued', 'queued', timestamp(now)))
    response = view(db.execute('SELECT * FROM analysis_attempts WHERE job_id=?', (job,)).fetchone(), verified=True)
    db.execute('INSERT INTO receipts VALUES(?,?,?,?,?,?)', (current['account_id'], current['token_hash'], key,
        'support-s2-fit:' + submission.selection_key, sha(payload), canonical(response)))
    return response


def reconcile(db, owner, key):
    """Unknown remains unknown across sessions; never resubmit implicitly."""
    receipts = receipt_rows(db, owner, key)
    if not receipts:
        return dict(status='unknown', attempt=None)
    if len(receipts) != 1 or not receipts[0]['scope'].startswith('support-s2-fit:'):
        raise ValueError('original_S2_submission_receipt_required')
    row = db.execute('SELECT * FROM analysis_attempts WHERE job_id=? AND owner_id=?',
        (json.loads(receipts[0]['response'])['id'], owner)).fetchone()
    return dict(status='found', attempt=view(row)) if row is not None else dict(status='unknown', attempt=None)


def queued_request(db, *, owner, job, key, submission, source_commit):
    payload = S2Submission.model_validate_json(canonical(submission)).model_dump(mode='json')
    receipts = receipt_rows(db, owner, key)
    if (len(receipts) != 1 or receipts[0]['scope'] != 'support-s2-fit:' + payload['selection_key']
            or receipts[0]['payload_sha256'] != sha(payload) or json.loads(receipts[0]['response']).get('id') != job):
        raise ValueError('exact_S2_original_submission_receipt_required')
    row = db.execute('SELECT * FROM analysis_attempts WHERE owner_id=? AND job_id=?', (owner, job)).fetchone()
    if row is None or row['status'] != 'queued' or row['claim_token'] or row['started_at']:
        raise ValueError('owned_unclaimed_S2_queue_required')
    product = revalidate(db, row, payload['selection_key'], source_commit=source_commit)
    if submission_for(product, payload['selection_key']).model_dump(mode='json') != payload:
        raise ValueError('S2_queued_export_selection_changed')
    active = [dict(r) for r in db.execute("SELECT job_id,status FROM analysis_attempts WHERE status IN ('queued','running') ORDER BY job_id")]
    if active != [dict(job_id=job, status='queued')]:
        raise ValueError('one_exact_reviewed_queued_S2_attempt_required')
    require_executable(product)
    return dict(schema='support-s2-queued-request-v1', attempt_id=job, owner_id=owner,
        input_sha256=row['input_sha256'], input=product.model_dump(mode='json'), submission=payload,
        receipt=dict(key=key, scope=receipts[0]['scope'], payload_sha256=receipts[0]['payload_sha256'],
            response_sha256=sha(json.loads(receipts[0]['response']))), active_attempts=[dict(attempt_id=job, status='queued')])
