"""Evaluator-only trusted run/result byte checks, before production work."""
from pathlib import Path

from contracts.domain.evaluation import SimulatorTruth
from .admission import verify_export
from .common import Authority, ExportAuthority, read_artifact, sha256
from .private import CalibrationArtifact, ExternalCalibrationEvidence, RunManifest, RunResult, SeedLedger, TruthRequest, TruthResponse, validate_truth_response


def verify_run(raw: bytes, root: Path, authority: Authority):
    if sha256(raw)!=authority.manifest_sha256:raise ValueError('untrusted run manifest digest')
    run=RunManifest.model_validate_json(raw)
    if run.run_id!=authority.run_id or run.producer!=authority.producer or run.source_commit!=authority.source_commit or run.runtime!=authority.runtime:
        raise ValueError('untrusted run producer/source/runtime')
    if run.execution=='contract_fixture' and not authority.allow_contract_fixture:raise ValueError('fixture is not generated evidence')
    by_id={a.id:a for a in run.inputs}
    for name,ref in run.bindings:
        if name=='dgp':continue # DGP identity is the complete parameter manifest.
        artifact=by_id.get(ref.id)
        if artifact is None or artifact.role!='configuration':raise ValueError('missing required bound configuration artifact')
        raw_input=read_artifact(root,artifact,'configuration')
        if sha256(raw_input.replace(b'\r\n',b'\n'))!=ref.sha256:raise ValueError('configuration bytes differ from accepted version/hash')
    for artifact in run.inputs:read_artifact(root,artifact,artifact.role)
    for unit in run.units:
        if unit.evaluation_configuration is not None:
            import json
            ref=unit.evaluation_configuration;artifact=by_id.get(ref.id)
            if artifact is None or artifact.role!='configuration' or artifact.sha256!=ref.sha256:raise ValueError('evaluation preset requires the exact predeclared configuration bytes')
            configuration=json.loads(read_artifact(root,artifact,'configuration'))
            expected=dict(id=ref.id,version=ref.version,repetitions=unit.repetitions,cohorts=[dict(id=c.id,role=c.role,patients_per_replicate=sum(p.replicate==0 for p in c.patients)) for c in unit.cohorts])
            if configuration!=expected:raise ValueError('evaluation cohort/replicate roster differs from its hashed configuration')
    return run


