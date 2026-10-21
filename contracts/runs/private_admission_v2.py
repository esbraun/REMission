"""Private v2 truth admission retaining accepted scientific qualification."""
from pathlib import Path
from .common import read_artifact, sha256
from .private_v2 import AuthorityV2, TruthRequestV2, TruthResponseV2
from .truth_validation_v2 import validate_truth_response_v2


def verify_truth_v2(raw_request: bytes, raw_response: bytes, root: Path, *, request_sha256: str, response_sha256: str, evaluator: AuthorityV2, investigation_authorities=None):
    if not isinstance(evaluator, AuthorityV2):raise ValueError('explicit v2 evaluator authority required')
    if sha256(raw_request)!=request_sha256 or sha256(raw_response)!=response_sha256:raise ValueError('untrusted evaluator request/result digest')
    request=TruthRequestV2.model_validate_json(raw_request);response=TruthResponseV2.model_validate_json(raw_response)
    if request.bindings!=evaluator.bindings or response.bindings!=evaluator.bindings:raise ValueError('v2 evaluator representation/schema bindings mismatch')
    if request.execution=='engine_run' and evaluator.producer_qualification is None:raise ValueError('real evaluator qualification pending')
    for value in (request,response):
        if value.run_id!=evaluator.run_id or value.producer!=evaluator.producer or value.source_commit!=evaluator.source_commit or value.runtime!=evaluator.runtime:
            raise ValueError('untrusted evaluator producer/run/source/runtime')
        if value.execution=='contract_fixture' and not evaluator.allow_contract_fixture:raise ValueError('contract fixture cannot authorize numerical acceptance')
    if request.run_manifest.sha256!=evaluator.manifest_sha256:raise ValueError('truth request run manifest mismatch')
    for precision in response.interruption_precision:
        if precision.status=='computed' and precision.method=='numerical' and not precision.component.endswith('conditional_isi') and precision.matched_pilot!=request.comparator_pilot:
            raise ValueError('reported probability matched pilot differs from authenticated request plan')
    if request.observed_history:
        from contracts.domain.observed_v2 import LearnerHistoryV2 as LearnerHistory
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
        qualified_probability['symptom_qualifications']={}
        for precision in response.interruption_precision:
            if precision.status=='computed' and precision.component.endswith('conditional_isi'):
                qualification=qualify_symptom_pilot(precision.matched_pilot,root,request,refs[0],qualified_probability,precision.component)
                qualified_probability['symptom_matched_se'][precision.component]=qualification.smallest_estimator_se
                qualified_probability['symptom_qualifications'][precision.component]=qualification
        if response.conditional_accuracy is not None:
            for artifact in response.conditional_accuracy.independent_reduced_checks:read_artifact(root,artifact,'evaluator_result')
    validate_truth_response_v2(request,response,qualified_probability=qualified_probability)
    return request,response
