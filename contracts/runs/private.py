"""Evaluator/generator-owned run and truth contracts. Exclude from consumers."""
from datetime import datetime, timedelta
from typing import Annotated, Literal
from pydantic import AwareDatetime, Field, model_validator
from contracts.domain.common import Identifier, Name, Nonnegative, Sha256, Source, StrictModel, Versioned, VersionRef
from contracts.domain.estimands import EstimandContract, InterruptionResult
from contracts.domain.evaluation import SimulatorTruth, TruthResult
from contracts.dgp.calibration import CalibrationBinding, ExternalTargetEvidence
from contracts.dgp.parameters import reference_parameters
from contracts.dgp.scenarios import scenario_manifest
from contracts.dgp.truth import fixture_manifest, seed_words, truth_status
from .common import Artifact, Bindings, Commit, Producer, Runtime, RuntimeProfile, Token, canonical, sha256, unique, RESTRICTED, RESTRICTED_CELL, restricted_profile, restricted_producer

Phase=Literal['fixture','calibration','pilot','smoke','development','confirmation']
Namespace=Literal['generation','assignment','measurement','missingness','fitting','posterior_rollout','truth']
TruthKind=Literal['structural_parameter','marginal_contrast','observed_history_conditional_average','simulator_specific_individual_contrast','excursion_effect','fixed_policy_value','learning_algorithm_performance']
CELLS={cell['id']:cell for cell in scenario_manifest()['cells']}


class StreamKey(StrictModel):
    """Complete accepted key material; words and digest are verified, not trusted."""
    root_seed: Literal[20261020]
    protocol: Identifier
    phase: Phase
    namespace: Namespace
    scenario: Identifier
    replicate: Annotated[int, Field(ge=0)]
    patient: Identifier
    time_index: int
    process: Identifier
    stream: Identifier
    words: Annotated[list[Annotated[int,Field(ge=0,le=4294967295)]],Field(min_length=8,max_length=8)]
    key_sha256: Sha256

    @model_validator(mode='after')
    def derived(self):
        args=self.model_dump(exclude={'words','key_sha256'})
        words=seed_words(**args)
        digest=bytes().join(word.to_bytes(4,'little') for word in words).hex()
        if self.words!=words or self.key_sha256!=digest:
            raise ValueError('full stream key/seed words/hash mismatch')
        return self


class PatientSlot(StrictModel):
    id: Identifier
    replicate: Annotated[int,Field(ge=0)]


class Cohort(StrictModel):
    id: Token
    role: Literal['historical','external','prospective']
    patients: Annotated[list[PatientSlot],Field(min_length=1)]

    @model_validator(mode='after')
    def roster(self):
        unique([p.id for p in self.patients],'cohort patient')
        return self


class Unit(StrictModel):
    id: Token
    cell_id: Identifier
    catalog_patients: Annotated[int,Field(gt=0)]
    preset: Literal['catalog_cell','smoke','demonstration','evaluation']
    evaluation_configuration: VersionRef | None
    repetitions: Annotated[int,Field(ge=1)]
    cohorts: Annotated[list[Cohort],Field(min_length=1)]

    @model_validator(mode='after')
    def exact_cell_and_preset(self):
        if self.cell_id==RESTRICTED_CELL:
            if (self.catalog_patients!=12 or self.preset!='evaluation' or self.repetitions!=1
                    or self.evaluation_configuration is None or self.evaluation_configuration.model_dump(mode='json')!=RESTRICTED['evaluation_configuration']['reference']
                    or len(self.cohorts)!=1 or self.cohorts[0].role!='prospective' or len(self.cohorts[0].patients)!=12
                    or any(p.replicate!=0 for p in self.cohorts[0].patients)):
                raise ValueError('restricted reference requires exact prospective twelve-member evaluation')
            return self
        cell=CELLS.get(self.cell_id)
        if cell is None or self.catalog_patients!=cell['patients']:
            raise ValueError('unknown or resized catalog cell')
        if any(p.replicate>=self.repetitions for c in self.cohorts for p in c.patients):raise ValueError('patient outside declared replicate roster')
        sizes=[sum(p.replicate==0 for p in c.patients) for c in self.cohorts];roles=[c.role for c in self.cohorts]
        if any(sum(p.replicate==rep for p in c.patients)!=size for c,size in zip(self.cohorts,sizes) for rep in range(self.repetitions)):
            raise ValueError('every replicate must retain the complete cohort roster')
        expected={'catalog_cell':([cell['patients']],['historical']),
                  'smoke':([100,30,30,6],['historical','external','external','prospective']),
                  'demonstration':([2000,150,180,220,250,60],['historical','external','external','external','external','prospective'])}
        if self.preset in expected and (sizes,roles)!=expected[self.preset]:
            raise ValueError('preset roster differs from its exact sizes/roles; catalog n is separate')
        if (self.preset=='evaluation')!=(self.evaluation_configuration is not None):
            raise ValueError('evaluation sizes require an explicit version/hash configuration')
        unique([c.id for c in self.cohorts],'cohort ID')
        unique([p.id for c in self.cohorts for p in c.patients],'unit patient')
        return self


