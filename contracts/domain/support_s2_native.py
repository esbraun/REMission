"""Closed S2 native SOURCE preparation. Neither execution nor serving admission.

These identities are separate from immutable PROD1/candidate configurations.
Only scalar contracts live here; binary/scientific validation lives in learner.
"""
from typing import Annotated, Literal
from pydantic import AwareDatetime, Field, field_validator, model_validator
from .analysis import canonical, reference, sha
from .common import Identifier, Sha256, StrictModel, VersionRef
from .support_s2_app import (S2FitInput, S2ExtensionRequest, SamplerSettings,
    DiagnosticSettings, ExtensionPolicy, FitSeedRecord, validate_extension)
from .support_s2_fit import FitMember, MODEL_REF, PRIOR_REF

FEATURES = ('prior_available_quality_default7', 'no_prior_available_quality',
    'previous_six_nights_delivered_prompts', 'reward_night/84')
SCALARS = ('mu_alpha', 'mu_tau', 's_alpha', 's_tau', 's_e', 's_Q', 'rho')
PATIENT = ('z', 'u', 'alpha', 'tau', 'e_T')
MONITORED = (*SCALARS, 'b', *PATIENT,
    *(name + str(i) for i in range(12) for name in ('epsilon_', 'error_')))
STATS = ('energy', 'lp', 'diverging', 'tree_depth', 'sampler_warning')
MIB = 1024**2
INPUT_CAP = 8*MIB
RESULT_CAP = MIB
PROGRESS_CAP = 2048
FILE_CAPS = {1000:72*MIB, 2000:136*MIB}
TOTAL_CAP = 216*MIB  # Both original and extension posterior + both scalar results.


def variable_schema(cutoff):
    if type(cutoff) is not int or cutoff not in (14,28,42,56,70,84):
        raise ValueError('S2_full_grid_cutoff_required')
    variables = {}
    for name in MONITORED:
        dimensions = () if name in SCALARS else ('feature',) if name == 'b' else ('patient',) if name in PATIENT else ('night_'+name.split('_')[-1],)
        unit = ('dimensionless' if name in ('rho','z','u') or name.startswith('epsilon_')
            else 'quality_points_per_named_feature' if name == 'b'
            else 'quality_points_per_centered_assignment' if name in ('mu_tau','s_tau','tau')
            else 'quality_points')
        variables[name] = dict(dims=['chain','draw',*dimensions], dtype='float64', unit=unit)
    stats = {name:dict(dims=['chain','draw'],
        dtype='bool' if name in ('diverging','sampler_warning') else 'int64' if name=='tree_depth' else 'float64',
        unit='log_density' if name=='lp' else 'negative_log_density' if name=='energy' else 'count' if name=='tree_depth' else 'indicator') for name in STATS}
    return dict(posterior=variables, sample_stats=stats)


def dimension_bound(cutoff, draws):
    """Stdlib scalar proof, before any arrays/read/allocation/transport.

    7 scalars + 4 b + 5*12 patient + 24*T latent scalars per draw.
    Stats: two float64, one int64 and two bool. Coordinates are bounded
    separately; the enforced file allowance includes 8MiB metadata overhead.
    """
    variable_schema(cutoff)
    if type(draws) is not int or draws not in FILE_CAPS:
        raise ValueError('S2_all_original_saved_draws_required')
    posterior = 4*draws*(7+4+5*12+24*cutoff)*8
    stats = 4*draws*(8+8+8+1+1)
    coordinates = (4+draws+12*cutoff)*8 + 12*128*4 + 4*128*4
    result = dict(posterior_bytes=posterior, sample_stats_bytes=stats,
        coordinate_bytes=coordinates, uncompressed_bytes=posterior+stats+coordinates,
        file_cap=FILE_CAPS[draws], result_cap=RESULT_CAP)
    if result['uncompressed_bytes']+8*MIB > FILE_CAPS[draws]:
        raise ValueError('S2_dimension_bound_exceeds_predeclared_file_cap')
    return result


