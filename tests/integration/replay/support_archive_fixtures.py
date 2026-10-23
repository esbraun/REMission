"""Hand-authored one-window structural proofs; no producer or numerical import.

The 84-day descriptor shape and 72 projection slots are interface fixtures,
never a generated panel, scientific output or accepted invocation qualification.
"""
from datetime import datetime,timedelta,timezone
import json

from contracts.domain.analysis import FIXED_SUPPORT_REF, reference
from contracts.domain.evidence_v2 import exact_ref,projection_hash
from contracts.domain.protocol import LAW_REF,SUPPORT_REF,ObservedHistoryV21,RECORD_ADAPTER_V21
from contracts.domain.protocol_request import S1_ESTIMAND,IDENTITIES
from contracts.runs.common import Artifact,RESTRICTED,canonical,sha256
from contracts.runs.coverage_v2 import StageLedgerV2
from contracts.runs.support_research import SupportArchiveAuthority,SupportCompletion,SupportRuntime,StageVerifier,version_ref
from services.foundation.protocol import project_protocol

START=datetime(2026,1,1,12,tzinfo=timezone.utc)
WALL=datetime(2026,10,22,12,tzinfo=timezone.utc)
REF=reference('structural-support-fixture','Hand-authored structural fixture only')
SOURCE='a'*40
PLAN='b'*64


def record(patient,name,at,kind,*,schema='1.0.0',published=None,**fields):
    value=dict(schema_version=schema,synthetic=True,record_id=name,patient_id=patient,event_at=at.isoformat(),
        recorded_at=(published or at).isoformat(),available_at=(published or at).isoformat(),
        lineage_id=name,revision=1,supersedes=None,duplicate_of=None,record_status='active',kind=kind,**fields)
    observed=kind in ('delivery','daily_report')
    value['source']=dict(id=LAW_REF['id'] if observed else REF['id'],version='2.0.0' if observed else '1.0.0',
        adapter='patient_report' if kind=='daily_report' else 'simulation' if observed else 'research_configuration',raw_sha256=sha256(canonical(value)))
    return RECORD_ADAPTER_V21.validate_json(canonical(value))


def history(patient,records):
    return ObservedHistoryV21(schema_version='2.1.0',synthetic=True,kind='observed_history',patient_id=patient,records=records)


def snapshot(patient,name,at,policy,mode,eligibility):
    return record(patient,name,at,'decision_snapshot',cutoff=at.isoformat(),patient_version=1,state_version=1,
        consent_version=1,eligibility_version=1,workflow=dict(clinical='treatment_active',learning='support_active',
        data_readiness='ready',hold_reasons=[],support_policy=policy,support_mode=mode),view=dict(patient_id=patient,mode='current',snapshot_id=None),
        eligibility=eligibility,outcome='quality',horizon_days=1,estimand=S1_ESTIMAND,model=IDENTITIES['S1-WCLS']['model'],posterior=None,evidence=[REF],policy=REF)


def approval(patient,name,at,snapshot,option=None):
    return record(patient,name,at,'approval',decision_id=snapshot.record_id,option=option,
        permitted_options=[] if option else ['support_prompt','no_prompt'],clinician_id='structural-fixture',
        purpose='ordinary_treatment' if option else 'randomization_protocol',expected_patient_version=1,
        expected_state_version=1,expected_consent_version=1,expected_eligibility_version=1)


def assignment(patient,name,at,snapshot,approval,option,policy,randomized=False):
    return record(patient,name,at,'assignment',decision_id=snapshot.record_id,approval_id=approval.record_id,option=option,
        experimental=randomized,component='mrt_bandit' if randomized else None,probability=.5 if randomized else None,
        seed=dict(namespace='assignment',protocol=SUPPORT_REF['id'],scenario='fixture',replicate=0,patient=patient,time_index=0,process='fixture') if randomized else None,
        support_policy=policy,patient_blinded=False,clinician_blinded=False,clinician_override=None,override_reason=None)