class RequiredWorkloads(StrictModel):
    """Required future workloads, never a count of computations executed here."""
    calibration_patients: Literal[200000]
    source_shift_pilot_trials: Literal[1000]
    source_shift_trial_size: Literal[200]
    comparator_pilot_trials: Literal[1000]
    source_comparator_sizes: list[int]
    truth_batch_size: Literal[10000]
    truth_batch_cap: Literal[1000]
    smoke_repetitions_per_cell: Literal[5]
    catalog_cells: Literal[82]
    conditional_particle_levels: list[int]
    conditional_filters_per_level: Literal[32]
    distribution_patients: Annotated[int,Field(ge=10000)]

    @model_validator(mode='after')
    def frozen_sizes(self):
        if self.source_comparator_sizes!=[30,150,180,200,220,250] or self.conditional_particle_levels!=[1024,4096,16384,65536]:
            raise ValueError('approved pilot sizes/conditional refinement levels cannot be reduced')
        return self


class RunManifest(Versioned):
    """Immutable pre-execution input plan; outputs are separate to avoid hash cycles."""
    kind: Literal['generator_run_manifest']
    contract_version: Literal['1.0.0']
    run_id: Token
    producer: Producer
    execution: Literal['contract_fixture','engine_run']
    source_commit: Commit
    runtime: RuntimeProfile
    bindings: Bindings
    input_sha256: Sha256
    inputs: list[Artifact]
    root_seed: Literal[20261020]
    phase: Phase
    scope: Literal['cell_batch','catalog_smoke','preset']
    cutoff: AwareDatetime
    created_at: AwareDatetime
    units: Annotated[list[Unit],Field(min_length=1)]
    required_workloads: RequiredWorkloads
    sources: Annotated[list[dict[Literal['id','version','adapter'],str]],Field(min_length=1)]

    @model_validator(mode='after')
    def inputs_and_rosters(self):
        restricted=restricted_profile(self.bindings,self.runtime)
        if restricted:
            restricted_producer(self.producer,self.execution)
            if (self.schema_version!='1.0.0' or self.phase!='development' or self.scope!='preset'
                    or len(self.units)!=1 or self.units[0].cell_id!=RESTRICTED_CELL
                    or self.cutoff!=datetime.fromisoformat(RESTRICTED['binding_descriptors']['timing']['origin'])+timedelta(days=42)
                    or self.sources!=[*RESTRICTED['source'], RESTRICTED['historical_assignment_source']]):
                raise ValueError('restricted run profile/configuration/source mismatch')
        elif any(u.cell_id==RESTRICTED_CELL for u in self.units):
            raise ValueError('restricted cell requires restricted profile')
        if self.producer.role not in ('generator','contract_fixture') or (self.execution=='contract_fixture')!=(self.producer.role=='contract_fixture'):
            raise ValueError('run producer/execution mismatch')
        if self.execution=='contract_fixture' and self.phase!='fixture':
            raise ValueError('pure contract fixtures must be explicitly fixture phase')
        if self.input_sha256!=sha256(canonical([a.model_dump(mode='json') for a in self.inputs])):
            raise ValueError('input manifest hash mismatch')
        if self.created_at<self.cutoff:
            raise ValueError('run creation precedes its declared receipt cutoff')
        unique([u.id for u in self.units],'unit ID')
        unique([p.id for u in self.units for c in u.cohorts for p in c.patients],'run patient')
        unique([a.id for a in self.inputs],'input artifact ID');unique([a.path for a in self.inputs],'input artifact path')
        if self.scope=='catalog_smoke':
            if self.phase!='smoke' or {u.cell_id for u in self.units}!=set(CELLS) or len(self.units)!=82 or any(u.preset!='catalog_cell' or u.repetitions<5 for u in self.units):
                raise ValueError('catalog smoke requires every exact cell and five repetitions each')
        if self.phase=='smoke' and any(u.repetitions<5 for u in self.units if u.preset=='catalog_cell'):
            raise ValueError('cell smoke requires five attempts per cell')
        for source in self.sources:
            if set(source)!={'id','version','adapter'} or (not restricted and source['version']!='1.2.0') or source['adapter'] not in {'simulation','synthetic_fhir_shaped','synthetic_oura_like','patient_report','synthetic_trial'}:
                raise ValueError('complete explicit generated source identity/version/adapter required')
            Source.model_validate({**source,'raw_sha256':'0'*64})
        unique([canonical(source) for source in self.sources],'source identity')
        return self


