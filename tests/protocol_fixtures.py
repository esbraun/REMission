"""Public P1 schema fixtures; no executable configuration or fitted output."""
import copy
from datetime import timedelta

from contracts.domain.analysis import canonical, reference, sha
from contracts.domain.evidence_v2 import exact_ref, projection_hash
from contracts.domain.protocol import ObservedHistoryV21, RECORD_ADAPTER_V21
from contracts.domain.protocol import PROTOCOL_REFS
from services.foundation.store import instant
from services.foundation.workflow import record_header, state_for, SUPPORT
from services.generator.restricted_v2 import generate

ORIGIN=instant('2026-01-01T12:00:00Z')
PATIENT='P1-PUBLIC'


def typed(value):
    value=copy.deepcopy(value)
    value['source']['raw_sha256']=sha({k:v for k,v in value.items() if k!='source'})
    return RECORD_ADAPTER_V21.validate_json(canonical(value))


def history(records):
    return ObservedHistoryV21.model_validate_json(canonical(dict(schema_version='2.1.0',synthetic=True,
        kind='observed_history',patient_id=PATIENT,records=[r.model_dump(mode='json') if hasattr(r,'model_dump') else r for r in records])))


def full_history(*, family='support', days=2, recursive=True):
    value=generate(dict(law_version='poc-longitudinal-v2',family=family,seed=1245,index=1,
        patient_id=PATIENT,through_day=days,actions=[],medications=[],support=[]))
    records=[RECORD_ADAPTER_V21.validate_json(canonical(entry['record'])) for entry in value['records']]
    if not recursive:return history(records)
    at=ORIGIN+timedelta(days=1)
    clinical=state_for('ASSIGN-08')['workflow']
    eligibility=[dict(action=a,status='excluded',reasons=['not_activated']) for a in ('support_prompt','no_prompt')]
    snapshot=typed(dict(**record_header('p1-decision',PATIENT,at),kind='decision_snapshot',cutoff=at.isoformat(),
        patient_version=1,state_version=1,consent_version=1,eligibility_version=1,workflow=clinical,
        view=dict(patient_id=PATIENT,mode='current',snapshot_id=None),eligibility=eligibility,
        outcome='quality',horizon_days=1,estimand=reference('fixture-estimand','not active'),model=reference('fixture-model','not active'),
        posterior=None,evidence=[],policy=SUPPORT))
    records.append(snapshot)
    quality=next(r for r in records if r.kind=='daily_report' and r.event_at==at-timedelta(minutes=1))
    isi=next(r for r in records if r.kind=='isi')
    assessment=ORIGIN+timedelta(days=2,minutes=-1)
    window=dict(id='p1-window',starts_at=at.isoformat(),ends_at=assessment.isoformat(),assessment_at=assessment.isoformat(),
        timezone='UTC',local_date=at.date().isoformat(),endpoint_definition=reference('quality-window','next morning quality'))
    decision=typed(dict(**(record_header('p1-support',PATIENT,at)|dict(schema_version='2.1.0')),kind='support_decision',
        decision_snapshot=exact_ref(snapshot).model_dump(),decision_index=0,cutoff=at.isoformat(),
        context=[exact_ref(quality).model_dump(),exact_ref(isi).model_dump()],context_projection_sha256=projection_hash(history(records),at),
        context_mapping=reference('fixture-context','audit references'),policy=SUPPORT,mechanism=reference('fixture-mechanism','not active'),
        mode='paused',eligibility=eligibility,policy_constraint=dict(allowed_actions=['support_prompt','no_prompt'],reason='unrestricted',snapshot_ref=None),
        availability='unavailable',unavailable_reasons=['not_activated'],probabilities=dict(support_prompt=0.,no_prompt=0.),probability_tolerance=1e-12,
        assignment_id=None,distribution_persisted_at=at.isoformat(),execution_receipt=reference('fixture-execution','no assignment'),
        outcome_window=window,outcome_link_id='p1-outcome'))
    records.append(decision)
    report=next(r for r in records if r.kind=='daily_report' and r.event_at==assessment)
    status='observed' if report.missingness=='observed' else 'missing'
    published=assessment+timedelta(seconds=10)
    header=record_header('p1-outcome',PATIENT,assessment)|dict(schema_version='2.0.0',recorded_at=published.isoformat(),available_at=published.isoformat())
    outcome=typed(dict(**header,kind='support_outcome_link',support_decision=exact_ref(decision).model_dump(),assignment_ref=None,
        window_id=window['id'],assessment_at=assessment.isoformat(),evaluated_as_of=published.isoformat(),
        reward=dict(status=status,report_ref=exact_ref(report).model_dump() if status=='observed' else None,field='sleep_quality',unit='quality_points',
            reason=None if status=='observed' else 'missing report',evidence_refs=[exact_ref(report).model_dump(),exact_ref(isi).model_dump()],definition_refs=[]),
        burden=[dict(definition=reference(name,'pending unverified count'),type=name,unit='count',status='pending',value=None,source_refs=[]) for name in ['offered_prompt_count','delivered_prompt_count']],
        offered_closure_ref=None,delivered_closure_ref=None))
    return history([*records,outcome])


