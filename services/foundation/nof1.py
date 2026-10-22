"""One physician-authorized fictional N-of-1 loop in the existing transaction."""
from datetime import timedelta
import json
import uuid

from contracts.domain.boundaries import lineage_heads,visible_records,validate_approval,validate_assignment
from contracts.domain.entities import Approval,DecisionSnapshot
from contracts.domain.evidence_v2 import exact_ref
from contracts.domain.protocol import NOF1_REF,RECORD_ADAPTER_V21
from .store import canonical,digest,instant,timestamp
from .workflow import history,patient_clock,record_header,SUPPORT
from .simulation import SimulationError
from .nof1_clock import boundaries_at,phase_at,TOTAL_DAYS

VERSIONS=('version','state_version','consent_version','eligibility_version')


def persist(db,value,received_at):
    """Only server-constructed administrative records; generic ingestion stays closed."""
    value=dict(value)
    raw=canonical({k:v for k,v in value.items() if k!='source'}).encode()
    value['source']=dict(value['source'],raw_sha256=digest(raw))
    record=RECORD_ADAPTER_V21.validate_json(canonical(value))
    encoded=canonical(record.model_dump(mode='json'))
    db.execute('INSERT INTO events VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
        (record.record_id,record.patient_id,record.kind,record.lineage_id,record.revision,record.duplicate_of,
         encoded,digest(encoded),raw,digest(raw),timestamp(record.event_at),timestamp(record.recorded_at),
         timestamp(record.available_at),0 if record.kind=='consent' else 5,timestamp(received_at)))
    return record


def audit(db,patient_id,actor,at,kind,**details):
    identifier='nof1-audit-'+uuid.uuid4().hex
    value=dict(kind=kind,synthetic=True,at=timestamp(at),**details)
    db.execute('INSERT INTO state_changes VALUES(?,?,?,?,?)',(identifier,patient_id,actor,timestamp(at),canonical(value)))
    return identifier


def checkpoint(db,patient_id,received_at,label):
    patient=db.execute('SELECT * FROM patients WHERE id=?',(patient_id,)).fetchone()
    state=json.loads(patient['state_json']);loop=state['simulation']['nof1']
    if not loop.get('snapshot_id'):return
    approval=json.loads(db.execute('SELECT payload FROM events WHERE id=?',(loop['approval_id'],)).fetchone()[0])
    decision=db.execute('SELECT * FROM decisions WHERE id=?',(patient['current_decision'],)).fetchone()
    value=dict(workspace=json.loads(decision['display']),approval=approval,rationale=label,protocol=NOF1_REF,
        follow_up=dict(id='nof1-review-'+loop['snapshot_id'],due_at=timestamp(instant(state['simulation']['origin'])+timedelta(days=loop['start_day']+72)),owner_id=loop['actor']),
        audit=dict(actor=loop['actor'],change=label,at=timestamp(received_at)))
    encoded=canonical(value)
    db.execute('INSERT INTO bundles VALUES(?,?,?,?,?,?)',('nof1-checkpoint-'+uuid.uuid4().hex,patient_id,
        patient['current_decision'],encoded,digest(encoded),patient['cutoff']))


def selected(patient):
    state=json.loads(patient['state_json']);simulation=state.get('simulation',{})
    if simulation.get('law_version')!='poc-longitudinal-v2' or simulation.get('family')!='nof1_med':
        raise SimulationError('nof1_patient_required','Explicitly generate and select a v2 N-of-1 patient.')
    return state,simulation


def latest_consent(full,at,received_at):
    candidates=[r for r in full.records if r.kind=='consent' and r.component=='nof1']
    heads=lineage_heads(visible_records(candidates,max(at,received_at),inclusive=True))
    return max(heads,key=lambda r:(r.available_at,r.recorded_at,r.revision,r.record_id),default=None)


def safety_reasons(db,patient_id,state,at,received_at):
    from .live_journal import active_episodes
    full=history(db,patient_id)
    reasons=[]
    if state['workflow']['hold_reasons'] or active_episodes(db,patient_id):reasons.append('Clinical hold')
    events=lineage_heads(visible_records(full.records,max(at,received_at),inclusive=True))
    if any(r.record_status!='retracted' and r.kind=='intercurrent_event' and r.event_type in
           ('death','rescue','fall','regimen_change','steroid_change','discontinuation','override') for r in events):
        reasons.append('Death, rescue, fall or material treatment change requires a new assessment')
    consent=latest_consent(full,at,received_at)
    if consent is None or not consent.permits('nof1',at):reasons.append('Current component consent and approved synthetic oversight required')
    return reasons