class SeedLedger(Versioned):
    kind: Literal['seed_ledger']
    contract_version: Literal['1.0.0']
    run_id: Token
    keys: Annotated[list[StreamKey],Field(min_length=1)]

    @model_validator(mode='after')
    def identities(self):
        unique([k.key_sha256 for k in self.keys],'full stream key')
        return self


class RunResult(Versioned):
    kind: Literal['generator_run_result']
    contract_version: Literal['1.0.0']
    run_id: Token
    run_manifest: VersionRef
    producer: Producer
    execution: Literal['contract_fixture','engine_run']
    source_commit: Commit
    runtime: Runtime
    status: Literal['pending','failed','partial','complete']
    reason: Name | None
    observed_exports: list[Artifact]
    private_truth: list[Artifact]
    seed_ledger: Artifact | None
    calibration: list[Artifact]
    reports: list[Artifact]

    @model_validator(mode='after')
    def output_roles(self):
        if self.status!='complete' and self.reason is None:
            raise ValueError('pending/failed/partial result requires its actual reason')
        for artifacts,role in [(self.observed_exports,'observed_manifest'),(self.private_truth,'private_truth'),(self.calibration,'calibration'),(self.reports,'evaluator_result')]:
            if any(a.role!=role for a in artifacts):raise ValueError('run output role mismatch')
        if self.seed_ledger is not None and self.seed_ledger.role!='seed_ledger':raise ValueError('seed ledger role mismatch')
        if self.status=='complete' and (not self.observed_exports or self.seed_ledger is None or self.reason is not None):
            raise ValueError('complete generator output needs observed exports/full key ledger and no failure reason')
        return self


class ClinicalTarget(StrictModel):
    kind: Literal['clinical']
    truth_kind: TruthKind
    estimand: EstimandContract


class FixtureTarget(StrictModel):
    kind: Literal['fixture']
    truth_kind: Literal['marginal_contrast']
    estimand: Literal['FIX-CONSTANT','FIX-ESC-RANDOMIZED','FIX-ESC-OBSERVATIONAL']
    outcome: Literal['linear_Y']
    unit: Literal['fixture_points']
    intervention: Literal['A1','regime_11']
    comparator: Literal['A0','regime_00']
    fixture_manifest: VersionRef


class SystemTarget(StrictModel):
    kind: Literal['system']
    estimand: Literal['SYSTEM-LINEAGE','SYSTEM-BOUNDARY']
    outcome: Literal['rejection']
    unit: Literal['none']
    expected_fault: Identifier


class ParameterTarget(StrictModel):
    kind: Literal['parameter']
    truth_kind: Literal['structural_parameter']
    symbol: Identifier
    parameters: VersionRef


FIXTURE_QUANTITIES={
    'normal':{'truth_mean','truth_variance'},'beta':{'truth_shape'},'constant':{'ATE'},
    'modifier':{'ATE','CATE_M0','CATE_M1'},'two_period':{'regime_values'},
    'ordinal':{'single_item_at0','single_item_at1','seven_equal_at0'},
    'contextual_policy':{'no_action','always_action','A_equals_M'},
    'escalation_randomized':{'regime_values'},'escalation_observational':{'regime_values'}}


class AnalyticTarget(StrictModel):
    """Native standalone Layer A quantities; not catalog n60/n240 or clinical ISI."""
    kind: Literal['analytic_fixture']
    fixture: Identifier
    quantity: Identifier
    unit: Literal['fixture_native_units']
    fixture_manifest: VersionRef

    @model_validator(mode='after')
    def registered_quantity(self):
        if self.quantity not in FIXTURE_QUANTITIES.get(self.fixture,set()) or self.fixture not in fixture_manifest()['fixtures']:
            raise ValueError('unknown native analytic fixture/quantity')
        return self


Target=Annotated[ClinicalTarget|FixtureTarget|SystemTarget|ParameterTarget|AnalyticTarget,Field(discriminator='kind')]


