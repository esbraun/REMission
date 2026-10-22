"""Private, bounded n12 reference producer. No authority or fitted result is issued.

Prepare one immutable through42 trajectory, then two public observed projections.
Production callers must separately qualify the frozen source/runtime and supply
independent ExportAuthority to the existing admit_export/replay host boundary.
"""
import argparse
from datetime import timedelta
import hashlib
import json
from pathlib import Path
from typing import Annotated, Literal

from pydantic import AwareDatetime, Field, TypeAdapter, model_validator
from contracts.domain.analysis import FIXED_SUPPORT_REF, project_history
from contracts.domain.boundaries import ObservedHistory
from contracts.domain.common import StrictModel
from contracts.dgp.truth import seed_words
from contracts.runs.common import RESTRICTED, RESTRICTED_CELL, RuntimeProfile, Token, canonical, sha256, unique
from contracts.runs.observed import INGESTIBLE, ObservedExport, ReplayBatch
from contracts.runs.private import RunManifest, SeedLedger, StreamKey
from .restricted import START, generate, uniform

MAPPING='poc-restricted-adapter-map-v1'


class ResearchPlan(StrictModel):
    version: Literal['poc-restricted-research-plan-v1']
    namespace: Annotated[str,Field(min_length=1,max_length=256)]
    run_id: Token
    unit_id: Token
    cohort_id: Token
    created_at: AwareDatetime
    patients: Annotated[list[Token],Field(min_length=12,max_length=12)]

    @model_validator(mode='after')
    def opaque_members(self):
        unique(self.patients,'research member')
        if any(len(p)>90 or not all(c.isalnum() or c in '-_' for c in p) for p in self.patients):
            raise ValueError('restricted adapter patient identifier required')
        return self


def mappings(plan):
    """Full canonical words are derivation inputs, not measurement PRNG words."""
    result=[];seen=set()
    for index,patient in enumerate(plan.patients):
        for domain in ('generation','assignment'):
            args=dict(root_seed=20261020,protocol=RESTRICTED['bindings']['protocol']['id'],phase='development',
                namespace=domain,scenario=RESTRICTED_CELL,replicate=0,patient=patient,time_index=0,
                process='restricted-'+domain,stream='adapter-input')
            words=seed_words(**args)
            key=StreamKey.model_validate(dict(**args,words=words,key_sha256=b''.join(w.to_bytes(4,'little') for w in words).hex()))
            material=dict(namespace=plan.namespace,run_id=plan.run_id,unit_id=plan.unit_id,cohort_id=plan.cohort_id,
                replicate=0,key=key.model_dump(mode='json'))
            digest=sha256(canonical([MAPPING,material,domain]))
            seed=int(digest,16)%2**31
            if seed in seen:raise ValueError('adapter seed collision before generation')
            seen.add(seed)
            result.append(dict(patient_id=patient,index=index,domain=domain,adapter_seed=seed,
                material_sha256=digest,derivation_input=key.model_dump(mode='json')))
    return result


def _write(root, identifier, path, value, role):
    raw=canonical(value);target=root/path;target.parent.mkdir(parents=True,exist_ok=True)
    if any(p.is_symlink() for p in (target,*target.parents) if p!=root and p.is_relative_to(root)):
        raise ValueError('symlink research artifact denied')
    if target.exists():
        if target.is_symlink() or target.read_bytes()!=raw:raise ValueError('immutable research artifact conflict')
    else:
        with target.open('xb') as handle:handle.write(raw)
    return dict(id=identifier,path=path,sha256=sha256(raw),bytes=len(raw),role=role,media_type='application/json')


def _assignment(patient, day, option, initial):
    at=(START+timedelta(days=day)).isoformat();identifier=f'{patient}-assignment-{day}'
    # The public SeedKey is a historical design reference, never adapter seed,
    # full private key, words or a live protocol/physician authorization.
    seed=dict(namespace='assignment',protocol=RESTRICTED['bindings']['protocol']['id'],scenario=RESTRICTED_CELL,
        replicate=0,patient=patient,time_index=0,process='historical-initial-assignment') if initial else None
    envelope=dict(schema_version='1.0.0',synthetic=True,record_id=identifier,patient_id=patient,
        event_at=at,recorded_at=at,available_at=at,lineage_id=identifier,revision=1,supersedes=None,
        duplicate_of=None,record_status='active',kind='assignment',decision_id=identifier+'-historical-design',
        approval_id=identifier+'-historical-protocol',option=option,experimental=initial,
        component='escalation' if initial else None,probability=.5 if initial else None,seed=seed,
        support_policy=FIXED_SUPPORT_REF,patient_blinded=False,clinician_blinded=False,
        clinician_override=None,override_reason=None)
    raw=canonical(envelope).decode()
    envelope['source']=dict(**RESTRICTED['historical_assignment_source'],raw_sha256=sha256(raw.encode()))
    return dict(record=envelope,raw_source=raw)