def build(root):
    profile=RESTRICTED['runtime_profile']
    runtime=SupportRuntime.model_validate_json(canonical(dict(image_sha256='c'*64,
        numerical_lock=dict(id='fixture-numerical-lock',version='1',sha256=profile['numerical_lock_sha256']),
        service_lock=dict(id='fixture-service-lock',version='1',sha256=profile['service_lock_sha256']),
        python_version='3.13.0',numpy_version='2.5.4',prng=profile['prng'],seed_derivation='poc-support-research-map-v1',precision='float64')))
    def write(name,path,value,role='observed'):
        raw=canonical(value);target=root/path;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
        return Artifact(id=name,path=path,sha256=sha256(raw),bytes=len(raw),role=role,media_type='application/json')
    members=[f'STRUCT-{i:02d}' for i in range(12)];trajectories=[];supplemental=[]
    for patient in members:
        for mode in ('S0','S1'):
            partition=patient+'-'+mode;policy=FIXED_SUPPORT_REF if mode=='S0' else SUPPORT_REF
            consent=record(patient,'consent',START-timedelta(seconds=50),'consent',component='mrt_bandit',
                consent_version='fixture',oversight_version='fixture',consent_status='active',oversight_status='approved_synthetic',
                effective_at=(START-timedelta(seconds=50)).isoformat(),expires_at=None,withdrawn_at=None)
            initial=snapshot(patient,'initial',START-timedelta(seconds=40),FIXED_SUPPORT_REF,'fixed',
                [dict(action=a,status='eligible',reasons=[]) for a in ('support_prompt','no_prompt','behavioral_continue')])
            binary=approval(patient,'binary',START-timedelta(seconds=39),initial)
            bgapproval=approval(patient,'bgapproval',START-timedelta(seconds=39),initial,'behavioral_continue')
            background=assignment(patient,'background',START-timedelta(seconds=38),initial,bgapproval,'behavioral_continue',FIXED_SUPPORT_REF)
            records=[consent,initial,binary,bgapproval,background];frozen=None
            if mode=='S0':
                frozen=record(patient,'frozen',START-timedelta(seconds=30),'protocol_snapshot',schema='2.1.0',family='support',
                    protocol=SUPPORT_REF,template=SUPPORT_REF,consent_refs=[exact_ref(consent).model_dump()],approval_refs=[exact_ref(binary).model_dump()],
                    background_ref=exact_ref(background).model_dump(),support_refs=[],activation_at=(START-timedelta(seconds=30)).isoformat())
                records.append(frozen)
            before=history(patient,records);eligibility=[dict(action=a,status='excluded' if mode=='S0' and a=='support_prompt' else 'eligible',
                reasons=['fixed_no_prompt'] if mode=='S0' and a=='support_prompt' else []) for a in ('support_prompt','no_prompt')]
            snap=snapshot(patient,'snapshot',START,policy,'fixed' if mode=='S0' else 'mrt',eligibility)
            app=approval(patient,'approval',START,snap,'no_prompt' if mode=='S0' else None)
            assessment=START+timedelta(days=1,minutes=-1)
            decision=record(patient,'decision',START,'support_decision',schema='2.1.0',decision_snapshot=exact_ref(snap).model_dump(),
                decision_index=0,cutoff=START.isoformat(),context=[],context_projection_sha256=projection_hash(before,START),context_mapping=REF,
                policy=policy,mechanism=SUPPORT_REF,mode='fixed' if mode=='S0' else 'mrt',eligibility=eligibility,
                policy_constraint=dict(allowed_actions=['no_prompt'] if frozen else ['support_prompt','no_prompt'],
                    reason='fixed_no_prompt' if frozen else 'unrestricted',snapshot_ref=exact_ref(frozen).model_dump() if frozen else None),
                availability='deterministic' if mode=='S0' else 'randomized',unavailable_reasons=[],
                probabilities=dict(support_prompt=0. if mode=='S0' else .5,no_prompt=1. if mode=='S0' else .5),probability_tolerance=1e-12,
                assignment_id='assignment',distribution_persisted_at=START.isoformat(),execution_receipt=REF,
                outcome_window=dict(id='window',starts_at=START.isoformat(),ends_at=assessment.isoformat(),assessment_at=assessment.isoformat(),
                    timezone='UTC',local_date=START.date().isoformat(),endpoint_definition=REF),outcome_link_id='outcome')
            assign=assignment(patient,'assignment',START,snap,app,'no_prompt' if mode=='S0' else 'support_prompt',policy,mode=='S1')
            predecision=write(patient+'-predecision',partition+'/predecision.json',dict(support_decision=decision.model_dump(mode='json'),
                decision_snapshot=snap.model_dump(mode='json'),approval=app.model_dump(mode='json'),context=[]))
            supplemental.append(dict(partition_id=partition,artifact=predecision.model_dump(mode='json')))
            records.extend([snap,app,decision,assign]);delivery_at=START+timedelta(hours=8)
            events=[record(patient,'event-'+stage,delivery_at,'delivery',assignment_id='assignment',option='support_prompt',stage=stage,
                adherence=None if stage=='offered' else 1.,rescue=False,protocol_deviations=[]) for stage in ('offered','delivered')] if mode=='S1' else []
            # Original producer event IDs repeat across paired partitions;
            # artifact paths and receipt partition bindings disambiguate them.
            records.extend(events);artifact=write(patient+'-events',partition+'/events.json',[r.model_dump(mode='json') for r in events])
            ledgers=[StageLedgerV2.model_validate_json(canonical(dict(schema_version='2.0.0',synthetic=True,kind='support_stage_ledger',id=stage,
                run_id='structural-run',partition_id=partition,patient_id=patient,decision_index=0,window_id='window',stage=stage,rule=REF,
                event_refs=[exact_ref(r).model_dump() for r in events if r.stage==stage]))) for stage in ('offered','delivered')]
            completed=delivery_at+timedelta(seconds=1);available=completed+timedelta(seconds=1)
            receipt=SupportCompletion.model_validate_json(canonical(dict(version='poc-support-stage-completion-v1',id='completion',run_id='structural-run',
                partition_id=partition,patient_id=patient,source_commit=SOURCE,runtime=runtime.model_dump(mode='json'),frozen_plan_sha256=PLAN,status='complete',reason=None,
                stage_ledgers=[version_ref(r).model_dump() for r in ledgers],output_artifacts=[artifact.model_dump(mode='json')],output_counts=dict(stage_events=len(events)),
                simulated_completed_through=completed.isoformat(),simulated_available_at=available.isoformat(),execution_started_at=WALL.isoformat(),execution_ended_at=WALL.isoformat(),published_at=WALL.isoformat())))
            closures=[record(patient,'closure-'+ledger.stage,completed,'support_stage_closure',schema='2.0.0',published=available,
                run_id='structural-run',partition_id=partition,support_decision=exact_ref(decision).model_dump(),assignment_ref=exact_ref(assign).model_dump(),
                window_id='window',decision_index=0,stage=ledger.stage,rule=REF,stage_completed_at=completed.isoformat(),status='complete',
                stage_event_refs=[r.model_dump() for r in ledger.event_refs],stage_ledger=version_ref(ledger).model_dump(),row_count=len(ledger.event_refs),
                reason='Hand-authored structural completion',completion_receipt=version_ref(receipt).model_dump()) for ledger in ledgers]
            report=record(patient,'report',assessment,'daily_report',sleep_quality=6.,function=5.,adverse_symptoms=[],diary_sleep_minutes=360.,goals=[],burden=1.,missingness='observed')
            outcome=record(patient,'outcome',assessment,'support_outcome_link',schema='2.0.0',published=assessment+timedelta(seconds=20),
                support_decision=exact_ref(decision).model_dump(),assignment_ref=exact_ref(assign).model_dump(),window_id='window',assessment_at=assessment.isoformat(),
                evaluated_as_of=(assessment+timedelta(seconds=10)).isoformat(),reward=dict(status='observed',report_ref=exact_ref(report).model_dump(),field='sleep_quality',
                    unit='quality_points',reason=None,evidence_refs=[exact_ref(report).model_dump()],definition_refs=[]),
                burden=[dict(definition=REF,type=stage+'_prompt_count',unit='count',status='observed',value=0 if mode=='S0' else 1,
                    source_refs=[exact_ref(r).model_dump() for r in events if r.stage==stage]) for stage in ('offered','delivered')],
                offered_closure_ref=exact_ref(closures[0]).model_dump(),delivered_closure_ref=exact_ref(closures[1]).model_dump())
            later_reports=[record(patient,'report-'+str(day),START+timedelta(days=day,minutes=-1),'daily_report',
                sleep_quality=None,function=None,adverse_symptoms=[],diary_sleep_minutes=None,goals=[],burden=None,missingness='missing') for day in range(2,85)]
            full=history(patient,[*records,*closures,report,outcome,*later_reports])
            verifier=StageVerifier(full,ledgers,[receipt],root,run_id='structural-run',partition_id=partition,source_commit=SOURCE,runtime=runtime,frozen_plan_sha256=PLAN)
            projections={str(day):write(partition+'-'+str(day),partition+f'/day-{day}.json',project_protocol(full,START+timedelta(days=day),family='support',origin=START,verify_closure=verifier).model_dump(mode='json')).model_dump(mode='json') for day in (14,42,84)}
            trajectories.append(dict(member_id=patient,paired_member_id='pair-'+patient,mode=mode,partition_id=partition,
                history=write(partition+'-history',partition+'/history.json',full.model_dump(mode='json')).model_dump(mode='json'),projections=projections,
                stage_ledgers=write(partition+'-ledgers',partition+'/ledgers.json',[r.model_dump(mode='json') for r in ledgers],'configuration').model_dump(mode='json'),
                completions=write(partition+'-completions',partition+'/completions.json',[receipt.model_dump(mode='json')],'configuration').model_dump(mode='json')))
    index=dict(version='poc-support-research-v1',synthetic=True,execution='historical-research-only',run_id='structural-run',cohort_id='structural-cohort',members=members,
        origin=START.isoformat(),horizon=84,cuts=[14,42,84],law=LAW_REF,protocol=SUPPORT_REF,estimand=S1_ESTIMAND,source_commit=SOURCE,
        generator_sources={k:'d'*64 for k in ('restricted.py','restricted_v2.py','research_support.py')},runtime=runtime.model_dump(mode='json'),
        frozen_plan_sha256=PLAN,private_recipe_sha256='e'*64,shared_pair_sha256='f'*64,trajectories=trajectories)
    timing=write('structural-timing','generation-timing.json',dict(scope='hand-authored structural fixture; no measured generation'))
    supplemental.append(dict(partition_id=None,artifact=timing.model_dump(mode='json')))
    raw=canonical(index);(root/'manifest.json').write_bytes(raw)
    authority=SupportArchiveAuthority.model_validate_json(canonical(dict(kind='restricted_support_archive',manifest_sha256=sha256(raw),descriptor=index,
        producer_qualification=REF,outcome_qualification=REF,qualification_scope='structural_fixture',supplemental_public_artifacts=supplemental)))
    return raw,root,authority