class TruthRequest(Versioned):
    kind: Literal['evaluator_request']
    contract_version: Literal['1.0.0']
    id: Token
    run_id: Token
    run_manifest: VersionRef
    producer: Producer
    execution: Literal['contract_fixture','engine_run']
    source_commit: Commit
    runtime: Runtime
    bindings: Bindings
    unit_id: Token | None
    cell_id: Identifier | None
    target: Target
    information_set: Literal['structural_population','available_observed_history','realized_latent_oracle','deterministic_fixture']
    method: Literal['analytic','enumerated','numerical','deterministic_check']
    cutoff: AwareDatetime
    patient_id: Identifier | None
    observed_history: Artifact | None
    generating_policy: VersionRef | None
    coupling: VersionRef | None
    seeds: Annotated[list[StreamKey],Field(min_length=1)]
    batch_size: Literal[10000]
    batch_cap: Literal[1000]
    comparator_pilot: Artifact | None
    smallest_estimator_se: Nonnegative | None

    @model_validator(mode='after')
    def registered_target(self):
        if self.bindings.model_dump(mode='json')==RESTRICTED['bindings']:
            raise ValueError('restricted producer profile does not authorize evaluator requests')
        cell=CELLS.get(self.cell_id)
        standalone=self.target.kind=='analytic_fixture'
        if standalone:
            if self.cell_id is not None or self.unit_id is not None or self.target.fixture_manifest!=self.bindings.analytic_fixtures or self.method not in ('analytic','enumerated') or self.information_set!='deterministic_fixture':
                raise ValueError('native fixture must remain separate from catalog/clinical execution')
        elif cell is None or self.unit_id is None:raise ValueError('unknown truth cell/unit')
        if self.producer.role not in ('evaluator','contract_fixture') or (self.execution=='contract_fixture')!=(self.producer.role=='contract_fixture'):
            raise ValueError('truth request requires evaluator/fixture producer')
        if self.execution=='contract_fixture' and any(key.phase!='fixture' for key in self.seeds):raise ValueError('contract-only requests cannot claim executed calibration/pilot/smoke phases')
        scenario=self.target.fixture if standalone else self.cell_id
        if any(k.namespace!='truth' or k.scenario!=scenario or k.protocol!=self.bindings.protocol.id for k in self.seeds):
            raise ValueError('truth keys must be independent truth namespace bound to protocol/cell')
        unique([k.key_sha256 for k in self.seeds],'truth key')
        target=self.target
        if target.kind=='clinical':
            estimand=target.estimand
            if (estimand.estimand_id,estimand.outcome,estimand.unit,estimand.intervention,estimand.comparator)!=(cell['estimand'],cell['outcome'],cell['unit'],cell['intervention'],cell['comparator']):
                raise ValueError('clinical target differs from the exact catalog estimand/actions/outcome')
            if estimand.observation_cutoff!=self.cutoff:
                raise ValueError('truth/estimand cutoff mismatch')
            conditional=target.truth_kind=='observed_history_conditional_average'
            oracle=target.truth_kind=='simulator_specific_individual_contrast'
            expected='available_observed_history' if conditional else 'realized_latent_oracle' if oracle else 'structural_population'
            if self.information_set!=expected or conditional!=(self.observed_history is not None) or (conditional or oracle)!=(self.patient_id is not None):
                raise ValueError('conditional history and realized-latent oracle must remain distinct')
            if oracle!=(self.coupling is not None):raise ValueError('individual oracle must declare its simulator coupling')
            if target.truth_kind in ('excursion_effect','fixed_policy_value','learning_algorithm_performance') and self.generating_policy is None:
                raise ValueError('policy/excursion target requires its named generating policy')
            if target.truth_kind=='structural_parameter':raise ValueError('structural parameter is not a clinical points-scale contrast')
            expected_kind={'EST-MRT':{'excursion_effect'},'EST-POLICY':{'fixed_policy_value','learning_algorithm_performance'}}.get(estimand.estimand_id,{'marginal_contrast','observed_history_conditional_average','simulator_specific_individual_contrast'})
            if target.truth_kind not in expected_kind:raise ValueError('truth kind differs from the declared clinical estimand')
            if estimand.estimand_id=='EST-POLICY' and (target.truth_kind=='fixed_policy_value')!=(estimand.policy_value_target=='fixed_contextual'):
                raise ValueError('fixed policy value and complete learning-run performance remain distinct')
        elif target.kind=='fixture':
            if (target.estimand,target.outcome,target.unit,target.intervention,target.comparator)!=(cell['estimand'],cell['outcome'],cell['unit'],cell['intervention'],cell['comparator']) or target.fixture_manifest!=self.bindings.analytic_fixtures:
                raise ValueError('fixture target cannot be relabeled as clinical ISI')
            if self.method not in ('analytic','enumerated') or self.information_set!='deterministic_fixture':raise ValueError('fixture method/information mismatch')
        elif target.kind=='system':
            if target.estimand!=cell['estimand'] or target.expected_fault!=cell['variant'] or self.method!='deterministic_check' or self.information_set!='deterministic_fixture':raise ValueError('system cell requires its deterministic fault check, not a fit')
        elif target.kind=='parameter':
            if target.symbol not in reference_parameters()['parameters'] or target.parameters!=self.bindings.parameters or self.information_set!='structural_population':raise ValueError('unknown/mismatched structural parameter target')
        if target.kind!='clinical' and any(value is not None for value in (self.patient_id,self.observed_history,self.generating_policy,self.coupling)):
            raise ValueError('nonclinical targets cannot silently add patient/history/policy/oracle conditioning')
        if self.observed_history is not None and self.observed_history.role!='observed':raise ValueError('conditioning input must be observed history')
        if self.method=='numerical' and (self.comparator_pilot is None or self.comparator_pilot.role!='evaluator_result' or self.smallest_estimator_se is None):
            raise ValueError('numerical truth requires independently verified matched pilot evidence/SE')
        return self


