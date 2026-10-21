"""Hand-authored CONTRACT fixtures only: no generator, calibration or truth run."""
import json
import platform
from pathlib import Path

from contracts.domain.boundaries import ObservedHistory
from contracts.runs.common import Authority, ExportAuthority, canonical, sha256
from contracts.runs.export import SOURCES, bindings_data
from contracts.runs.observed import ObservedExport, ReplayBatch
from contracts.runs.private import RunManifest, RunResult, SeedLedger, StreamKey
from contracts.dgp.truth import seed_words

ROOT=Path(__file__).resolve().parents[2]
BASE='69e6ae9dc5bf85ddbf39976d2ce4ce70bce1ea1e'
CUTOFF='2026-10-21T12:00:00Z'


def load(model,value):return model.model_validate_json(canonical(value))


def artifact(root,identifier,path,value,role,media_type='application/json'):
    raw=value if isinstance(value,bytes) else canonical(value)
    target=root/path;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
    return dict(id=identifier,path=path,sha256=sha256(raw),bytes=len(raw),role=role,media_type=media_type)


def full_key(patient='SYN-02',scenario='S01.reference.n60',namespace='measurement',phase='fixture',**overrides):
    args=dict(root_seed=20261020,protocol='remission-g1-v1',phase=phase,namespace=namespace,scenario=scenario,replicate=0,patient=patient,time_index=0,process='contract_fixture_measurement',stream='error')
    args.update(overrides)
    words=seed_words(**args)
    return dict(**args,words=words,key_sha256=b''.join(w.to_bytes(4,'little') for w in words).hex())


def runtime():
    manifest=json.loads((ROOT/'docs/implementation/evidence/G1-FOUNDATION-20261021/build-source-and-images.json').read_text(encoding='utf-8'))
    def ref(name,path):return dict(id=name,version='20261021',sha256=sha256((ROOT/path).read_bytes().replace(b'\r\n',b'\n')))
    return dict(image_sha256=manifest['images']['runtime'].removeprefix('sha256:'),numerical_lock=ref('numerical-lock','tooling/library/requirements.lock'),service_lock=ref('service-lock','tooling/foundation/requirements.lock'),python_version=platform.python_version(),numpy_version='2.5.4',prng='PCG64DXSM',seed_derivation='remission-seed-v1',precision='float64')


def wire_investigation(counts,*,request_hash='a'*64,truth_hash='b'*64):
    """Explicit caller fixture authority: never production investigation evidence."""
    from contracts.runs.probability import COMPONENTS, IIDInvestigationAuthority, truth_diagnostics
    stats=truth_diagnostics(counts,conditional=False)
    producer=dict(id='contract-fixture-investigator',version='1.0.0',role='contract_fixture')
    qualification=dict(id='wire-fixture-NOT-producer-qualified',version='1.0.0',sha256='f'*64)
    data=dict(kind='iid_dispersion_investigation',execution='contract_fixture',producer=producer,source_commit=BASE,runtime=runtime(),producer_qualification=qualification,request_sha256=request_hash,truth_evidence_sha256=truth_hash,raw_counts_sha256=sha256(canonical(counts.tolist())),independent_unit='iid_paired_path',independent_units=len(counts)*10000,batches=len(counts),batch_size=10000,component_order=list(COMPONENTS),mean=stats['mean'].tolist(),batch_mcse=stats['mcse'].tolist(),pooled_iid_mcse=stats['pooled_iid_mcse'].tolist(),batch_covariance=stats['covariance'].tolist(),disposition='resolved',method=dict(id='wire-fixture-diagnostic',version='1.0.0',sha256='e'*64),rationale='Hand-authored deterministic contract fixture; diagnostic wire binding only, no independent producer execution or statistical qualification.')
    raw=canonical(data);authority=load(IIDInvestigationAuthority,dict(sha256=sha256(raw),producer=producer,source_commit=BASE,runtime=runtime(),producer_qualification=qualification,allow_contract_fixture=True))
    return raw,authority,request_hash,truth_hash


def workloads():
    return dict(calibration_patients=200000,source_shift_pilot_trials=1000,source_shift_trial_size=200,comparator_pilot_trials=1000,source_comparator_sizes=[30,150,180,200,220,250],truth_batch_size=10000,truth_batch_cap=1000,smoke_repetitions_per_cell=5,catalog_cells=82,conditional_particle_levels=[1024,4096,16384,65536],conditional_filters_per_level=32,distribution_patients=10000)


def observation(patient):
    identifier='record-'+patient
    payload=dict(schema_version='1.0.0',synthetic=True,kind='daily_report',record_id=identifier,patient_id=patient,
        event_at='2026-10-21T07:00:00Z',recorded_at='2026-10-21T08:01:00Z',available_at=CUTOFF,
        lineage_id=identifier,revision=1,supersedes=None,duplicate_of=None,record_status='active',
        sleep_quality=6.0,function=5.0,adverse_symptoms=[],diary_sleep_minutes=360.0,goals=[],burden=1.0,missingness='observed')
    raw=canonical(payload).decode()
    payload['source']=dict(id='contract-observed-fixture',version='1.2.0',adapter='simulation',raw_sha256=sha256(raw.encode()))
    return dict(record=payload,raw_source=raw)