CONFIG = dict(schema='s2-native-source-1.0.0', sampler=SamplerSettings().model_dump(),
    diagnostics=DiagnosticSettings().model_dump(), extension=ExtensionPolicy().model_dump(),
    construction=dict(floatX='float64',cast_policy='numpy+floatX',compiledir='/tmp/pytensor-s2',
        pymc='6.3.2',pytensor='3.3.4',linker='cvm',optimizer='NATIVE_OPTIMIZER'),
    schema_at_max=variable_schema(84), bounds_at_max={str(n):dimension_bound(84,n) for n in FILE_CAPS},
    total_cap=TOTAL_CAP, input_cap=INPUT_CAP, result_cap=RESULT_CAP, progress_cap=PROGRESS_CAP,
    operation=dict(status='PROSPECTIVE_NOT_QUALIFIED', outer_seconds=7200,
        preflight_seconds=120, fit_end_seconds=6900, collection_end_seconds=7020,
        ingest_end_seconds=7080, reap_end_seconds=7200,
        origin='one_absolute_operation_origin_including_preflight_both_attempts_collection_ingest_reap',
        cpu=2,memory_bytes=2*1024**3,swap_total_bytes=2*1024**3,native_threads=1,
        pid_limit=None,tmp_bytes=None,compiler_tmp_exec=None),
    qualification=dict(source_review=None,operation_review=None,image=None,installed_closure=None,
        installed_diagnostic_api=None,genuine_input=None,root_go=None),
    executable=False,serving_authority=False)
CONFIG_REF = reference('poc-support-s2-native-source-v1', CONFIG)
SCHEMA_REF = reference('poc-support-s2-native-posterior-v1', dict(
    variables=CONFIG['schema_at_max'],features=FEATURES,chain=[0,1,2,3],
    draw='0..999 OR 0..1999',night='1..T',groups=['posterior','sample_stats'],
    coordinate_dtypes='int64 axes; patient/feature fixed ASCII S128 encoded NC_CHAR with 128-byte axis; no VLEN',
    attrs=['schema_sha256','input_sha256','ownership_sha256'],all_draws=True))


class NativeInput(StrictModel):
    schema_version: Literal['s2-native-source-1.0.0']
    kind: Literal['poc_support_s2_native_fit_input']
    initial: S2FitInput
    extension: S2ExtensionRequest | None
    parent_result_reference: VersionRef | None
    retained_initial_artifact: 'Artifact | None'
    configuration: VersionRef
    posterior_schema: VersionRef
    executable: Literal[False]

    @model_validator(mode='after')
    def bound(self):
        if self.configuration.model_dump()!=CONFIG_REF or self.posterior_schema.model_dump()!=SCHEMA_REF:
            raise ValueError('S2_native_configuration_or_schema_changed')
        if self.extension is not None:validate_extension(self.extension,self.initial)
        if (self.extension is None)!=(self.parent_result_reference is None) or (self.extension is None)!=(self.retained_initial_artifact is None):
            raise ValueError('S2_extension_requires_retained_parent_result_and_artifact')
        dimension_bound(self.initial.export.provenance.cutoff_day,self.draws)
        return self

    @property
    def attempt_id(self):return self.initial.attempt_id if self.extension is None else self.extension.attempt_id
    @property
    def draws(self):return 1000 if self.extension is None else 2000
    @property
    def seed_record(self):return self.initial.seed_record if self.extension is None else self.extension.seed_record