def verify_result(raw: bytes, root: Path, run: RunManifest, authority: Authority, expected_result_sha256: str, *, calibration_policies=None, external_inputs=None):
    if sha256(raw)!=expected_result_sha256:raise ValueError('untrusted producer result digest')
    result=RunResult.model_validate_json(raw)
    if (result.run_id!=run.run_id or result.run_manifest.id!=run.run_id or result.run_manifest.version!='1.0.0' or result.run_manifest.sha256!=authority.manifest_sha256
            or result.producer!=run.producer or result.source_commit!=run.source_commit or result.runtime!=run.runtime or result.execution!=run.execution):
        raise ValueError('result changed trusted run identity/provenance')
    slots={p.id:(u,c,p) for u in run.units for c in u.cohorts for p in c.patients}
    from contracts.dgp.parameters import reference_parameters
    from contracts.dgp.scenarios import resolve_cell,scenario_manifest
    calibration_needed={}
    for unit in run.units:
        values={name:row['value'] for name,row in resolve_cell(reference_parameters(),scenario_manifest(),unit.cell_id)['parameters'].items()}
        calibration_needed[unit.cell_id]=values['report_mode'] in (2,3,4) or bool(values['external_shift_SE'] or values['external_reverse_sign'])
    calibrated={}
    for calibration in result.calibration:
        policy=(calibration_policies or {}).get(calibration.id)
        if policy is None:raise ValueError('calibration needs a separately trusted evaluator artifact digest and authority')
        evaluator,trusted_digest=policy
        if calibration.sha256!=trusted_digest:raise ValueError('generator cannot substitute a self-declared calibration digest')
        external=(external_inputs or {}).get(calibration.id,(None,None))
        artifact=verify_calibration(read_artifact(root,calibration,'calibration'),root,expected_sha256=trusted_digest,evaluator=evaluator,bindings=run.bindings,trusted_external_raw=external[0],trusted_external_sha256=external[1])
        if artifact.binding.status!='solved':raise ValueError('unresolved calibration cannot authorize published scenario data')
        if artifact.binding.cell_id in calibrated:raise ValueError('duplicate calibration cell')
        calibrated[artifact.binding.cell_id]=artifact
    keys={}
    if result.seed_ledger:
        ledger=SeedLedger.model_validate_json(read_artifact(root,result.seed_ledger,'seed_ledger'))
        if ledger.run_id!=run.run_id:raise ValueError('seed ledger run mismatch')
        for key in ledger.keys:
            slot=slots.get(key.patient)
            if slot is None:raise ValueError('seed patient outside exact roster')
            unit,_,patient=slot
            if key.scenario!=unit.cell_id or key.replicate!=patient.replicate or key.phase!=run.phase or key.protocol!=run.bindings.protocol.id:
                raise ValueError('full seed key not bound to its run/cell/patient/replicate')
            keys[key.key_sha256]=key
    admitted=[];seen=set()
    for artifact in result.observed_exports:
        raw_export=read_artifact(root,artifact,'observed_manifest')
        from .observed import ObservedExport
        public=ObservedExport.model_validate_json(raw_export)
        expected=ExportAuthority(**authority.model_dump(),export_id=public.id,export_sha256=artifact.sha256)
        manifest,partitions=verify_export(raw_export,root,expected)
        if manifest.bindings!=run.bindings or manifest.cutoff!=run.cutoff:raise ValueError('export changed run input versions/cutoff')
        for partition,history,batch,projection,_,_ in partitions:
            slot=slots.get(partition.patient_id)
            if slot is None or partition.patient_id in seen:raise ValueError('unknown/repeated patient partition')
            unit,cohort,patient=slot;seen.add(partition.patient_id)
            if (partition.unit_id,partition.cell_id,partition.preset,partition.cohort_id,partition.replicate)!=(unit.id,unit.cell_id,unit.preset,cohort.id,patient.replicate):
                raise ValueError('multi-patient cell/preset/cohort/replicate mapping mismatch')
            if calibration_needed[unit.cell_id] and unit.cell_id not in calibrated:
                raise ValueError('registered calibrated cell cannot export data before independently verified solved binding')
            for binding in partition.records:
                source=binding.source.model_dump(exclude={'raw_sha256'})
                if source not in run.sources:raise ValueError('generated record forged an undeclared source identity')
                key=keys.get(binding.seed_key_sha256)
                if key is None or key.patient!=patient.id or key.scenario!=unit.cell_id or key.replicate!=patient.replicate:
                    raise ValueError('record missing its exact private full seed identity')
            admitted.append((manifest,partition,history,batch,projection))
    if result.status=='complete' and seen!=set(slots):raise ValueError('complete output omitted planned patients/replicates')
    for artifact in result.private_truth:
        truth=SimulatorTruth.model_validate_json(read_artifact(root,artifact,'private_truth'))
        if truth.patient_id not in slots:raise ValueError('private truth patient not in run')
    for artifact in result.reports:read_artifact(root,artifact,artifact.role)
    return result,admitted


