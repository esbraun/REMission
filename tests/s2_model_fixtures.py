"""Small public scalar histories only; no generator, Store or fitted evidence."""
from datetime import datetime,timedelta,timezone
from pydantic import TypeAdapter
from contracts.domain.analysis import reference,sha,FIXED_SUPPORT_REF
from contracts.domain.protocol import LAW_REF,SUPPORT_REF
from contracts.domain.protocol_analysis import ProtocolHistory,ReducedRecord,ReducedHeader
from contracts.domain.support_s2 import HSTAR_REF
from contracts.domain.support_s2_fit import CONFIG_REF,DEFINITIONS,S2FitProvenance

ORIGIN=datetime(2026,1,1,12,tzinfo=timezone.utc)
POLICY=reference('UNIT-S2-policy','structural persisted final distribution; no activation claim')
ADAPTER=TypeAdapter(ReducedRecord)


def ref(value):return dict(record_id=value.record_id,projection_sha256=sha(value.model_dump(mode='json')))


def history(patient,day=14,*,all_missing=False,activation_day=0,late_report=None,correction=None,
            duplicate_outcome=None,bad_probability=None,missing_feature=None,statuses=None,
            bad_window=None,bad_approval=None,held=None,bad_snapshot=None):
    records=[];extra_provenance=[];statuses=statuses or {}
    def record(kind,name,at,**fields):
        header=dict(record_id=patient+'-'+name,patient_id=patient,kind=kind,
            record_schema='2.1.0' if kind in ('protocol_snapshot','support_decision') else '2.0.0',
            event_at=at,recorded_at=at,available_at=at,lineage_id=patient+'-'+name,
            revision=1,supersedes=None,duplicate_of=None,record_status='active')
        header.update(fields);return ADAPTER.validate_python(header)
    eligibility=[dict(action=a,status='eligible',reasons=[]) for a in ('support_prompt','no_prompt')]
    def snapshot(name,at,eligible):
        return record('decision_snapshot',name,at,cutoff=at,eligibility=eligible,
            workflow=dict(clinical='treatment_active',learning='support_active',data_readiness='ready',
                hold_reasons=[],support_policy=POLICY,support_mode='adaptive'))
    consent=record('consent','consent',ORIGIN,component='mrt_bandit',consent_status='active',
        oversight_status='approved_synthetic',effective_at=ORIGIN,expires_at=None,withdrawn_at=None)
    initial=snapshot('initial-context',ORIGIN,[dict(action='behavioral_continue',status='eligible',reasons=[]),*eligibility])
    approved=record('approval','initial-binary',ORIGIN,decision_id=initial.record_id,option=None,
        permitted_options=['support_prompt','no_prompt'],purpose='randomization_protocol')
    background_approval=record('approval','background-approval',ORIGIN,decision_id=initial.record_id,
        option='behavioral_continue',permitted_options=[],purpose='ordinary_treatment')
    background=record('assignment','background',ORIGIN,decision_id=initial.record_id,approval_id=background_approval.record_id,
        option='behavioral_continue',experimental=False,component=None,probability=None,support_policy=FIXED_SUPPORT_REF,
        patient_blinded=False,clinician_blinded=False,clinician_override=None,override_reason=None)
    activated=ORIGIN+timedelta(days=activation_day)
    activation=record('protocol_snapshot','activation',activated,family='support',protocol=SUPPORT_REF,template=SUPPORT_REF,
        consent_refs=[ref(consent)],approval_refs=[ref(approved)],background_ref=ref(background),support_refs=[],activation_at=activated)
    records.extend([consent,initial,approved,background_approval,background,activation])
    reports={};reward_status={}
    for t in range(1,day+1):
        status=statuses.get(t,'missing' if all_missing or t in (2,14,day) else 'pending' if t==5 else 'undefined' if t==6 else 'observed')
        reward_status[t]=status;at=ORIGIN+timedelta(days=t,minutes=-1)
        report=record('daily_report','quality-'+str(t),at,sleep_quality=(0. if t==1 else 10. if t==3 else 5.123) if status=='observed' else None,
            missingness='observed' if status=='observed' else 'pending' if status=='pending' else 'missing')
        if late_report==t:
            report=report.model_copy(update=dict(recorded_at=at+timedelta(hours=2),available_at=at+timedelta(hours=2)))
        if correction==t:
            extra_provenance.append(ReducedHeader.model_validate(report.model_dump(include=set(ReducedHeader.model_fields))))
            available=at+timedelta(seconds=20) if t==day else ORIGIN+timedelta(days=t+1,hours=2)
            report=record('daily_report','quality-'+str(t)+'-r2',at,sleep_quality=4.321 if status=='observed' else None,
                missingness=report.missingness,lineage_id=report.lineage_id,revision=2,supersedes=report.record_id,
                recorded_at=available,available_at=available)
        reports[t]=report;records.append(report)
    for t in range(1,day+1):
        at=ORIGIN+timedelta(days=t-1);assessment=ORIGIN+timedelta(days=t,minutes=-1)
        deterministic=t==4;unavailable=t==6 and reward_status[t]=='undefined'
        option='support_prompt' if t%7 in (1,3,6) and not deterministic else 'no_prompt'
        eligible=[dict(action=a,status='excluded' if unavailable or deterministic and a=='support_prompt' else 'eligible',
                       reasons=['UNIT-mask'] if unavailable or deterministic and a=='support_prompt' else []) for a in ('support_prompt','no_prompt')]
        clinical=snapshot('context-'+str(t),at,[dict(action='behavioral_continue',status='eligible',reasons=[]),*eligible])
        if held==t:clinical=clinical.model_copy(update=dict(workflow=clinical.workflow.model_copy(update=dict(clinical='clinical_hold',hold_reasons=['UNIT-hold']))))
        if bad_snapshot==t:clinical=clinical.model_copy(update=dict(cutoff=at+timedelta(seconds=1)))
        approval=record('approval','approval-'+str(t),at,decision_id=clinical.record_id,
            option='no_prompt' if deterministic else None,permitted_options=[] if deterministic else ['support_prompt','no_prompt'],
            purpose='ordinary_treatment' if deterministic else 'randomization_protocol')
        if bad_approval==t:approval=approval.model_copy(update=dict(purpose='ordinary_treatment',option='no_prompt',permitted_options=[]))
        p=0. if deterministic or unavailable else .25
        assignment=None
        if not unavailable:
            assignment=record('assignment','assignment-'+str(t),at,decision_id=clinical.record_id,approval_id=approval.record_id,
                option=option,experimental=not deterministic,component=None if deterministic else 'mrt_bandit',
                probability=None if deterministic else p if option=='support_prompt' else 1-p,
                support_policy=POLICY,patient_blinded=False,clinician_blinded=False,clinician_override=None,override_reason=None)
            if bad_probability==t:assignment=assignment.model_copy(update=dict(probability=.123))
        context=[ref(r) for r in records if r.kind in ('daily_report','delivery') and r.available_at<at]
        if missing_feature==t:context=[]
        context.sort(key=lambda r:r['record_id'])
        decision=record('support_decision','support-'+str(t),at,decision_snapshot=ref(clinical),decision_index=t-1,
            cutoff=at,context=context,context_projection_sha256=sha(context),policy=POLICY,mode='adaptive',eligibility=eligible,
            policy_constraint=dict(allowed_actions=['support_prompt','no_prompt'],reason='unrestricted',snapshot_ref=None),
            availability='unavailable' if unavailable else 'deterministic' if deterministic else 'randomized',
            unavailable_reasons=['UNIT-unavailable'] if unavailable else [],
            probabilities=dict(support_prompt=p,no_prompt=0. if unavailable else 1-p),
            assignment_id=None if assignment is None else assignment.record_id,distribution_persisted_at=at,
            execution_receipt_id=patient+'-execution-'+str(t),
            outcome_window=dict(id=patient+'-window-'+str(t),starts_at=at,ends_at=assessment,assessment_at=assessment,
                timezone='UTC',local_date=at.date(),endpoint_definition=reference('UNIT-quality','next-morning .001 quality')),
            outcome_link_id=patient+'-outcome-'+str(t))
        publication=max(assessment+timedelta(seconds=2),reports[t].available_at+timedelta(seconds=1))
        outcome=record('support_outcome_link','outcome-'+str(t),assessment,recorded_at=publication,available_at=publication,
            support_decision=ref(decision),assignment_ref=None if assignment is None else ref(assignment),
            window_id='UNIT-wrong-window' if bad_window==t else decision.outcome_window.id,assessment_at=assessment,evaluated_as_of=publication,
            reward=dict(status=reward_status[t],report_ref=ref(reports[t]) if reward_status[t]=='observed' else None,
                field='sleep_quality',unit='quality_points',reason=None if reward_status[t]=='observed' else 'UNIT-'+reward_status[t],
                evidence_refs=[] if reward_status[t]=='observed' else [ref(reports[t])],definition_refs=[]),
            burden=[dict(definition=reference('UNIT-burden','not a covariate'),type=name,unit='count',status='pending',value=None,source_refs=[])
                for name in ('offered_prompt_count','delivered_prompt_count')],offered_closure_ref=None,delivered_closure_ref=None)
        records.extend([clinical,approval,decision,outcome])
        if assignment is not None:
            records.append(assignment)
            if option=='support_prompt':records.append(record('delivery','delivered-'+str(t),at+timedelta(hours=8),
                assignment_id=assignment.record_id,option=option,stage='delivered',adherence=None,rescue=False,protocol_deviations=[]))
        if duplicate_outcome==t:
            records.append(outcome.model_copy(update=dict(record_id=outcome.record_id+'-duplicate',lineage_id=outcome.record_id+'-duplicate')))
    return ProtocolHistory.model_validate(dict(schema_version='2.0.0',synthetic=True,kind='poc_protocol_history',
        version='poc-analysis-history-v1-protocol-v2',patient_id=patient,family='support',cutoff=ORIGIN+timedelta(days=day),origin=ORIGIN,
        protocol=SUPPORT_REF,records=records,provenance=[ReducedHeader.model_validate(r.model_dump(include=set(ReducedHeader.model_fields))) for r in records]+extra_provenance))