def ownership(product):
    p=product.initial.export.provenance
    value=dict(schema_version='s2-native-ownership-v1',attempt_id=product.attempt_id,
        parent_attempt_id=None if product.extension is None else product.initial.attempt_id,
        input_sha256=sha(product.model_dump(mode='json')),initial_input_sha256=sha(product.initial.model_dump(mode='json')),
        owner_id=p.owner_id,store_id=p.store_id,authority_generation=product.initial.export.selection.authority_generation,
        generation_id=p.generation_id,cohort_id=p.cohort_id,target_id=p.target_id,purpose=p.purpose,
        cutoff=p.cutoff.isoformat(),cutoff_day=p.cutoff_day,
        members=[m.model_dump(mode='json') for m in p.members],histories_sha256=p.histories_sha256,
        contribution_sha256=product.initial.export.contribution_sha256,
        export_reference=product.initial.export.reference.model_dump(),
        model=p.definitions['model'].model_dump(),prior=p.definitions['prior'].model_dump(),
        configuration=CONFIG_REF,posterior_schema=SCHEMA_REF,seed_record=product.seed_record.model_dump(mode='json'))
    return OwnershipManifest.model_validate_json(canonical(value)).model_dump(mode='json')


class OwnershipManifest(StrictModel):
    schema_version: Literal['s2-native-ownership-v1']
    attempt_id: Identifier
    parent_attempt_id: Identifier | None
    input_sha256: Sha256
    initial_input_sha256: Sha256
    owner_id: Identifier
    store_id: Identifier
    authority_generation: Annotated[int,Field(ge=1)]
    generation_id: Identifier
    cohort_id: Identifier
    target_id: Identifier
    purpose: Literal['EST-POLICY:poc-support-refresh-v1']
    cutoff: AwareDatetime
    cutoff_day: Literal[14,28,42,56,70,84]
    members: Annotated[tuple[FitMember,...],Field(min_length=12,max_length=12)]
    histories_sha256: Sha256
    contribution_sha256: Sha256
    export_reference: VersionRef
    model: VersionRef
    prior: VersionRef
    configuration: VersionRef
    posterior_schema: VersionRef
    seed_record: FitSeedRecord

    @model_validator(mode='after')
    def complete(self):
        ids=[m.patient_id for m in self.members]
        if ids!=sorted(set(ids)) or self.target_id not in ids:
            raise ValueError('S2_ownership_exact_ordered_twelve_target_required')
        if (self.model.model_dump()!=MODEL_REF or self.prior.model_dump()!=PRIOR_REF
                or self.configuration.model_dump()!=CONFIG_REF or self.posterior_schema.model_dump()!=SCHEMA_REF
                or self.seed_record.attempt_id!=self.attempt_id or self.seed_record.owner_id!=self.owner_id
                or self.seed_record.key.patient!=self.target_id or self.seed_record.key.time_index!=self.cutoff_day):
            raise ValueError('S2_ownership_model_prior_config_seed_binding_changed')
        return self


Finite = Annotated[float,Field(ge=0)]


class VariableDiagnostics(StrictModel):
    rhat: Finite
    ess_bulk: Finite
    ess_tail: Finite
    mcse: Finite


class FitDiagnostics(StrictModel):
    variables: dict[str,VariableDiagnostics]
    energy_min: tuple[float,float,float,float]
    energy_max: tuple[float,float,float,float]
    bfmi: tuple[Finite,Finite,Finite,Finite]
    divergences: Annotated[int,Field(ge=0)]
    tree_depth_hits: Annotated[int,Field(ge=0)]
    maximum_tree_depth: Annotated[int,Field(ge=0,le=12)]
    sampler_warnings: Annotated[int,Field(ge=0)]
    python_warnings: Annotated[int,Field(ge=0)]
    accepted: bool

    @model_validator(mode='after')
    def complete(self):
        if set(self.variables)!=set(MONITORED):raise ValueError('S2_diagnostic_inventory_incomplete')
        if any(lo>hi for lo,hi in zip(self.energy_min,self.energy_max)):
            raise ValueError('S2_energy_range_invalid')
        accepted=(all(v.rhat<1.01 and v.ess_bulk>=400 and v.ess_tail>=400 for v in self.variables.values())
            and all(v>.3 for v in self.bfmi) and not self.divergences and not self.tree_depth_hits
            and self.maximum_tree_depth<12 and not self.sampler_warnings and not self.python_warnings)
        if self.accepted is not accepted:raise ValueError('S2_diagnostic_acceptance_mismatch')
        return self