def setup(root: Path,*,complete=False,cell='S01.reference.n60'):
    bindings=bindings_data();inputs=[]
    for name,(identifier,_,source) in SOURCES.items():
        if name=='dgp':continue
        suffix=Path(source).suffix
        inputs.append(artifact(root,identifier,'configuration/'+identifier+suffix,(ROOT/source).read_bytes().replace(b'\r\n',b'\n'),'configuration','text/markdown' if suffix=='.md' else 'application/json'))
    patients=['SYN-02','SYN-B01',*[f'CONTRACT-{i:02d}' for i in range(58)]]
    producer=dict(id='contract-fixture-producer',version='1.0.0',role='contract_fixture')
    run=load(RunManifest,dict(schema_version='1.0.0',synthetic=True,kind='generator_run_manifest',contract_version='1.0.0',
        run_id='contract-run',producer=producer,execution='contract_fixture',source_commit=BASE,runtime=runtime(),bindings=bindings,
        input_sha256=sha256(canonical(inputs)),inputs=inputs,root_seed=20261020,phase='fixture',scope='cell_batch',cutoff=CUTOFF,created_at=CUTOFF,
        units=[dict(id='unit-one',cell_id=cell,catalog_patients=60,preset='catalog_cell',evaluation_configuration=None,repetitions=1,
            cohorts=[dict(id='historical',role='historical',patients=[dict(id=p,replicate=0) for p in patients])])],required_workloads=workloads(),
        sources=[dict(id='contract-observed-fixture',version='1.2.0',adapter='simulation')]))
    run_raw=canonical(run.model_dump(mode='json'))
    authority=load(Authority,dict(run_id=run.run_id,producer=producer,manifest_sha256=sha256(run_raw),source_commit=BASE,runtime=runtime(),allow_contract_fixture=True))
    run_ref=dict(id=run.run_id,version='1.0.0',sha256=sha256(run_raw));partitions=[];keys=[]
    for index,patient in enumerate(patients if complete else patients[:2]):
        entry=observation(patient);key=full_key(patient,scenario=cell);keys.append(key)
        history=load(ObservedHistory,dict(schema_version='1.0.0',synthetic=True,kind='observed_history',patient_id=patient,records=[entry['record']]))
        batch=load(ReplayBatch,dict(schema_version='1.0.0',synthetic=True,kind='observed_replay_batch',contract_version='1.0.0',run_id=run.run_id,partition_id=f'partition-{index}',patient_id=patient,entries=[entry]))
        partition=dict(id=f'partition-{index}',unit_id='unit-one',cell_id=cell,preset='catalog_cell',cohort_id='historical',replicate=0,patient_id=patient,
            history=artifact(root,f'history-{index}',f'observed/{run.run_id}/partition-{index}.json',history.model_dump(mode='json'),'observed'),
            replay=artifact(root,f'replay-{index}',f'replay/{run.run_id}/partition-{index}.json',batch.model_dump(mode='json'),'replay'),
            records=[dict(record_id=history.records[0].record_id,payload_sha256=sha256(canonical(history.records[0].model_dump(mode='json'))),source=history.records[0].source.model_dump(mode='json'),seed_key_sha256=key['key_sha256'],import_to_event_store=True,exclusion_reason=None)])
        partitions.append(partition)
    export=load(ObservedExport,dict(schema_version='1.0.0',synthetic=True,kind='observed_export',contract_version='1.0.0',id='export-one',run_id=run.run_id,run_manifest=run_ref,
        producer=producer,execution='contract_fixture',source_commit=BASE,runtime=runtime(),bindings=bindings,cutoff=CUTOFF,created_at=CUTOFF,status='complete' if complete else 'partial',partitions=partitions))
    export_raw=canonical(export.model_dump(mode='json'))
    export_artifact=artifact(root,'export-one','exports/contract-run/export-one.json',export_raw,'observed_manifest')
    seed_artifact=artifact(root,'seed-ledger','seeds/contract-run/ledger.json',load(SeedLedger,dict(schema_version='1.0.0',synthetic=True,kind='seed_ledger',contract_version='1.0.0',run_id=run.run_id,keys=keys)).model_dump(mode='json'),'seed_ledger')
    result=load(RunResult,dict(schema_version='1.0.0',synthetic=True,kind='generator_run_result',contract_version='1.0.0',run_id=run.run_id,run_manifest=run_ref,
        producer=producer,execution='contract_fixture',source_commit=BASE,runtime=runtime(),status='complete' if complete else 'partial',reason=None if complete else 'Only two hand-authored contract patients; full generator not executed',
        observed_exports=[export_artifact],private_truth=[],seed_ledger=seed_artifact,calibration=[],reports=[]))
    export_authority=load(ExportAuthority,dict(**authority.model_dump(mode='json'),export_id=export.id,export_sha256=sha256(export_raw)))
    return dict(run=run,run_raw=run_raw,authority=authority,export=export,export_raw=export_raw,export_authority=export_authority,result=result,result_raw=canonical(result.model_dump(mode='json')))
