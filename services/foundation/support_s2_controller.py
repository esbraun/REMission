"""Owned support envelope and decision-time controller. No scientific computation.

Called only inside the existing serialized app transaction. The accepted saved
execution gate controls this branch; ordinary simulation and N paths bypass it.
"""
from datetime import timedelta
import hashlib
import json
import uuid
from contracts.domain.analysis import canonical, sha, reference
from contracts.domain.boundaries import lineage_heads, visible_records, validate_approval, validate_assignment
from contracts.domain.entities import Approval, DecisionSnapshot
from contracts.domain.evidence_v2 import exact_ref, projection_hash
from contracts.domain.protocol import SUPPORT_REF
from contracts.domain.support_s2_controller import CONFIG_REF, SavedScalar
from contracts.domain.support_s2_saved import require_executable

VERSIONS = ('version', 'state_version', 'consent_version', 'eligibility_version')
ACTIONS = ('support_prompt', 'no_prompt')


def mask(full, state, at, received_at, *, approved=True):
    """Safety is inclusive/current; feature/operational histories are predecision.

    Prior offered assignments also restrict burden, so an outstanding delivery
    cannot open capacity. Unknown observed closure must refuse at admission.
    """
    heads = lineage_heads(visible_records(full.records, max(at, received_at), inclusive=True))
    consents = [r for r in heads if r.kind == 'consent' and r.component == 'mrt_bandit']
    consent = max(consents, key=lambda r: (r.available_at, r.recorded_at, r.revision, r.record_id), default=None)
    flow = state['workflow']; sim = state['simulation']; loop = sim.get('support_controller', {})
    reasons = []
    if not consent or not consent.permits('mrt_bandit', at): reasons.append('Current support consent and synthetic oversight required')
    if flow['clinical'] == 'clinical_hold' or flow['hold_reasons']: reasons.append('Clinical hold')
    if flow['data_readiness'] != 'ready': reasons.append('Current data review required')
    if any(r.kind == 'intercurrent_event' and r.record_status != 'retracted' and r.event_type in
           ('death', 'rescue', 'fall', 'regimen_change', 'steroid_change', 'discontinuation', 'override') for r in heads):
        reasons.append('Current safety assessment required')
    if approved and (loop.get('status') != 'active' or not loop.get('snapshot_id')): reasons.append('Explicit current support envelope required')
    n = sim.get('nof1', {})
    if approved and n.get('status') in ('stopped', 'completed') and loop.get('nof1_review_identity') != sha(n):
        reasons.append('New explicit support approval required after N review')
    if reasons: return (), reasons
    if (approved and flow['support_mode'] in ('fixed', 'frozen')) or flow['learning'] in ('nof1_block', 'nof1_washout') or n.get('status') == 'active':
        return ('no_prompt',), ['Frozen no-prompt policy']
    if approved and flow['support_mode'] == 'paused': return (), ['Support paused']
    prior = full.as_known_at(at)
    delivered = [r for r in prior if r.kind == 'delivery' and r.option == 'support_prompt' and r.stage == 'delivered']
    offered = [r for r in prior if r.kind == 'support_decision' and r.assignment_id and
               r.probabilities['support_prompt'] > 0 and at-timedelta(days=6) <= r.cutoff < at]
    assignments = {r.record_id: r for r in prior if r.kind == 'assignment'}
    offered_days = {r.cutoff.date() for r in offered if r.assignment_id in assignments and assignments[r.assignment_id].option == 'support_prompt'}
    delivered_days = {r.event_at.date() for r in delivered if at-timedelta(days=6) <= r.event_at < at}
    if len(offered_days | delivered_days) >= 3 or any(at-timedelta(days=1) <= r.event_at < at for r in delivered) or (at-timedelta(days=1)).date() in offered_days:
        return ('no_prompt',), ['Rolling seven-night cap or consecutive-night restriction']
    return ACTIONS, []