class Artifact(StrictModel):
    path: Literal['posterior.nc']
    bytes: Annotated[int,Field(gt=0,le=136*MIB)]
    sha256: Sha256
    uncompressed_bytes: Annotated[int,Field(gt=0,le=136*MIB)]


class BinarySemantics(StrictModel):
    schema_version: Literal['s2-native-binary-v1']
    posterior_schema: VersionRef
    input_sha256: Sha256
    ownership_sha256: Sha256
    chains: Literal[4]
    draws: Literal[1000,2000]
    cutoff: Literal[14,28,42,56,70,84]
    artifact: Artifact
    roundtrip: Literal[True]


class TrustedLaunch(StrictModel):
    schema_version: Literal['s2-native-trusted-launch-v1']
    input_sha256: Sha256
    ownership_sha256: Sha256
    configuration: VersionRef
    source_commit: Annotated[str,Field(pattern=r'^[a-f0-9]{40}$')]
    learner_image: Annotated[str,Field(pattern=r'^sha256:[a-f0-9]{64}$')]
    installed_closure_sha256: Sha256
    claim_sha256: Sha256


class ActualVM(StrictModel):
    vm_type: Literal['pytensor.link.c.cvm.CVM']
    linker: Literal['VMLinker']
    use_cloop: Literal[True]
    c_thunks: Literal[True]
    callback_empty: Literal[True]
    callback_input_empty: Literal[True]
    limitation: Literal['Whole VM checked; individual operations may use ordinary Python thunks.']


class Coordinate(StrictModel):
    name: Identifier
    shape: Annotated[list[Annotated[int,Field(ge=1,le=84)]],Field(max_length=1)]
    dtype: Literal['float64']
    start: Annotated[int,Field(ge=0,le=1043)]
    stop: Annotated[int,Field(ge=1,le=1043)]


class Compilation(StrictModel):
    index: Annotated[int,Field(ge=1,le=8)]
    actual_vm: ActualVM
    compiled_optimizer: dict
    coordinate_map: Annotated[list[Coordinate],Field(min_length=22,max_length=22)]
    compiled_graph_float32_constants: Literal[0]
    unowned_random_variables: Literal[0]
    strict_prior_operands: Literal[True]
    finite_logp_dlogp: Literal[True]

    @field_validator('compiled_optimizer')
    @classmethod
    def optimizer(cls,value):
        from .borrow_runtime import NATIVE_OPTIMIZER
        if value!=NATIVE_OPTIMIZER:raise ValueError('S2_actual_optimizer_identity_changed')
        return value


class NativeExecution(StrictModel):
    launch: TrustedLaunch
    native_compilations: Annotated[list[Compilation],Field(min_length=1,max_length=8)]
    callback_calls: Annotated[int,Field(ge=8000,le=16000)]
    python_warnings: Annotated[int,Field(ge=0,le=1000)]


class NativeResult(StrictModel):
    schema_version: Literal['s2-native-source-1.0.0']
    kind: Literal['poc_support_s2_native_fit_result']
    attempt_id: Identifier
    configuration: VersionRef
    ownership: OwnershipManifest
    diagnostics: FitDiagnostics
    semantics: BinarySemantics
    execution: NativeExecution
    status: Literal['completed','abstained']
    reason: Literal['fit_diagnostics_unmet'] | None
    serving_authority: Literal[False]

    @model_validator(mode='after')
    def closed(self):
        finite_tree(self.model_dump())
        if self.configuration.model_dump()!=CONFIG_REF:
            raise ValueError('S2_native_result_configuration_changed')
        if (self.status=='completed') is not self.diagnostics.accepted or self.reason != (None if self.diagnostics.accepted else 'fit_diagnostics_unmet'):
            raise ValueError('S2_result_diagnostics_status_mismatch')
        return self