class FixtureAnswer(StrictModel):
    kind: Literal['fixture_answer']
    estimand: Literal['FIX-CONSTANT','FIX-ESC-RANDOMIZED','FIX-ESC-OBSERVATIONAL']
    unit: Literal['fixture_points']
    value: float


class SystemAnswer(StrictModel):
    kind: Literal['system_answer']
    estimand: Literal['SYSTEM-LINEAGE','SYSTEM-BOUNDARY']
    fault: Identifier
    detected: bool


class ParameterAnswer(StrictModel):
    kind: Literal['parameter_answer']
    symbol: Identifier
    parameters: VersionRef
    value: float | list[float]


class AnalyticAnswer(StrictModel):
    kind: Literal['analytic_fixture_answer']
    fixture: Identifier
    quantity: Identifier
    unit: Literal['fixture_native_units']
    value: float | list[float] | dict[Identifier,float]


class InterruptionPrecision(StrictModel):
    """Component evidence; numerical probability needs the R1 artifact barrier."""
    component: Literal['intervention.survival_day42','intervention.admission_by_day42','intervention.alive_outpatient_day42','intervention.conditional_isi','comparator.survival_day42','comparator.admission_by_day42','comparator.alive_outpatient_day42','comparator.conditional_isi']
    status: Literal['pending','failed','undefined','unresolved_probability_precision','computed']
    numerical_standard_error: Nonnegative | None
    smallest_estimator_se: Nonnegative | None
    matched_pilot: Artifact | None
    probability_evidence: Artifact | None = None
    method: Literal['analytic','enumerated','numerical'] = 'numerical'

    @model_validator(mode='after')
    def accepted_threshold(self):
        probability=not self.component.endswith('conditional_isi')
        if self.status=='computed':
            absolute=.001 if probability else .05
            if self.method!='numerical':
                if not probability or self.numerical_standard_error!=0 or self.smallest_estimator_se!=0:raise ValueError('structural probability proof has zero numerical uncertainty and no borrowed pilot SE')
            elif self.numerical_standard_error is None or self.smallest_estimator_se is None or self.matched_pilot is None or self.matched_pilot.role!='evaluator_result' or self.smallest_estimator_se<=0 or self.numerical_standard_error>min(absolute,.1*self.smallest_estimator_se):
                raise ValueError('component needs actual matched positive SE and both MCSE bounds')
            if probability and (self.probability_evidence is None or self.probability_evidence.role!='evaluator_result'):
                raise ValueError('probability computation needs the accepted R1 full evidence artifact')
        if not probability and self.probability_evidence is not None:raise ValueError('probability pilot exception cannot authorize conditional ISI')
        return self


class ConditionalAccuracy(StrictModel):
    particle_levels: list[int]
    filters_per_level: Literal[32]
    successive_differences: Annotated[list[Nonnegative],Field(min_length=2,max_length=2)]
    paired_standard_errors: Annotated[list[Nonnegative],Field(min_length=2,max_length=2)]
    quadrature_change: Nonnegative
    within_filter_mcse: Nonnegative
    between_filter_mcse: Nonnegative
    independent_reduced_checks: Annotated[list[Artifact],Field(min_length=1)]

    def require_accuracy(self, epsilon: float):
        levels=[1024,4096,16384,65536]
        if len(self.particle_levels)<3 or self.particle_levels!=levels[:len(self.particle_levels)]:raise ValueError('two successive approved particle refinements required')
        quarter=epsilon/4
        refinements=[difference+1.96*se for difference,se in zip(self.successive_differences,self.paired_standard_errors)]
        allowances=[self.quadrature_change,max(refinements),self.within_filter_mcse,self.between_filter_mcse]
        if any(value>quarter for value in allowances) or sum(allowances)>epsilon:raise ValueError('conditional numerical refinement/uncertainty budget unresolved')
        if any(a.role!='evaluator_result' for a in self.independent_reduced_checks):raise ValueError('conditional reduced checks must be evaluator reports')