def final_distribution(allowed, saved):
    """Finite saved scalar admission precedes clipping; never infer authority."""
    saved = SavedScalar.model_validate(saved)
    if len(set(allowed)) != len(allowed) or not set(allowed) <= set(ACTIONS): raise ValueError('invalid_support_mask')
    if not allowed: return 'unavailable', dict.fromkeys(ACTIONS, 0.), 'current_support_unavailable'
    if len(allowed) == 1:
        if allowed != ('no_prompt',): raise ValueError('unsupported_deterministic_prompt_policy')
        return 'deterministic', dict(support_prompt=0., no_prompt=1.), 'current_mask_no_prompt'
    ready = saved.summary_available and saved.serving_authority and saved.status == 'candidate_ready' and saved.probability is not None
    p = saved.probability if ready else .5
    p = min(.9, max(.1, p)); result = dict(support_prompt=p, no_prompt=1-p)
    if abs(sum(result.values())-1) > 1e-12 or any(not .1-1e-12 <= p <= .9+1e-12 for p in result.values()):
        raise ValueError('infeasible_support_distribution')
    return 'randomized', result, None if ready else (saved.reason or 'saved_prediction_unavailable')


def keyed_uniform(seed):
    raw = hashlib.sha256(canonical(seed).encode()).digest()
    return ((int.from_bytes(raw[:8], 'big') >> 11)+.5)/2**53


def eligibility(db, patient, state, at, received_at):
    from .workflow import _producer_history as history
    from .live_journal import active_episodes
    allowed, reasons = mask(history(db, patient['id']), state, at, received_at,
        approved=state['simulation'].get('support_controller',{}).get('status')=='active')
    if active_episodes(db, patient['id']): allowed, reasons = (), ['Independent clinical hold']
    return [dict(action=a, status='eligible' if a in allowed else 'excluded', reasons=[] if a in allowed else reasons) for a in ACTIONS]


def selected(patient):
    from .simulation import SimulationError
    state = json.loads(patient['state_json']); sim = state.get('simulation', {})
    if (sim.get('family') != 'support' or sim.get('law_version') != 'poc-longitudinal-v2'
            or state.get('historical_read_only') or state.get('observed_archive') or sim.get('research_run_id')):
        raise SimulationError('support_patient_required', 'Select an owned current support simulation patient.')
    return state, sim


def view(db, patient, received_at):
    from .workflow import patient_clock
    state, sim = selected(patient)
    try:
        require_executable()
        from .support_s2_authority import qualification
        qualification(db)
        executable = True
    except ValueError:
        executable = False
    return dict(configuration=CONFIG_REF, execution_available=executable,
        loop=sim.get('support_controller',dict(status='unapproved')),
        **saved_status(db,patient['owner_id'],patient,patient_clock(patient,received_at)))


def saved_status(db, owner, patient, at):
    """Reads saved scalar metadata only. Existing admission remains authoritative."""
    from .support_s2_prediction import read_summary, current_context
    from contracts.domain.support_s2_saved import SavedPredictionInput, INPUT_CAP
    rows = db.execute('SELECT * FROM analysis_attempts WHERE owner_id=? AND patient_id=? AND purpose=? ORDER BY created_at DESC,rowid DESC LIMIT 1',
                      (owner, patient['id'], 'EST-POLICY:poc-support-prediction-v1')).fetchall()
    row = dict(rows[0]) if rows else None
    view = dict(summary_available=False, serving_authority=False, reason='saved_prediction_missing')
    if row:
        if row['status'] != 'completed': view['reason'] = 'saved_prediction_'+row['status']
        elif len(row['request_json'].encode()) > INPUT_CAP: view['reason'] = 'saved_prediction_input_cap'
        else:
            try:
                product = SavedPredictionInput.model_validate_json(row['request_json'])
                p = product.fit.product.initial.export.provenance
                if not product.context.decision.cutoff <= at < p.origin+timedelta(days=p.cutoff_day+14):
                    raise ValueError('saved_prediction_expired')
                context = current_context(db, owner, patient['id'], product.fit)
                if context != product.context: raise ValueError('saved_prediction_stale_current_context')
                view = read_summary(db, owner, row['job_id'], current_context=context, current_fit=product.fit, at=at)
                typed = SavedScalar.model_validate(view)
                if typed.summary_available and (typed.context_reference != context.reference or typed.fit_collection_reference != product.fit.collection_reference):
                    raise ValueError('saved_prediction_identity_mismatch')
            except ValueError as error:
                view = dict(summary_available=False, serving_authority=False, reason=str(error))
    attempt = {k:row[k] for k in ('job_id','status','cutoff','finished_at','failure_reason')} if row else None
    return dict(saved=SavedScalar.model_validate(view).model_dump(mode='json'), attempt=attempt,
                activation_gap='Exact installed fit/image/operation/current-context and interactive completion qualification required')