def readiness(db,patient,state,at,received_at):
    simulation=state['simulation'];loop=simulation.get('nof1',{})
    reasons=safety_reasons(db,patient['id'],state,at,received_at)
    if not loop.get('review'):reasons.append('Explicit provisional stability, eligibility, fall-risk and rescue-plan review required')
    elif loop.get('status')!='active' and {k:patient[k] for k in VERSIONS} not in (loop.get('review_versions'),loop.get('authorized_versions')):
        reasons.append('The prior review was invalidated by a patient, consent or state change')
    if not simulation['actions'] or simulation['actions'][-1]['option']!='behavioral_continue':
        reasons.append('A current approved and assigned behavioral continuation is required')
    else:
        assignment=db.execute('SELECT payload FROM events WHERE id=? AND patient_id=? AND kind=?',
            (simulation['actions'][-1]['assignment_id'],patient['id'],'assignment')).fetchone()
        if assignment is None:reasons.append('Current behavioral Assignment is missing')
    if loop.get('status') in ('stopped','completed'):reasons.append('This protocol cannot silently restart')
    return reasons


def guard(db,patient_id,state,at,received_at):
    """Recheck full current authority and exact frozen context before every draw."""
    simulation=state['simulation'];loop=simulation.get('nof1',{})
    reasons=safety_reasons(db,patient_id,state,at,received_at)
    if not loop.get('review'):reasons.append('Review invalidated')
    if not simulation['actions'] or simulation['actions'][-1]['assignment_id']!=loop.get('background_id'):
        reasons.append('Frozen behavioral background changed')
    if state['workflow']['support_policy']!=SUPPORT or state['workflow']['support_mode'] not in ('frozen','fixed'):
        reasons.append('Frozen no-prompt support changed')
    if state['workflow']['learning'] not in ('nof1_block','nof1_washout','nof1_review') or state['workflow']['data_readiness']!='ready':
        reasons.append('Reviewed protocol state or eligibility changed')
    if any(row['option']!='no_prompt' or row['assignment_id']!=loop.get('support_id') for row in simulation['support']
           if row['day']>=loop.get('start_day',0)):
        reasons.append('Frozen no-prompt support schedule changed')
    try:
        full=history(db,patient_id)
        from .protocol import validate_snapshot
        snapshot=next(r for r in full.records if r.record_id==loop['snapshot_id'])
        validate_snapshot(full,snapshot,max(at,received_at)+timedelta(microseconds=1))
    except (ValueError,KeyError,StopIteration):reasons.append('Frozen exact protocol authority changed')
    return list(dict.fromkeys(reasons))


def stop(db,patient_id,state,at,received_at,reasons,actor='protocol'):
    simulation=state['simulation'];loop=simulation.get('nof1')
    if not loop or loop.get('status') in ('stopped','completed'):return
    loop.update(status='stopped',phase='stopped',uninterrupted=False)
    loop.setdefault('deviations',[]).append(dict(at=timestamp(at),reasons=reasons))
    if simulation['medications'] and simulation['medications'][-1]['option'] is not None:
        # No retrospective rewrite: stop the assigned schedule at current noon.
        day=(at-instant(simulation['origin'])).days
        if simulation['medications'][-1]['day']==day:
            # Cancel pending delivery before20:00. The typed draw and immutable
            # audit remain; only the future generator schedule is canceled.
            simulation['medications'][-1]=dict(day=day,option=None,assignment_id=None)
        else:simulation['medications'].append(dict(day=day,option=None,assignment_id=None))
    audit(db,patient_id,actor,received_at,'nof1_stopped',fictional_at=timestamp(at),reasons=reasons)


def reconcile(db,patient,state,received_at):
    simulation=state.get('simulation',{});loop=simulation.get('nof1',{})
    if loop.get('status')=='active':
        reasons=guard(db,patient['id'],state,patient_clock(patient,received_at),received_at)
        if reasons:stop(db,patient['id'],state,patient_clock(patient,received_at),received_at,reasons)
    return state