def cohort(day=14,*,target_missing=False,all_missing=False,member_change=None):
    return tuple(history(f'UNIT-S2-{i:02}',day,all_missing=all_missing or target_missing and i==7,
                         **(member_change or {}) if i==0 else {}) for i in range(12))


def provenance(histories,target='UNIT-S2-07'):
    members=[]
    for h in histories:
        snapshot=next(r for r in h.records if r.kind=='protocol_snapshot')
        members.append(dict(patient_id=h.patient_id,patient_version=1,history_sha256=sha(h.model_dump(mode='json')),
            revisions_sha256=sha([r.model_dump(mode='json') for r in sorted(h.provenance,key=lambda r:r.record_id)]),
            source_projection_sha256=sha(dict(scope='UNIT structural projection identity',patient=h.patient_id)),activation_ref=ref(snapshot)))
    return S2FitProvenance.model_validate(dict(schema_version='s2-fit-source-1.0.0',purpose='EST-POLICY:poc-support-refresh-v1',synthetic=True,
        owner_id='UNIT-owner',store_id='UNIT-store',generation_id='UNIT-generation',cohort_id='UNIT-predeclared12',export_id='UNIT-export',
        source_commit='0'*40,target_id=target,origin=histories[0].origin,cutoff=histories[0].cutoff,
        cutoff_day=(histories[0].cutoff-histories[0].origin).days,members=tuple(members),
        membership_sha256=sha(members),histories_sha256=sha([h.model_dump(mode='json') for h in histories]),
        law=LAW_REF,protocol=SUPPORT_REF,hstar=HSTAR_REF,configuration=CONFIG_REF,definitions=DEFINITIONS,serving_authority=False))