def transition(db, settings, patient, actor, data, received_at):
    from .simulation import SimulationError
    from .workflow import _producer_history as history, patient_clock, record_header, create_decision
    from .support_s2_authority import producer_persist as persist,producer_gate
    from .live_journal import active_episodes
    state, sim = selected(patient); at = patient_clock(patient, received_at)
    if data.decision_id != patient['current_decision'] or any(getattr(data, 'expected_'+k) != patient[k] for k in VERSIONS):
        raise SimulationError('stale_support', 'Refresh and review current patient, state, consent and eligibility versions.')
    loop = sim.setdefault('support_controller', dict(status='unapproved'))
    full = history(db, patient['id'])
    if data.action in ('consent', 'withdraw'):
        if data.action == 'consent' and data.consent_expires_at is not None and data.consent_expires_at <= at:
            raise SimulationError('expired_support_consent', 'Consent expiry must follow the fictional clock.')
        prior = [r for r in full.records if r.kind == 'consent' and r.lineage_id == 'support-consent-'+patient['id']]
        previous = max(prior, key=lambda r:r.revision, default=None)
        withdrawn = data.action == 'withdraw'
        value = dict(**record_header('support-consent-'+uuid.uuid4().hex, patient['id'], at), kind='consent', component='mrt_bandit',
            consent_version='poc-support-consent-v1', oversight_version='synthetic-engineering-v1', consent_status='withdrawn' if withdrawn else 'active',
            oversight_status='withdrawn' if withdrawn else 'approved_synthetic', effective_at=at.isoformat(),
            expires_at=data.consent_expires_at.isoformat() if data.consent_expires_at else None, withdrawn_at=at.isoformat() if withdrawn else None)
        value.update(lineage_id='support-consent-'+patient['id'], revision=previous.revision+1 if previous else 1,
                     supersedes=previous.record_id if previous else None)
        persist(db, value, received_at); loop['status'] = 'withdrawn' if withdrawn else 'unapproved'
    elif data.action == 'pause': loop['status'] = 'paused'
    else:
        producer_gate(db,patient['id'])
        if sim.get('nof1', {}).get('status') == 'active' or active_episodes(db, patient['id']):
            raise SimulationError('support_frozen', 'Review N freeze or the current independent hold first.')
        allowed, reasons = mask(full, state, at, received_at, approved=False)
        if reasons and allowed != ACTIONS: raise SimulationError('support_not_ready', '; '.join(reasons))
        if not sim['actions'] or sim['actions'][-1]['option'] != 'behavioral_continue':
            raise SimulationError('support_background_required', 'Approve continuing behavioral care first.')
        decision = DecisionSnapshot.model_validate_json(db.execute('SELECT snapshot FROM decisions WHERE id=?', (patient['current_decision'],)).fetchone()[0])
        if db.execute('SELECT 1 FROM events WHERE id=?', (decision.record_id,)).fetchone() is None: persist(db, decision.model_dump(mode='json'), received_at)
        approval = Approval.model_validate_json(canonical(dict(**record_header('support-envelope-'+uuid.uuid4().hex, patient['id'], at), kind='approval',
            decision_id=decision.record_id, option=None, permitted_options=list(ACTIONS), clinician_id=actor, purpose='randomization_protocol',
            **dict(zip(('expected_patient_version','expected_state_version','expected_consent_version','expected_eligibility_version'), (patient[k] for k in VERSIONS))))))
        validate_approval(approval, decision, decision.view, 'doctor', at, 'mrt_bandit', [r for r in full.records if r.kind=='consent'])
        approval = persist(db, approval.model_dump(mode='json'), received_at)
        consent = max((r for r in full.as_known_at(at+timedelta(microseconds=1)) if r.kind=='consent' and r.component=='mrt_bandit'), key=lambda r:(r.available_at,r.recorded_at,r.revision,r.record_id))
        background = next(r for r in full.records if r.record_id == sim['actions'][-1]['assignment_id'])
        snapshot = persist(db, dict(**(record_header('support-envelope-snapshot-'+uuid.uuid4().hex, patient['id'], at)|dict(schema_version='2.1.0')),
            kind='protocol_snapshot', family='support', protocol=SUPPORT_REF, template=SUPPORT_REF,
            consent_refs=[exact_ref(consent).model_dump()], approval_refs=[exact_ref(approval).model_dump()],
            background_ref=exact_ref(background).model_dump(), support_refs=[], activation_at=at.isoformat()), received_at)
        loop.update(status='active', snapshot_id=snapshot.record_id, approval_id=approval.record_id, actor=actor,
                    nof1_review_identity=sha(sim.get('nof1', {})), configuration=CONFIG_REF)
    if data.action != 'approve':
        state['workflow'].update(support_mode='paused', learning='support_unavailable')
    else: state['workflow'].update(support_mode='adaptive', learning='support_active', support_policy=CONFIG_REF)
    command_id='support-command-'+uuid.uuid4().hex
    if data.action=='approve':loop['command_id']=command_id
    encoded = canonical(dict(kind='support_envelope_command', command=data.model_dump(mode='json'), actor=actor,
        envelope_id=loop.get('snapshot_id'),at=received_at.isoformat()))
    db.execute('INSERT INTO state_changes VALUES(?,?,?,?,?)', (command_id, patient['id'], actor, received_at.isoformat(), encoded))
    db.execute('UPDATE patients SET state_json=?,version=version+1,state_version=state_version+1,eligibility_version=eligibility_version+1,consent_version=consent_version+? WHERE id=?',
               (canonical(state), int(data.action in ('consent','withdraw')), patient['id']))
    create_decision(db, patient['id'], received_at)
    return dict(status=loop['status'], action=data.action)