def approval_record(db,patient,actor,at,received_at,*,options,option=None):
    snapshot=DecisionSnapshot.model_validate_json(db.execute('SELECT snapshot FROM decisions WHERE id=?',(patient['current_decision'],)).fetchone()[0])
    if db.execute('SELECT 1 FROM events WHERE id=?',(snapshot.record_id,)).fetchone() is None:
        snapshot=persist(db,snapshot.model_dump(mode='json'),received_at)
    value=dict(**record_header('approval-'+uuid.uuid4().hex,patient['id'],at),kind='approval',decision_id=snapshot.record_id,
        option=option,permitted_options=options,clinician_id=actor,purpose='randomization_protocol' if options else 'ordinary_treatment',
        expected_patient_version=patient['version'],expected_state_version=patient['state_version'],
        expected_consent_version=patient['consent_version'],expected_eligibility_version=patient['eligibility_version'])
    approval=Approval.model_validate_json(canonical(value))
    validate_approval(approval,snapshot,snapshot.view,'doctor',at,'nof1' if options else None,
                      [r for r in history(db,patient['id']).records if r.kind=='consent'])
    return persist(db,value,received_at),snapshot


def assigned(db,patient_id,approval,snapshot,option,at,received_at,seed=None):
    value=dict(**record_header('assignment-'+uuid.uuid4().hex,patient_id,at),kind='assignment',
        decision_id=snapshot.record_id,approval_id=approval.record_id,option=option,experimental=seed is not None,
        component='nof1' if seed else None,probability=.5 if seed else None,seed=seed,support_policy=SUPPORT,
        patient_blinded=False,clinician_blinded=False,clinician_override=None,override_reason=None)
    record=RECORD_ADAPTER_V21.validate_json(canonical(value))
    validate_assignment(record,approval,snapshot,snapshot.view,'doctor',[r for r in history(db,patient_id).records if r.kind=='consent'])
    return persist(db,value,received_at)