def validate_result(result, product, trusted):
    """trusted is service-owned launch/custody, never a worker-supplied claim."""
    expected=ownership(product)
    if (result.attempt_id!=product.attempt_id or result.ownership.model_dump(mode='json')!=expected
            or result.semantics.input_sha256!=expected['input_sha256']
            or result.semantics.ownership_sha256!=sha(expected)
            or result.semantics.posterior_schema.model_dump()!=SCHEMA_REF
            or result.semantics.draws!=product.draws or result.semantics.cutoff!=product.initial.export.provenance.cutoff_day):
        raise ValueError('S2_result_complete_ownership_or_binary_identity_mismatch')
    bound=dimension_bound(result.semantics.cutoff,product.draws)
    if (result.semantics.artifact.bytes>bound['file_cap']
            or result.semantics.artifact.uncompressed_bytes!=bound['uncompressed_bytes']):
        raise ValueError('S2_result_artifact_dimension_or_file_bound_mismatch')
    validate_execution(result.execution.model_dump(mode='json'),product,trusted)
    return result


def validate_execution(value,product,trusted):
    # A fixed closed binding is prepared, but no current source/image/API/OP
    # qualification exists. Even a rehashed result cannot create authority.
    if not isinstance(trusted,dict) or set(trusted)!={'schema_version','input_sha256','ownership_sha256','configuration',
            'source_commit','learner_image','installed_closure_sha256','claim_sha256'}:
        raise ValueError('S2_service_owned_launch_and_artifact_custody_required')
    import re
    if (trusted['schema_version']!='s2-native-trusted-launch-v1'
            or trusted['input_sha256']!=sha(product.model_dump(mode='json'))
            or trusted['ownership_sha256']!=sha(ownership(product)) or trusted['configuration']!=CONFIG_REF
            or re.fullmatch('[a-f0-9]{40}',trusted['source_commit']) is None
            or re.fullmatch('sha256:[a-f0-9]{64}',trusted['learner_image']) is None
            or any(re.fullmatch('[a-f0-9]{64}',trusted[k]) is None for k in
                ('installed_closure_sha256','claim_sha256'))):
        raise ValueError('S2_launch_identity_or_owned_artifact_custody_mismatch')
    if (not isinstance(value,dict) or set(value)!={'launch','native_compilations','callback_calls','python_warnings'}
            or value['launch']!=trusted or type(value['callback_calls']) is not int
            or value['callback_calls']!=8*product.draws or type(value['python_warnings']) is not int
            or value['python_warnings']<0 or not isinstance(value['native_compilations'],list)
            or not 1<=len(value['native_compilations'])<=8):
        raise ValueError('S2_actual_sampling_execution_evidence_missing')
    from .borrow_runtime import NATIVE_OPTIMIZER
    for i,record in enumerate(value['native_compilations']):
        if (set(record)!={'index','actual_vm','compiled_optimizer','coordinate_map',
                'compiled_graph_float32_constants','unowned_random_variables','strict_prior_operands','finite_logp_dlogp'}
                or record['index']!=i+1 or record['compiled_optimizer']!=NATIVE_OPTIMIZER
                or record['coordinate_map']!=coordinate_layout(product.initial.export.provenance.cutoff_day)
                or record['compiled_graph_float32_constants']!=0 or record['unowned_random_variables']!=0
                or record['strict_prior_operands'] is not True or record['finite_logp_dlogp'] is not True):
            raise ValueError('S2_actual_sampler_graph_evidence_invalid')
        vm=record['actual_vm']
        if (set(vm)!={'vm_type','linker','use_cloop','c_thunks','callback_empty','callback_input_empty','limitation'}
                or vm['vm_type']!='pytensor.link.c.cvm.CVM' or vm['linker']!='VMLinker'
                or any(vm[k] is not True for k in ('use_cloop','c_thunks','callback_empty','callback_input_empty'))
                or vm['limitation']!='Whole VM checked; individual operations may use ordinary Python thunks.'):
            raise ValueError('S2_actual_sampler_CVM_evidence_invalid')