def decide(db, settings, patient, state, received_at):
    """Persist the final distribution BEFORE the single purpose-keyed draw.

    Caller owns rollback, and never invokes this from a read/approval/navigation.
    Original envelope persists; per-decision Approval is an administrative
    execution record under that envelope, not a new claim of human approval.
    """
    from .workflow import _producer_history as history, patient_clock, record_header
    from .support_s2_authority import producer_persist as persist,producer_gate,producer_id
    from .live_journal import active_episodes
    producer_gate(db,patient['id'])
    sim = state['simulation']; loop = sim['support_controller']; at = patient_clock(patient, received_at)
    full = history(db, patient['id'])
    allowed, reasons = mask(full, state, at, received_at)
    if active_episodes(db, patient['id']): allowed, reasons = (), ['Independent clinical hold']
    snapshot = DecisionSnapshot.model_validate_json(db.execute('SELECT snapshot FROM decisions WHERE id=?', (patient['current_decision'],)).fetchone()[0])
    if ((snapshot.patient_version,snapshot.state_version,snapshot.consent_version,snapshot.eligibility_version) != tuple(patient[k] for k in VERSIONS)
            or snapshot.cutoff != at or snapshot.patient_id != patient['id'] or snapshot.view.mode != 'current'
            or snapshot.workflow.model_dump(mode='json') != state['workflow']):
        raise ValueError('support_exact_current_snapshot_required')
    if any(r.kind=='support_decision' and r.cutoff==at for r in full.records):
        raise ValueError('support_decision_already_persisted')
    envelope = next((r for r in full.records if r.record_id==loop.get('snapshot_id')), None)
    if allowed:
        from .protocol import validate_snapshot
        validate_snapshot(full, envelope, max(at,received_at)+timedelta(microseconds=1))
    expected = [dict(action=a,status='eligible' if a in allowed else 'excluded',reasons=[] if a in allowed else reasons) for a in ACTIONS]
    current = [e.model_dump(mode='json') for e in snapshot.eligibility if e.action in ACTIONS]
    if state['workflow']['support_mode']!='paused' and current != expected:
        raise ValueError('support_eligibility_changed_refresh_required')
    from .support_s2_invocation import candidate_context
    saved = (dict(summary_available=False,serving_authority=False,reason='UNTRUSTED_candidate_fallback_no_scientific_authority')
        if candidate_context(db) is not None else saved_status(db, patient['owner_id'], patient, at)['saved']) if len(allowed)==2 else dict(summary_available=False,serving_authority=False,reason='current_mask_not_binary')
    availability, probabilities, fallback = final_distribution(allowed, saved)
    if not any(r.record_id==snapshot.record_id for r in full.records):snapshot=persist(db,snapshot.model_dump(mode='json'),received_at)
    full=history(db,patient['id'])
    from .support_s2_authority import derive_execution_authorization
    receipt=derive_execution_authorization(db,full,patient,state,snapshot,saved,probabilities,fallback,at,received_at)
    approval = None; assignment_id = producer_id(db,'support-assignment-'+sha([patient['id'],snapshot.record_id])[:32]) if allowed else None
    if allowed:
        value = dict(**record_header(producer_id(db,'s2-admin-'+receipt['sha256'][:32]),patient['id'],at),kind='approval',
            decision_id=snapshot.record_id,option='no_prompt' if len(allowed)==1 else None,
            permitted_options=[] if len(allowed)==1 else list(ACTIONS),clinician_id=loop['actor'],
            purpose='ordinary_treatment' if len(allowed)==1 else 'randomization_protocol',
            **dict(zip(('expected_patient_version','expected_state_version','expected_consent_version','expected_eligibility_version'),(patient[k] for k in VERSIONS))))
        approval = Approval.model_validate_json(canonical(value))
        validate_approval(approval,snapshot,snapshot.view,'doctor',at,'mrt_bandit' if len(allowed)==2 else None,[r for r in full.records if r.kind=='consent'])
        approval = persist(db,value,received_at)
    known = full.as_known_at(at)
    report = max((r for r in known if r.kind=='daily_report' and r.missingness=='observed'),key=lambda r:(r.event_at,r.available_at,r.record_id),default=None)
    context = ([report] if report else [])+[r for r in known if r.kind=='delivery' and r.option=='support_prompt' and r.stage=='delivered' and at-timedelta(days=6)<=r.event_at<at]
    identifier=producer_id(db,'support-decision-'+sha([patient['id'],snapshot.record_id])[:32]); assessment=at+timedelta(days=1,minutes=-1)
    decision = persist(db,dict(**(record_header(identifier,patient['id'],at)|dict(schema_version='2.1.0')),kind='support_decision',
        decision_snapshot=exact_ref(snapshot).model_dump(),decision_index=sim['day'],cutoff=at.isoformat(),
        context=[exact_ref(r).model_dump() for r in context],context_projection_sha256=projection_hash(full,at),
        context_mapping=reference('poc-support-public-context-v1','Latest available quality and preceding six nights delivered prompts'),
        policy=state['workflow']['support_policy'],mechanism=SUPPORT_REF,mode=state['workflow']['support_mode'],
        eligibility=current,policy_constraint=dict(allowed_actions=list(ACTIONS),reason='unrestricted',snapshot_ref=None),
        availability=availability,unavailable_reasons=reasons if not allowed else [],probabilities=probabilities,probability_tolerance=1e-12,
        assignment_id=assignment_id,distribution_persisted_at=at.isoformat(),execution_receipt=receipt,
        outcome_window=dict(id=identifier+'-window',starts_at=at.isoformat(),ends_at=assessment.isoformat(),assessment_at=assessment.isoformat(),
            timezone='UTC',local_date=at.date().isoformat(),endpoint_definition=reference('poc-support-quality-window-v1','Noon through next day11:59; exact next-morning reported quality')),
        outcome_link_id=identifier+'-outcome'),received_at)
    if settings.fault: settings.fault('after_support_distribution')
    assignment = None
    if allowed:
        seed = None; option='no_prompt'
        if availability=='randomized':
            unit=sha(['s2-assignment-unit-v1',sim['seed'],sim['index']])
            seed=dict(namespace='assignment',protocol=CONFIG_REF['id'],scenario='interactive-synthetic',replicate=0,
                patient='assignment-unit-'+unit[:32],time_index=sim['day'],process='s2-support-assignment-v1')
            option='support_prompt' if keyed_uniform(seed)<probabilities['support_prompt'] else 'no_prompt'
        value=dict(**record_header(assignment_id,patient['id'],at),kind='assignment',decision_id=snapshot.record_id,
            approval_id=approval.record_id,option=option,experimental=seed is not None,component='mrt_bandit' if seed else None,
            probability=probabilities[option] if seed else None,seed=seed,support_policy=state['workflow']['support_policy'],
            patient_blinded=False,clinician_blinded=False,clinician_override=None,override_reason=None)
        from contracts.domain.entities import Assignment
        typed=Assignment.model_validate_json(canonical(value))
        validate_assignment(typed,approval,snapshot,snapshot.view,'doctor',[r for r in full.records if r.kind=='consent'])
        assignment=persist(db,value,received_at)
        sim['support'].append(dict(day=sim['day'],option=option,assignment_id=assignment.record_id))
    loop['last_decision']=dict(id=decision.record_id,cutoff=at.isoformat(),probabilities=probabilities,fallback_reason=fallback,
        availability=availability,assignment_id=assignment_id,execution_receipt=receipt)
    return decision, assignment