class TruthResponse(Versioned):
    kind: Literal['evaluator_response']
    contract_version: Literal['1.0.0']
    id: Token
    run_id: Token
    request: VersionRef
    producer: Producer
    execution: Literal['contract_fixture','engine_run']
    source_commit: Commit
    runtime: Runtime
    status: Literal['pending','failed','undefined','capped','computed']
    reason: Name | None
    result: TruthResult | InterruptionResult | FixtureAnswer | SystemAnswer | ParameterAnswer | AnalyticAnswer | None
    batches: Annotated[int,Field(ge=0,le=1000)]
    report: Artifact
    diagnostics: list[Artifact]
    conditional_accuracy: ConditionalAccuracy | None
    interruption_precision: list[InterruptionPrecision]

    @model_validator(mode='after')
    def actual_states(self):
        if self.producer.role not in ('evaluator','contract_fixture') or (self.execution=='contract_fixture')!=(self.producer.role=='contract_fixture') or self.report.role!='evaluator_result':
            raise ValueError('evaluator producer/report role mismatch')
        if self.status=='computed':
            if self.result is None or self.reason is not None:raise ValueError('computed result requires actual payload and no unresolved reason')
            if isinstance(self.result,TruthResult) and self.result.estimate.status!='estimated':raise ValueError('unavailable truth cannot be computed')
            if isinstance(self.result,SystemAnswer) and not self.result.detected:raise ValueError('undetected fault is failed, not computed')
        elif self.reason is None:
            raise ValueError('pending/failed/undefined/capped result requires a reason')
        if self.status in ('pending','failed','capped') and self.result is not None and not isinstance(self.result,InterruptionResult):
            raise ValueError('unresolved scalar values belong in labeled private diagnostics, not a computed result')
        if self.status=='undefined' and not isinstance(self.result,(InterruptionResult,type(None))):
            raise ValueError('undefined symptom target may retain its separate interruption vector only')
        if self.status=='capped' and self.batches!=1000:raise ValueError('capped must retain the full declared truth batch cap')
        if isinstance(self.result,InterruptionResult):
            expected={arm+'.'+name for arm in ('intervention','comparator') for name in ('survival_day42','admission_by_day42','alive_outpatient_day42','conditional_isi')}
            if len(self.interruption_precision)!=8 or {p.component for p in self.interruption_precision}!=expected:raise ValueError('retain separate uncertainty/status for all intervention-specific components')
            if self.status=='computed' and any(p.status!='computed' for p in self.interruption_precision):raise ValueError('unresolved event components cannot become a computed vector')
            for arm in (self.result.intervention,self.result.comparator):
                if arm.conditional_isi.numerator_count<2 and arm.conditional_isi.isi.status!='undefined':raise ValueError('fewer than two eligible ISI values has undefined uncertainty')
        elif self.interruption_precision:raise ValueError('scalar answer cannot borrow an interruption precision vector')
        return self


class CalibrationArtifact(Versioned):
    kind: Literal['calibration_artifact']
    contract_version: Literal['1.0.0']
    run_id: Token
    producer: Producer
    execution: Literal['contract_fixture','engine_run']
    source_commit: Commit
    runtime: Runtime
    binding: CalibrationBinding
    sample: Artifact
    seeds: Artifact
    source_reference: Artifact | None
    source_pilot: Artifact | None
    comparator_pilots: list[Artifact]

    @model_validator(mode='after')
    def calibration_provenance(self):
        if self.producer.role not in ('evaluator','contract_fixture') or (self.execution=='contract_fixture')!=(self.producer.role=='contract_fixture'):
            raise ValueError('calibration artifacts are evaluator owned')
        if self.sample.role!='calibration' or self.seeds.role!='seed_ledger' or self.sample.sha256!=self.binding.calibration_sample_sha256 or self.seeds.sha256!=self.binding.seed_key_sha256:
            raise ValueError('calibration sample/seed artifact hash mismatch')
        if self.binding.sample_size!=200000:raise ValueError('required calibration sample cannot be reduced')
        if self.binding.purpose=='external_contrast':
            if self.source_reference is None or self.source_pilot is None or len(self.comparator_pilots)!=6:
                raise ValueError('external calibration needs source reference, distinct shift pilot and six comparison sizes')
            for artifact,ref in [(self.source_reference,self.binding.source_reference),(self.source_pilot,self.binding.source_pilot)]:
                if artifact.role!='evaluator_result' or artifact.id!=ref.id or artifact.sha256!=ref.sha256:raise ValueError('external binding/provenance disagreement')
        elif self.source_reference is not None or self.source_pilot is not None or self.comparator_pilots:
            raise ValueError('rate calibration cannot borrow unrelated source pilot evidence')
        if any(a.role!='evaluator_result' for a in self.comparator_pilots):raise ValueError('comparison pilots must be evaluator reports')
        return self