def coordinate_layout(cutoff):
    variable_schema(cutoff)
    import math
    shapes=[('mu_alpha',()),('mu_tau',()),('b',(4,)),('s_alpha_log__',()),
        ('s_tau_log__',()),('s_e_log__',()),('s_Q_log__',()),('rho_interval__',()),
        ('z',(12,)),('u',(12,)),*[('epsilon_'+str(i),(cutoff,)) for i in range(12)]]
    result=[];offset=0
    for name,shape in shapes:
        size=math.prod(shape)
        result.append(dict(name=name,shape=list(shape),dtype='float64',start=offset,stop=offset+size));offset+=size
    return result


def finite_tree(value):
    import math
    if isinstance(value,dict):
        for v in value.values():finite_tree(v)
    elif isinstance(value,(list,tuple)):
        for v in value:finite_tree(v)
    elif type(value) in (int,float) and not math.isfinite(value):
        raise ValueError('S2_nonfinite_scalar_manifest')


def parse_native_result(raw):
    """Bounded closed scalar JSON. Does not read any file or scientific bytes."""
    import json
    if not isinstance(raw,bytes) or not 0<len(raw)<=RESULT_CAP:
        raise ValueError('S2_result_byte_cap')
    def pairs(items):
        result={}
        for key,value in items:
            if key in result:raise ValueError('S2_duplicate_result_key')
            result[key]=value
        return result
    value=json.loads(raw,object_pairs_hook=pairs,
        parse_constant=lambda _:(_ for _ in ()).throw(ValueError('S2_nonfinite_result_JSON')))
    nodes=0
    def bounded(item,depth=0):
        nonlocal nodes
        nodes+=1
        if depth>20 or nodes>12000:raise ValueError('S2_result_structure_cap')
        if isinstance(item,dict):
            if len(item)>64:raise ValueError('S2_result_object_cap')
            for key,child in item.items():bounded(key,depth+1);bounded(child,depth+1)
        elif isinstance(item,list):
            if len(item)>84:raise ValueError('S2_result_array_cap')
            for child in item:bounded(child,depth+1)
        elif isinstance(item,str) and len(item)>512:raise ValueError('S2_result_string_cap')
    bounded(value);finite_tree(value)
    return NativeResult.model_validate_json(canonical(value))


def validate_extension_admission(product,parent,parent_product,parent_trusted, *, indicator_failed=False):
    """Explicit caller selection only; no retry, concatenation or new prior."""
    if product.extension is None or parent_product.extension is not None:
        raise ValueError('S2_exactly_one_explicit_extension_only')
    validate_result(parent,parent_product,parent_trusted)
    if (product.initial!=parent_product.initial
            or product.parent_result_reference.model_dump()!=reference('poc-support-s2-native-fit-result-v1',parent.model_dump(mode='json'))
            or product.retained_initial_artifact!=parent.semantics.artifact
            or product.retained_initial_artifact.bytes+FILE_CAPS[2000]+2*RESULT_CAP>TOTAL_CAP):
        raise ValueError('S2_extension_parent_retention_or_original_evidence_mismatch')
    if ((product.extension.trigger=='canonical_fit_diagnostics_failed' and parent.diagnostics.accepted)
            or (product.extension.trigger=='required_indicator_precision_failed' and indicator_failed is not True)):
        raise ValueError('S2_extension_trigger_not_established')
    return product


def require_executable(product=None):
    raise ValueError('S2_native_source_image_API_caps_genuine_input_and_OP_unqualified')


NativeInput.model_rebuild()