def dispatch(db,settings,patient,state,decision,assignment,received_at):
    """Actual simulated 20:00 offer operation; never inferred from delivery."""
    from .workflow import _producer_history as history,record_header
    from .support_s2_authority import producer_persist as persist,producer_id
    from .live_journal import active_episodes
    from .support_s2_authority import producer_qualification as qualification,put
    qualification(db,patient['id'])
    if assignment is None:return None,False
    allowed,_=mask(history(db,patient['id']),state,decision.cutoff,received_at)
    if active_episodes(db,patient['id']):allowed=()
    if assignment.option not in allowed:
        # Only the future generator schedule is canceled. Immutable probability,
        # assignment and original authorization are retained with this refusal.
        state['simulation']['support'][:]=[r for r in state['simulation']['support'] if r['assignment_id']!=assignment.record_id]
        put(db,patient['id'],patient['owner_id'],'poc-support-interactive-cancellation-v1',
            dict(decision=exact_ref(decision).model_dump(),assignment=exact_ref(assignment).model_dump(),
                 at=(decision.cutoff+timedelta(hours=8)).isoformat(),reason='Current authority restricted pending dispatch'),received_at)
        return None,True
    if assignment.option=='no_prompt':return None,False
    at=decision.cutoff+timedelta(hours=8)
    header=record_header(producer_id(db,'support-offer-'+sha(assignment.record_id)[:32]),patient['id'],at)
    header['source'].update(id='foundation-support-offer-v1',version='1.0.0',adapter='research_configuration')
    offered=persist(db,dict(**header,
        kind='delivery',assignment_id=assignment.record_id,option='support_prompt',stage='offered',adherence=None,
        rescue=False,protocol_deviations=[]),received_at)
    if settings.fault:settings.fault('after_support_offer')
    return offered,False