class ExternalCalibrationEvidence(Versioned):
    """Trusted evaluator output loaded by hash before target construction."""
    kind: Literal['external_calibration_evidence']
    contract_version: Literal['1.0.0']
    run_id: Token
    producer: Producer
    execution: Literal['contract_fixture','engine_run']
    source_commit: Commit
    runtime: Runtime
    evidence: ExternalTargetEvidence
    source_reference: Artifact
    source_shift_pilot: Artifact
    source_shift_pilot_trials: Literal[1000]
    source_shift_trial_size: Literal[200]
    comparison_pilots: Annotated[list[Artifact],Field(min_length=6,max_length=6)]
    comparison_sizes: list[int]
    comparison_pilot_trials: Literal[1000]

    @model_validator(mode='after')
    def distinct_pilot_provenance(self):
        if self.producer.role not in ('evaluator','contract_fixture') or (self.execution=='contract_fixture')!=(self.producer.role=='contract_fixture'):
            raise ValueError('external calibration evidence must have an evaluator producer')
        if self.comparison_sizes!=[30,150,180,200,220,250]:raise ValueError('all six independently piloted comparison sizes required')
        artifacts=[self.source_reference,self.source_shift_pilot,*self.comparison_pilots]
        if any(a.role!='evaluator_result' for a in artifacts):raise ValueError('external evidence role mismatch')
        unique([a.sha256 for a in artifacts],'independent source/reference/comparison artifact')
        for artifact,ref in [(self.source_reference,self.evidence.source_reference),(self.source_shift_pilot,self.evidence.source_pilot)]:
            if artifact.id!=ref.id or artifact.sha256!=ref.sha256:raise ValueError('external evidence/version reference hash mismatch')
        return self