def _workloads():
    return dict(calibration_patients=200000,source_shift_pilot_trials=1000,source_shift_trial_size=200,
        comparator_pilot_trials=1000,source_comparator_sizes=[30,150,180,200,220,250],truth_batch_size=10000,
        truth_batch_cap=1000,smoke_repetitions_per_cell=5,catalog_cells=82,
        conditional_particle_levels=[1024,4096,16384,65536],conditional_filters_per_level=32,distribution_patients=10000)


def prepare(plan, private_root, staging_root, *, runtime, source_commit):
    """No publication marker/authority is written here; admit_export publishes.

    Caller owns the supplied frozen runtime/source identity. Unit tests may use
    test-only identities; they confer no production qualification or trust.
    """
    plan=ResearchPlan.model_validate_json(canonical(plan))
    runtime=TypeAdapter(RuntimeProfile).validate_json(canonical(runtime))
    if hashlib.sha256(Path(__file__).with_name('restricted.py').read_bytes()).hexdigest()!=RESTRICTED['binding_descriptors']['dgp']['generator_source_sha256']:
        raise ValueError('restricted scientific source bytes differ from frozen profile')
    private_root,staging_root=Path(private_root).resolve(),Path(staging_root).resolve()
    if private_root==staging_root or private_root.is_relative_to(staging_root) or staging_root.is_relative_to(private_root):
        raise ValueError('private archive must be separate from observed staging')
    private_root.mkdir(parents=True,exist_ok=True);staging_root.mkdir(parents=True,exist_ok=True)
    mapping=mappings(plan) # Collision preflight precedes any engine invocation.
    recipe=dict(mapping_id=MAPPING,plan=plan.model_dump(mode='json'),mapping=mapping,
        runtime=runtime.model_dump(mode='json'),source_commit=source_commit,canonical_words='derivation input only')
    config=_write(private_root,'research-private-recipe','configuration/recipe.json',recipe,'configuration')
    evaluation=_write(private_root,RESTRICTED['evaluation_configuration']['reference']['id'],'configuration/evaluation.json',RESTRICTED['evaluation_configuration']['payload'],'configuration')
    descriptors=[_write(private_root,RESTRICTED['bindings'][name]['id'],f'configuration/{name}.json',value,'configuration') for name,value in RESTRICTED['binding_descriptors'].items()]
    inputs=[config,evaluation,*descriptors];through=START+timedelta(days=42)
    run=RunManifest.model_validate_json(canonical(dict(schema_version='1.0.0',synthetic=True,
        kind='generator_run_manifest',contract_version='1.0.0',run_id=plan.run_id,producer=RESTRICTED['producer'],
        execution='engine_run',source_commit=source_commit,runtime=runtime.model_dump(mode='json'),bindings=RESTRICTED['bindings'],
        input_sha256=sha256(canonical(inputs)),inputs=inputs,root_seed=20261020,phase='development',scope='preset',
        cutoff=through.isoformat(),created_at=plan.created_at.isoformat(),units=[dict(id=plan.unit_id,cell_id=RESTRICTED_CELL,
        catalog_patients=12,preset='evaluation',evaluation_configuration=RESTRICTED['evaluation_configuration']['reference'],
        repetitions=1,cohorts=[dict(id=plan.cohort_id,role='prospective',patients=[dict(id=p,replicate=0) for p in plan.patients])])],
        required_workloads=_workloads(),sources=[*RESTRICTED['source'],RESTRICTED['historical_assignment_source']])) )
    run_artifact=_write(private_root,plan.run_id,'run-manifest.json',run.model_dump(mode='json'),'run_manifest')
    ledger=SeedLedger.model_validate_json(canonical(dict(schema_version='1.0.0',synthetic=True,kind='seed_ledger',
        contract_version='1.0.0',run_id=plan.run_id,keys=[m['derivation_input'] for m in mapping])))
    _write(private_root,'research-derivation-inputs','seed-ledger.json',ledger.model_dump(mode='json'),'seed_ledger')
    trajectories={};assignments=[]
    for index,patient in enumerate(plan.patients):
        seeds={m['domain']:m['adapter_seed'] for m in mapping if m['patient_id']==patient}
        draw=uniform(seeds['assignment'],index,0,'initial-assignment')
        option='behavioral_escalate' if draw<.5 else 'behavioral_continue'
        actions=[dict(day=d,option=option,assignment_id=f'{patient}-assignment-{d}') for d in (0,14,28)]
        assignments.append(dict(patient_id=patient,probabilities=[.5,.5],draw=draw,option=option,retain_days=[14,28]))
        output=generate(dict(seed=seeds['generation'],index=index,patient_id=patient,through_day=42,actions=actions))
        trajectories[patient]=output['records']+[_assignment(patient,d,option,d==0) for d in (0,14,28)]
    _write(private_root,'research-assignment-ledger','assignment-ledger.json',dict(assignments=assignments),'configuration')
    _write(private_root,'research-through42','trajectory.json',trajectories,'configuration')
    exports=[]
    for day in (14,42):
        cutoff=START+timedelta(days=day);partitions=[];view=staging_root/f'day-{day}'
        # Private plan order determines adapter indices. Public order/partition
        # identifiers disclose only already-public member/run/cutoff identity.
        for patient in sorted(plan.patients):
            selected=[e for e in trajectories[patient] if all(e['record'][clock]<cutoff.isoformat() for clock in ('event_at','recorded_at','available_at'))]
            history=ObservedHistory.model_validate_json(canonical(dict(schema_version='1.0.0',synthetic=True,
                kind='observed_history',patient_id=patient,records=[e['record'] for e in selected])))
            project_history(history.project(cutoff)) # Enforce the actual reduced-H* boundary before output.
            partition='partition-'+sha256(canonical([plan.run_id,patient,day]))[:24]
            batch=ReplayBatch.model_validate_json(canonical(dict(schema_version='1.0.0',synthetic=True,
                kind='observed_replay_batch',contract_version='1.0.0',run_id=plan.run_id,partition_id=partition,
                patient_id=patient,entries=[e for e in selected if e['record']['kind'] in INGESTIBLE])))
            links=[dict(record_id=r.record_id,payload_sha256=sha256(canonical(r.model_dump(mode='json'))),
                source=r.source.model_dump(mode='json'),seed_key_sha256=None,import_to_event_store=r.kind in INGESTIBLE,
                exclusion_reason=None if r.kind in INGESTIBLE else 'administrative_event_not_live_authority') for r in history.records]
            partitions.append(dict(id=partition,unit_id=plan.unit_id,cell_id=RESTRICTED_CELL,preset='evaluation',
                cohort_id=plan.cohort_id,replicate=0,patient_id=patient,records=links,
                history=_write(view,'history-'+partition,f'observed/{plan.run_id}/{partition}.json',history.model_dump(mode='json'),'observed'),
                replay=_write(view,'replay-'+partition,f'replay/{plan.run_id}/{partition}.json',batch.model_dump(mode='json'),'replay')))
        export=ObservedExport.model_validate_json(canonical(dict(schema_version='1.0.0',synthetic=True,kind='observed_export',
            contract_version='1.0.0',id=f'{plan.run_id}-day-{day}',run_id=plan.run_id,
            run_manifest=dict(id=plan.run_id,version='1.0.0',sha256=run_artifact['sha256']),producer=RESTRICTED['producer'],
            execution='engine_run',source_commit=source_commit,runtime=runtime.model_dump(mode='json'),bindings=RESTRICTED['bindings'],
            evaluation_configuration=RESTRICTED['evaluation_configuration']['reference'],cutoff=cutoff.isoformat(),
            created_at=plan.created_at.isoformat(),status='complete',partitions=partitions)))
        # An unadmitted candidate, deliberately not manifest.json.
        exports.append(_write(view,'export-day-'+str(day),'candidate.json',export.model_dump(mode='json'),'observed_manifest'))
    return dict(run_manifest=run_artifact,exports=exports,execution='engine_run',production_qualified=False)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('plan','private-root','staging-root','runtime'):
        parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--source-commit',required=True)
    args=parser.parse_args()
    result=prepare(json.loads(args.plan.read_bytes()),args.private_root,args.staging_root,
        runtime=json.loads(args.runtime.read_bytes()),source_commit=args.source_commit)
    print(json.dumps(result,sort_keys=True))


if __name__=='__main__':main()