def verify_truth(raw_request: bytes, raw_response: bytes, root: Path, *, request_sha256: str, response_sha256: str, evaluator: Authority, investigation_authorities=None):
    if sha256(raw_request)!=request_sha256 or sha256(raw_response)!=response_sha256:raise ValueError('untrusted evaluator request/result digest')
    request=TruthRequest.model_validate_json(raw_request);response=TruthResponse.model_validate_json(raw_response)
    for value in (request,response):
        if value.run_id!=evaluator.run_id or value.producer!=evaluator.producer or value.source_commit!=evaluator.source_commit or value.runtime!=evaluator.runtime:
            raise ValueError('untrusted evaluator producer/run/source/runtime')
        if value.execution=='contract_fixture' and not evaluator.allow_contract_fixture:raise ValueError('contract fixture cannot authorize numerical acceptance')
    if request.run_manifest.sha256!=evaluator.manifest_sha256:raise ValueError('truth request run manifest mismatch')
    if request.observed_history:
        from contracts.domain.boundaries import LearnerHistory
        history=LearnerHistory.model_validate_json(read_artifact(root,request.observed_history,'observed'))
        if history.patient_id!=request.patient_id or history.cutoff!=request.cutoff:raise ValueError('conditional history patient/cutoff mismatch')
        # A conditioning artifact is the already-projected H_t, never a complete
        # lineage carrying future corrections or superseded clinical values.
        for record in history.records:
            measures=record.covariates if record.kind=='patient' else [record.measure] if record.kind=='observation' else []
            if any(m.observed_at>request.cutoff or m.available_at>=request.cutoff for m in measures):raise ValueError('future nested conditioning measure')
    if request.comparator_pilot:read_artifact(root,request.comparator_pilot,'evaluator_result')
    read_artifact(root,response.report,'evaluator_result')
    for artifact in response.diagnostics:read_artifact(root,artifact,artifact.role)
    qualified_probability=None
    if any(p.status=='computed' for p in response.interruption_precision):
        from .probability import ProbabilityEvidence, qualify_probability, qualify_symptom_pilot
        refs=[p.probability_evidence for p in response.interruption_precision if not p.component.endswith('conditional_isi')]
        if not refs or any(ref is None or ref!=refs[0] for ref in refs):raise ValueError('all six components must reference one full-vector R1 artifact')
        evidence=ProbabilityEvidence.model_validate_json(read_artifact(root,refs[0],'evaluator_result'))
        qualified_probability=qualify_probability(evidence,root,request,investigation_authorities=investigation_authorities)
        qualified_probability['symptom_matched_se']={}
        for precision in response.interruption_precision:
            if precision.status=='computed' and precision.component.endswith('conditional_isi'):
                qualified_probability['symptom_matched_se'][precision.component]=qualify_symptom_pilot(precision.matched_pilot,root,request,refs[0],qualified_probability,precision.component)
        if response.conditional_accuracy is not None:
            for artifact in response.conditional_accuracy.independent_reduced_checks:read_artifact(root,artifact,'evaluator_result')
    validate_truth_response(request,response,qualified_probability=qualified_probability)
    return request,response


def verify_calibration(raw: bytes, root: Path, *, expected_sha256: str, evaluator: Authority, bindings, trusted_external_raw: bytes | None = None, trusted_external_sha256: str | None = None):
    from contracts.dgp.calibration import calibration_request, require_solved
    def producer(value):
        if value.run_id!=evaluator.run_id or value.producer!=evaluator.producer or value.source_commit!=evaluator.source_commit or value.runtime!=evaluator.runtime:
            raise ValueError('untrusted calibration evaluator/run/source/runtime')
        if value.execution=='contract_fixture' and not evaluator.allow_contract_fixture:raise ValueError('fixture cannot authorize actual calibrated generation')
    if sha256(raw)!=expected_sha256:raise ValueError('untrusted calibration digest')
    artifact=CalibrationArtifact.model_validate_json(raw);producer(artifact)
    if artifact.binding.dgp!=bindings.dgp:raise ValueError('calibration DGP mismatch')
    for value in [artifact.sample,artifact.seeds,*artifact.comparator_pilots,*([artifact.source_reference,artifact.source_pilot] if artifact.source_reference else [])]:
        read_artifact(root,value,value.role)
    external=None
    if trusted_external_raw is not None:
        if trusted_external_sha256 is None or sha256(trusted_external_raw)!=trusted_external_sha256:raise ValueError('untrusted upstream external evidence digest')
        upstream=ExternalCalibrationEvidence.model_validate_json(trusted_external_raw);producer(upstream)
        for value in [upstream.source_reference,upstream.source_shift_pilot,*upstream.comparison_pilots]:read_artifact(root,value,'evaluator_result')
        if artifact.source_reference!=upstream.source_reference or artifact.source_pilot!=upstream.source_shift_pilot or artifact.comparator_pilots!=upstream.comparison_pilots:
            raise ValueError('binding cannot substitute its own external target/pilot artifacts')
        external=upstream.evidence
    expected=calibration_request(cell_id=artifact.binding.cell_id,dgp=bindings.dgp,external=external)
    actual=artifact.binding.model_dump(mode='json')
    if any(actual[name]!=value for name,value in expected.items()):raise ValueError('calibration target/purpose/cell/version mismatch')
    if artifact.binding.status=='solved':require_solved(artifact.binding,cell_id=artifact.binding.cell_id,dgp=bindings.dgp,external=external)
    return artifact