def noon(db,settings,patient_id,state,day,received_at):
    simulation=state['simulation'];loop=simulation['nof1']
    relative=day-loop['start_day'];at=instant(simulation['origin'])+timedelta(days=day)
    if loop['status']!='active' or loop.get('last_noon',-1)>=day:return
    reasons=guard(db,patient_id,state,at,received_at)
    if reasons:
        stop(db,patient_id,state,at,received_at,reasons);return
    for boundary in boundaries_at(relative):
        if boundary=='review':
            counts={option:sum(d['option']==option for d in loop['draws']) for option in ('MED_A','MED_B')}
            review=dict(day=day,protocol_day=relative,counts=counts,
                analysis_status='unavailable_methods_pending' if min(counts.values())>=2 else 'inconclusive_insufficient_arm_blocks')
            loop['reviews'].append(review);audit(db,patient_id,loop['actor'],received_at,'nof1_review',**review)
        elif boundary=='complete':
            loop.update(status='completed',phase='review');audit(db,patient_id,loop['actor'],received_at,'nof1_completed',day=day)
        elif boundary=='washout_start':
            simulation['medications'].append(dict(day=day,option=None,assignment_id=None))
            audit(db,patient_id,loop['actor'],received_at,'nof1_washout',day=day,block=relative//9+1)
        elif boundary=='block_start':
            import numpy as np
            # Replay uses the reproducible panel unit, not a fresh service UUID.
            # Domain separation keeps assignment RNG distinct from generator
            # outcomes; the full replay seed/index never enters reduced H*.
            unit=digest(canonical(['poc-nof1-assignment-unit-v1',simulation['seed'],simulation['index']]))
            seed=dict(namespace='assignment',protocol=NOF1_REF['id'],scenario='interactive-synthetic',replicate=0,
                patient='assignment-unit-'+unit[:32],time_index=relative//9+1,process='nof1-block-v1')
            uniform=float(np.random.default_rng(int(digest(canonical(seed)),16)).random())
            option='MED_A' if uniform<.5 else 'MED_B'
            full=history(db,patient_id)
            approval=next(r for r in full.records if r.record_id==loop['approval_id'])
            snapshot=next(r for r in full.records if r.record_id==approval.decision_id)
            assignment=assigned(db,patient_id,approval,snapshot,option,at,received_at,seed)
            draw=dict(day=day,block=relative//9+1,probabilities=dict(MED_A=.5,MED_B=.5),seed=seed,
                uniform=uniform,option=option,assignment_id=assignment.record_id,persisted_at=timestamp(at),
                washout_starts_day=day+7,next_boundary_day=day+9)
            loop['draws'].append(draw);simulation['medications'].append(dict(day=day,option=option,assignment_id=assignment.record_id))
            audit(db,patient_id,loop['actor'],received_at,'nof1_block_draw',**draw)
            if settings.fault:settings.fault('after_nof1_draw')
    loop.update(phase_at(relative));loop['last_noon']=day
    if loop['status']=='active':
        simulation['support'].append(dict(day=day,option='no_prompt',assignment_id=loop['support_id']))


def transition(db,settings,patient,actor,data,received_at):
    """Consent/review/approval/start use the same controller as advance boundaries."""
    state,simulation=selected(patient);at=patient_clock(patient,received_at)
    if data.decision_id!=patient['current_decision'] or any(getattr(data,'expected_'+k)!=patient[k] for k in VERSIONS):
        raise SimulationError('stale_protocol','Refresh and explicitly review this patient before continuing.')
    loop=simulation.setdefault('nof1',dict(status='design',draws=[],reviews=[],deviations=[],uninterrupted=True))
    if loop['status']=='active' and data.action in ('approve','start'):
        raise SimulationError('protocol_active','An active protocol retains its original approval, start and draw history. It cannot be approved or started again.')
    if loop['status'] in ('stopped','completed'):
        raise SimulationError('protocol_closed','History is retained. This protocol cannot restart automatically.')
    if data.action=='withdraw':
        consent_status='withdrawn'
    elif data.action=='consent':
        if loop['status']=='active':raise SimulationError('protocol_active','Consent cannot silently renew an active protocol.')
        consent_status='active'
    else:consent_status=None
    if consent_status:
        if data.consent_expires_at is not None and data.consent_expires_at<=at:
            raise SimulationError('expired_consent','Consent expiry must be later than the current fictional clock.')
        full=history(db,patient['id']);prior=[r for r in full.records if r.kind=='consent' and r.lineage_id=='nof1-consent-'+patient['id']]
        previous=max(prior,key=lambda r:r.revision,default=None)
        value=dict(**record_header('consent-'+uuid.uuid4().hex,patient['id'],at),kind='consent',component='nof1',
            consent_version='poc-nof1-consent-v1',oversight_version='synthetic-engineering-v1',consent_status=consent_status,
            oversight_status='approved_synthetic' if consent_status=='active' else 'withdrawn',effective_at=timestamp(at),
            expires_at=timestamp(data.consent_expires_at) if data.consent_expires_at else None,withdrawn_at=timestamp(at) if consent_status=='withdrawn' else None)
        value.update(lineage_id='nof1-consent-'+patient['id'],revision=previous.revision+1 if previous else 1,
            supersedes=previous.record_id if previous else None)
        persist(db,value,received_at)
        if loop['status']!='active':loop.pop('review',None);loop.pop('approval_id',None)
        if data.action=='withdraw':stop(db,patient['id'],state,at,received_at,['Component consent withdrawn'],actor)
    elif data.action=='review':
        if loop['status']=='active':raise SimulationError('protocol_active','An active frozen review cannot be silently replaced.')
        loop['review']=dict(assertions=data.assertions,at=timestamp(at),actor=actor,rationale=data.rationale)
        loop['review_versions']={k:patient[k]+(k!='consent_version') for k in VERSIONS}
        loop.pop('approval_id',None)
    elif data.action=='approve':
        reasons=readiness(db,patient,state,at,received_at)
        if reasons:raise SimulationError('protocol_not_ready','; '.join(reasons))
        approval,snapshot=approval_record(db,patient,actor,at,received_at,options=['MED_A','MED_B'])
        loop.update(approval_id=approval.record_id,actor=actor,authorized_versions={k:patient[k]+(k!='consent_version') for k in VERSIONS})
        workspace=json.loads(db.execute('SELECT display FROM decisions WHERE id=?',(patient['current_decision'],)).fetchone()[0])
        saved=dict(workspace=workspace,approval=approval.model_dump(mode='json'),rationale=data.rationale,
            protocol=NOF1_REF,follow_up=dict(id='nof1-review-'+approval.record_id,due_at=timestamp(at+timedelta(days=36)),owner_id=actor),
            audit=dict(actor=actor,change='Explicit both-MED fixed-template approval; no winner chosen',at=timestamp(received_at)))
        encoded=canonical(saved)
        db.execute('INSERT INTO bundles VALUES(?,?,?,?,?,?)',(approval.record_id,patient['id'],snapshot.record_id,encoded,digest(encoded),timestamp(at)))
    elif data.action=='start':
        reasons=readiness(db,patient,state,at,received_at)
        if reasons:raise SimulationError('protocol_not_ready','; '.join(reasons))
        if not loop.get('approval_id') or loop.get('authorized_versions')!={k:patient[k] for k in VERSIONS}:
            raise SimulationError('stale_protocol_approval','Explicit approval must match the current unchanged review and versions.')
        if simulation['day']+TOTAL_DAYS>84:raise SimulationError('protocol_duration','The full72-night template must fit within this synthetic horizon.')
        support_approval,snapshot=approval_record(db,patient,actor,at,received_at,options=[],option='no_prompt')
        support=assigned(db,patient['id'],support_approval,snapshot,'no_prompt',at,received_at)
        full=history(db,patient['id']);approval=next(r for r in full.records if r.record_id==loop['approval_id'])
        background=next(r for r in full.records if r.record_id==simulation['actions'][-1]['assignment_id'])
        consent=latest_consent(full,at,received_at)
        saved=record_header('protocol-'+uuid.uuid4().hex,patient['id'],at)|dict(schema_version='2.1.0',kind='protocol_snapshot',
            family='nof1_med',protocol=NOF1_REF,template=NOF1_REF,consent_refs=[exact_ref(consent).model_dump()],
            approval_refs=[exact_ref(approval).model_dump()],background_ref=exact_ref(background).model_dump(),
            support_refs=[exact_ref(support).model_dump()],activation_at=timestamp(at))
        frozen=persist(db,saved,received_at)
        loop.update(status='active',snapshot_id=frozen.record_id,background_id=background.record_id,support_id=support.record_id,
            start_day=simulation['day'],last_noon=simulation['day']-1)
        state['workflow'].update(support_mode='frozen',learning='nof1_block');state['stage']='ASSIGN-05'
        noon(db,settings,patient['id'],state,simulation['day'],received_at)
    audit(db,patient['id'],actor,received_at,'nof1_'+data.action,rationale=data.rationale,
        fictional_at=timestamp(at),template=NOF1_REF)
    simulation['protocol_status']=loop['status']
    db.execute('UPDATE patients SET state_json=?,version=version+1,state_version=state_version+1,eligibility_version=eligibility_version+1,consent_version=consent_version+? WHERE id=?',
        (canonical(state),int(consent_status is not None),patient['id']))
    from .workflow import create_decision
    create_decision(db,patient['id'],received_at)
    if data.action in ('start','withdraw'):checkpoint(db,patient['id'],received_at,'Saved N-of-1 '+data.action+'; no estimated winner')
    return dict(status='recorded',action=data.action,protocol_status=loop['status'])


def advance(db,settings,patient,state,target,received_at):
    from .simulation import product,persist_product
    from .workflow import create_decision
    simulation=state['simulation'];loop=simulation['nof1'];count=0
    origin=instant(simulation['origin'])
    # Each segment is noon→20:00 delivery→11:59 report→next noon.
    # Consequently a14-day click cannot generate outcomes across an unprocessed
    # block/washout/review boundary or use a not-yet-persisted assignment.
    for next_day in range(simulation['day']+1,target+1):
        noon(db,settings,patient['id'],state,next_day-1,received_at)
        cutoff=origin+timedelta(days=next_day)
        generated=product(settings,simulation,patient['id'],next_day)
        count+=persist_product(db,generated,patient['id'],after=origin+timedelta(days=next_day-1),
            cutoff=cutoff,received_at=received_at,actions=simulation['actions'],simulation=simulation)
        simulation['day']=next_day
        noon(db,settings,patient['id'],state,next_day,received_at)
    if settings.fault:settings.fault('after_simulation_events')
    simulation['protocol_status']=loop['status']
    if loop['status']=='active':
        state['stage']='ASSIGN-05';state['workflow'].update(learning='nof1_'+loop['phase'],support_mode='frozen')
    elif loop['status']=='completed':
        state['stage']='ASSIGN-06';state['workflow'].update(learning='nof1_review',support_mode='frozen')
    db.execute('UPDATE patients SET state_json=?,version=version+1,state_version=state_version+1,eligibility_version=eligibility_version+1 WHERE id=?',
        (canonical(state),patient['id']))
    create_decision(db,patient['id'],received_at)
    checkpoint(db,patient['id'],received_at,'Saved N-of-1 advancement; no estimated winner')
    return dict(status='advanced',day=target,cutoff=timestamp(origin+timedelta(days=target)),records_added=count)
