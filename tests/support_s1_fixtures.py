"""Scalar structural fixtures only. No producer admission or fitted estimate."""
from datetime import datetime,timedelta,timezone
from contracts.domain.analysis import canonical,sha
from contracts.domain.protocol_analysis import ProtocolHistory
from contracts.domain.support_s1 import (S1Input,S1Result,CONFIG_REF,MODEL_REF,
    S1_ESTIMAND,WCLS_PRIOR_REF,LAW_REF,SUPPORT_REF,consumed_ids,execution_binding)

ORIGIN=datetime(2026,1,1,12,tzinfo=timezone.utc)
WALL=datetime(2026,10,23,12,tzinfo=timezone.utc)
HOST=dict(learner_image='sha256:'+'a'*64,source_commit='b'*40)


def product(day=14):
    histories=[];members=[]
    for n in range(12):
        patient=f'S1-SHAPE-{n:02d}';records=[]
        for night in range(1,day+1):
            at=(ORIGIN+timedelta(days=night,minutes=-1)).isoformat();key=f'{patient}-report-{night}'
            records.append(dict(record_id=key,patient_id=patient,kind='daily_report',record_schema='1.0.0',
                event_at=at,recorded_at=at,available_at=at,lineage_id=key,revision=1,supersedes=None,
                duplicate_of=None,record_status='active',sleep_quality=6.,missingness='observed'))
        h=dict(schema_version='2.0.0',synthetic=True,kind='poc_protocol_history',
            version='poc-analysis-history-v1-protocol-v2',patient_id=patient,family='support',
            cutoff=(ORIGIN+timedelta(days=day)).isoformat(),origin=ORIGIN.isoformat(),protocol=SUPPORT_REF,
            records=records,provenance=[{k:v for k,v in r.items() if k not in ('sleep_quality','missingness')} for r in records])
        h=ProtocolHistory.model_validate_json(canonical(h)).model_dump(mode='json')
        histories.append(h);members.append(dict(patient_id=patient,patient_version=1,partition_id=patient+'-S1',
            projection_sha256='c'*64,history_sha256=sha(h)))
    return S1Input.model_validate_json(canonical(dict(schema_version='3.0.0',synthetic=True,
        kind='poc_support_s1_input',purpose='S1-WCLS',attempt_id='analysis-'+'1'*32,
        archive=dict(owner_id='alice',archive_id='structural-run:shape-cohort',run_id='structural-run',
            cohort_id='shape-cohort',manifest_sha256='d'*64,admission_sha256='e'*64,source_commit='f'*40,
            producer_runtime={'scope':'structural-shape-only'},producer_qualification={'scope':'not-admitted'},
            outcome_qualification={'scope':'not-admitted'}),mode='S1',cutoff_day=day,
        cutoff=histories[0]['cutoff'],cohort=members,histories=histories,history_sha256=sha(histories),
        configuration=CONFIG_REF,model=MODEL_REF,prior=WCLS_PRIOR_REF,estimand=S1_ESTIMAND,
        law=LAW_REF,protocol=SUPPORT_REF,provenance_seed='fit/wcls-unused-provenance/structural-shape')))


def abstention(p,*,status='abstained'):
    return S1Result.model_validate_json(canonical(dict(schema_version='3.0.0',synthetic=True,
        kind='poc_support_s1_result',purpose='S1-WCLS',attempt_id=p.attempt_id,
        input_sha256=sha(p.model_dump(mode='json')),history_sha256=p.history_sha256,
        feature_history_sha256=None,archive=p.archive.model_dump(),cohort=[m.model_dump() for m in p.cohort],
        cutoff=p.cutoff.isoformat(),configuration=CONFIG_REF,model=MODEL_REF,prior=WCLS_PRIOR_REF,
        estimand=S1_ESTIMAND,protocol=SUPPORT_REF,status=status,reason='structural no-estimate fixture',
        consumed_record_ids=consumed_ids(p),generated_at=WALL.isoformat(),
        diagnostics=dict(execution=execution_binding(p,HOST),timings=dict(import_seconds=0.,feature_seconds=0.,
            estimator_seconds=0.,worker_seconds=0.)),artifacts=[],output=None,
        limitations=['Structural result adapter fixture only; no estimator executed.'])))