def perturb_forbidden(full,*,isi=False):
    """Legitimate full audit hashes/refs change; allowed projection values stay."""
    values={r.record_id:r.model_dump(mode='json') for r in full.records}
    for value in values.values():
        if value['kind']=='daily_report' and value['missingness']=='observed':
            value['function']=1.234;value['diary_sleep_minutes']=300.1;value['goals']=['changed forbidden report metadata']
        if isi and value['kind']=='isi':value['items']=[0]*7
        value['source']['raw_sha256']=sha({'changed_raw_audit':value['record_id']})
    records={k:RECORD_ADAPTER_V21.validate_json(canonical(v)) for k,v in values.items()}
    support=values.get('p1-support')
    if support:
        support['decision_snapshot']=exact_ref(records['p1-decision']).model_dump()
        support['context']=[exact_ref(records[r['record_id']]).model_dump() for r in support['context']]
        support['context_projection_sha256']=projection_hash(history(list(records.values())),instant(support['cutoff']))
        records['p1-support']=typed(support)
        outcome=values['p1-outcome'];outcome['support_decision']=exact_ref(records['p1-support']).model_dump()
        if outcome['reward']['report_ref']:
            outcome['reward']['report_ref']=exact_ref(records[outcome['reward']['report_ref']['record_id']]).model_dump()
        outcome['reward']['evidence_refs']=[exact_ref(records[r['record_id']]).model_dump() for r in outcome['reward']['evidence_refs']]
        records['p1-outcome']=typed(outcome)
    return history(list(records.values()))


def snapshot_history():
    """A typed audit fixture, not service activation or an executable N fit."""
    full=full_history(family='nof1_med',recursive=False)
    at=ORIGIN
    consent=typed(dict(**record_header('n-consent',PATIENT,at-timedelta(seconds=1)),kind='consent',component='nof1',
        consent_version='fixture',oversight_version='fixture',consent_status='active',oversight_status='approved_synthetic',
        effective_at=(at-timedelta(seconds=1)).isoformat(),expires_at=None,withdrawn_at=None))
    decision=typed(dict(**record_header('n-decision',PATIENT,at),kind='decision_snapshot',cutoff=at.isoformat(),
        patient_version=1,state_version=1,consent_version=1,eligibility_version=1,workflow=state_for('ASSIGN-04')['workflow'],
        view=dict(patient_id=PATIENT,mode='current',snapshot_id=None),eligibility=[dict(action=a,status='eligible',reasons=[]) for a in ['MED_A','MED_B','behavioral_continue','no_prompt']],
        outcome='quality',horizon_days=7,estimand=reference('n-fixture-estimand','not executable'),model=reference('n-fixture-model','not executable'),posterior=None,evidence=[],policy=SUPPORT))
    def approval(name,option=None):
        return typed(dict(**record_header(name,PATIENT,at+timedelta(seconds=1)),kind='approval',decision_id=decision.record_id,
            option=option,permitted_options=[] if option else ['MED_A','MED_B'],clinician_id='fixture-doctor',purpose='ordinary_treatment' if option else 'randomization_protocol',
            expected_patient_version=1,expected_state_version=1,expected_consent_version=1,expected_eligibility_version=1))
    binary=approval('n-binary');background_approval=approval('n-background-approval','behavioral_continue');support_approval=approval('n-support-approval','no_prompt')
    def assignment(name,approved):
        return typed(dict(**record_header(name,PATIENT,at+timedelta(seconds=2)),kind='assignment',decision_id=decision.record_id,approval_id=approved.record_id,
            option=approved.option,experimental=False,component=None,probability=None,seed=None,support_policy=SUPPORT,
            patient_blinded=False,clinician_blinded=False,clinician_override=None,override_reason=None))
    background=assignment('n-background',background_approval);support=assignment('n-no-prompt',support_approval)
    activated=at+timedelta(seconds=3)
    snapshot=typed(dict(**(record_header('n-protocol-snapshot',PATIENT,activated)|dict(schema_version='2.1.0')),kind='protocol_snapshot',family='nof1_med',
        protocol=PROTOCOL_REFS['nof1_med'],template=PROTOCOL_REFS['nof1_med'],consent_refs=[exact_ref(consent).model_dump()],approval_refs=[exact_ref(binary).model_dump()],
        background_ref=exact_ref(background).model_dump(),support_refs=[exact_ref(support).model_dump()],activation_at=activated.isoformat()))
    return history([*full.records,consent,decision,binary,background_approval,support_approval,background,support,snapshot])