def validate_truth_response(request: TruthRequest, response: TruthResponse, *, qualified_probability=None):
    """Called after out-of-band producer/run and all artifact hashes are verified."""
    if response.run_id!=request.run_id or response.request.id!=request.id or response.request.version!='1.0.0' or response.request.sha256!=sha256(canonical(request.model_dump(mode='json'))):
        raise ValueError('result/request binding mismatch')
    if response.runtime!=request.runtime or response.source_commit!=request.source_commit or response.execution!=request.execution:
        raise ValueError('evaluator runtime/source/execution provenance changed')
    if response.status=='capped' and request.method!='numerical':raise ValueError('analytic/deterministic result cannot consume a numerical truth batch cap')
    result=response.result;target=request.target
    if target.kind=='clinical' and target.estimand.estimand_id=='EST-INT' and result is not None:
        if not isinstance(result,InterruptionResult) or (result.intervention.action,result.comparator.action)!=(target.estimand.intervention,target.estimand.comparator):raise ValueError('EST-INT requires its separate intervention vector, including unresolved results')
        if any(p.status=='computed' for p in response.interruption_precision):
            if request.method!='numerical' or qualified_probability is None:raise ValueError('partial/undefined vectors cannot bypass authenticated component qualification')
            from .probability import COMPONENTS
            precision={p.component:p for p in response.interruption_precision}
            for index,component in enumerate(COMPONENTS):
                p=precision[component]
                if p.status!='computed':continue
                if p.method=='numerical' and p.matched_pilot!=request.comparator_pilot:raise ValueError('reported probability matched pilot differs from authenticated request plan')
                arm,name=component.split('.')
                if (p.method!='numerical')!=(component in qualified_probability['structural_proofs']):raise ValueError('structural versus numerical component method mismatch')
                if abs(getattr(getattr(result,arm),name)-float(qualified_probability['mean'][index]))>1e-12 or abs(p.numerical_standard_error-float(qualified_probability['mcse'][index]))>1e-12 or abs(p.smallest_estimator_se-float(qualified_probability['matched_se'][index]))>1e-12:raise ValueError('reported probability component differs from qualified files')
            if response.batches!=qualified_probability['batches']:raise ValueError('reported probability batch count differs')
            for index,arm_name in enumerate(('intervention','comparator')):
                arm=getattr(result,arm_name);actual=qualified_probability['conditional_isi'][index];p=precision[arm_name+'.conditional_isi']
                for name,times in qualified_probability['event_times'][arm_name].items():
                    if sorted(getattr(arm,name))!=times:raise ValueError('reported event-time multiset differs from all qualified day42 paths')
                if arm.conditional_isi.numerator_count!=actual['count'] or arm.conditional_isi.denominator_count!=response.batches*10000:raise ValueError('conditional ISI must use its own actual eligible count and full denominator, including partial vectors')
                estimate=arm.conditional_isi.isi
                if estimate.status=='estimated':
                    if actual['status']!='computed' or abs(estimate.value-actual['value'])>1e-12:raise ValueError('reported symptom mean differs from qualified eligible paths')
                    if estimate.standard_error is not None and abs(estimate.standard_error-actual['mcse'])>1e-12:raise ValueError('nested symptom uncertainty conflicts with qualified MCSE')
                    if estimate.interval is not None:raise ValueError('no independently qualified symptom interval method; retain interval=None')
                if p.status=='computed':
                    if estimate.status!='estimated' or actual['status']!='computed' or abs(p.numerical_standard_error-actual['mcse'])>1e-12:raise ValueError('computed conditional ISI needs its actual eligible mean and batch uncertainty')
                    matched=qualified_probability['symptom_matched_se'].get(p.component)
                    if matched is None or abs(p.smallest_estimator_se-matched)>1e-12:raise ValueError('claimed symptom SE differs from its authenticated raw pilot and actual tighter comparison')
                    if target.truth_kind=='observed_history_conditional_average':
                        if response.conditional_accuracy is None:raise ValueError('computed conditional ISI needs separate symptom accuracy evidence')
                        from .probability import SymptomPilotQualification
                        qualification=qualified_probability.get('symptom_qualifications',{}).get(p.component)
                        levels=response.conditional_accuracy.particle_levels
                        if (not isinstance(qualification,SymptomPilotQualification) or levels!=qualification.particle_levels or levels[-1]!=qualification.final_particle_level
                            or levels!=qualified_probability.get('probability_truth_particle_levels') or levels[-1]!=qualified_probability.get('probability_truth_final_particle_level')):
                            raise ValueError('symptom accuracy must match authenticated symptom pilot and probability truth particle levels/final level')
                        response.conditional_accuracy.require_accuracy(min(.05,.1*matched))
    if response.status!='computed':return
    if target.kind=='clinical':
        if target.estimand.estimand_id=='EST-INT':
            if not isinstance(result,InterruptionResult) or (result.intervention.action,result.comparator.action)!=(target.estimand.intervention,target.estimand.comparator):raise ValueError('EST-INT requires its unordered separate intervention vector')
            return
        if not isinstance(result,TruthResult) or result.estimand.id!=target.estimand.estimand_id or result.estimand.version!=target.estimand.estimand_version or result.estimand.sha256!=sha256(canonical(target.estimand.model_dump(mode='json'))) or result.dgp!=request.bindings.dgp or result.method!=request.method:
            raise ValueError('scalar truth target/DGP/method mismatch')
        if result.estimate.unit!=target.estimand.unit:raise ValueError('truth outcome unit mismatch')
        if not any(result.seed.namespace=='truth' and (result.seed.protocol,result.seed.scenario,result.seed.replicate,result.seed.patient,result.seed.time_index,result.seed.process)==(key.protocol,key.scenario,key.replicate,key.patient,key.time_index,key.process) for key in request.seeds):
            raise ValueError('canonical truth seed does not match an authorized full key')
        if result.method=='numerical':
            if result.draws!=response.batches*10000 or truth_status(result.numerical_standard_error,request.smallest_estimator_se,result.estimate.unit,batches=response.batches,cap=1000)!='resolved':
                raise ValueError('numeric truth has not achieved both absolute and matched-SE precision')
            if target.truth_kind=='observed_history_conditional_average':
                if response.conditional_accuracy is None:raise ValueError('rollout MCSE alone cannot resolve conditional particle bias')
                response.conditional_accuracy.require_accuracy(min(.05 if result.estimate.unit=='ISI_points' else .01,.1*request.smallest_estimator_se))
    elif target.kind=='fixture':
        if not isinstance(result,FixtureAnswer) or result.estimand!=target.estimand:raise ValueError('fixture answer mismatch')
    elif target.kind=='system':
        if not isinstance(result,SystemAnswer) or result.estimand!=target.estimand or result.fault!=target.expected_fault:raise ValueError('fault answer mismatch')
    elif target.kind=='parameter':
        if not isinstance(result,ParameterAnswer) or result.symbol!=target.symbol or result.parameters!=target.parameters:raise ValueError('structural parameter answer mismatch')
    elif not isinstance(result,AnalyticAnswer) or (result.fixture,result.quantity)!=(target.fixture,target.quantity):
        raise ValueError('native analytic fixture answer mismatch')