def advance(db,settings,patient,state,target,received_at):
    """One serialized app transaction, daily decisions even for visit advance."""
    from .workflow import create_decision,patient_clock
    from .simulation import product,persist_product
    from .support_s2_authority import close_stages,producer_gate
    producer_gate(db,patient['id'])
    sim=state['simulation'];count=0
    while sim['day']<target:
        current=db.execute('SELECT * FROM patients WHERE id=? AND owner_id=?',(patient['id'],patient['owner_id'])).fetchone()
        decision,assignment=decide(db,settings,current,state,received_at)
        offered,canceled=dispatch(db,settings,current,state,decision,assignment,received_at)
        next_day=sim['day']+1;cutoff=decision.cutoff+timedelta(days=1)
        generated=product(settings,sim,patient['id'],next_day)
        count+=persist_product(db,generated,patient['id'],after=patient_clock(current,received_at),cutoff=cutoff,
            received_at=received_at,actions=sim['actions'],simulation=sim)
        if settings.fault:settings.fault('after_support_product')
        close_stages(db,settings,current,decision,assignment,offered,received_at,canceled=canceled)
        sim['day']=next_day
        if next_day%14==0:
            state['stage']='ASSIGN-10' if next_day==84 else 'ASSIGN-02'
            state['workflow']['clinical']='maintenance_closeout' if next_day==84 else 'scheduled_reassessment'
        db.execute('UPDATE patients SET state_json=?,version=version+1,state_version=state_version+1,eligibility_version=eligibility_version+1 WHERE id=?',
            (canonical(state),patient['id']))
        if settings.fault:settings.fault('after_support_clock')
        create_decision(db,patient['id'],received_at)
    return dict(status='advanced',day=sim['day'],cutoff=cutoff.isoformat(),records_added=count)
