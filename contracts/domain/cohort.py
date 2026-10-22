"""Explicit PA1 joint-cohort branch. Legacy visit/protocol envelopes are unchanged.

This source-only branch is deliberately not executable until exact-head numerical
and isolated-role qualification. Hashes bind the complete ordered reduced H*.
"""
from typing import Annotated, Literal

from pydantic import AwareDatetime, Field, model_validator

from .common import Identifier, Sha256, StrictModel, VersionRef
from .estimands import FitRequest
from .analysis import (AnalysisHistory, CONFIG, ESTIMAND_REF, MODEL_REF, PRIOR_REF,
    PROTOCOL_REF, DGP_REF, SCENARIO_REF, Effect, canonical, reference, sha, make_input)
from .borrowing import (SourceBundle, APPROVED_BUNDLES, BORROW_CONFIG,
    BORROW_MODEL_REF, NumericalSeeds, seed_value)


COORDINATE_SPEC = dict(id='poc-cohort-coordinates-v1', version='1.0.0',
    patient_order='ascending patient_id; common origin/cutoff grid',
    shared=['mu_b_standard', 'population_beta_c_standard',
            'population_beta_e_standard', 'a_standard'],
    patient=['b_standard', 'beta_c_standard', 'beta_e_standard',
             'innovation_nights_minus13_through_cutoff'],
    guide='existing exact Gaussian precision Cholesky and density/Jacobian correction')
COORDINATE_REF = reference(COORDINATE_SPEC['id'], COORDINATE_SPEC)
COHORT_MODEL_REF = reference('rounded-clipped-cohort-v1',
    dict(local=MODEL_REF, coordinates=COORDINATE_REF, shared_parameters_once=True))
COHORT_BORROW_MODEL_REF = reference('rounded-clipped-cohort-borrow-v1',
    dict(local=COHORT_MODEL_REF, source=BORROW_MODEL_REF, external_terms=2))
COHORT_CONFIG = dict(CONFIG, id='poc-visit-cohort-v1', model=COHORT_MODEL_REF,
    prior=PRIOR_REF, coordinates=COORDINATE_REF, cohort_size=12)
COHORT_BORROW_CONFIG = dict(BORROW_CONFIG, id='poc-visit-cohort-borrow-v1',
    model=COHORT_BORROW_MODEL_REF, coordinates=COORDINATE_REF, cohort_size=12)
COHORT_CONFIG_REF = reference(COHORT_CONFIG['id'], COHORT_CONFIG)
COHORT_BORROW_CONFIG_REF = reference(COHORT_BORROW_CONFIG['id'], COHORT_BORROW_CONFIG)
CONFIGURATIONS = {v['id']: (v, r) for v, r in [
    (COHORT_CONFIG, COHORT_CONFIG_REF), (COHORT_BORROW_CONFIG, COHORT_BORROW_CONFIG_REF)]}


class CohortMember(StrictModel):
    patient_id: Identifier
    patient_version: Annotated[int, Field(ge=1)]
    history_sha256: Sha256
    provenance_sha256: Sha256


class CohortSelection(StrictModel):
    """Owned common-cutoff selection, shared by preview and explicit approval."""
    cohort_id: Identifier
    patient_versions: dict[Identifier, Annotated[int, Field(ge=1)]]
    cutoff: AwareDatetime
    source_bundle_id: Identifier | None = None
    research_run_id: Identifier | None = None

    @model_validator(mode='after')
    def complete(self):
        if len(self.patient_versions)!=12:
            raise ValueError('Exactly twelve distinct current owned versions required.')
        return self


class CohortSubmission(CohortSelection):
    """Explicit cohort intent; does not widen legacy request1.0 or protocol2.0."""
    approved_manifest_sha256: Sha256
    previous_attempt: Identifier | None = None


class CohortManifest(StrictModel):
    schema: Literal['poc-cohort-manifest-v1/1.0.0']
    cohort_id: Identifier
    owner_id: Identifier
    panel_id: Identifier
    scope: Literal['interactive', 'research']
    research_run_id: Identifier | None
    research_execution: Literal['engine_run', 'contract_fixture'] | None = None
    cutoff: AwareDatetime
    origin: AwareDatetime
    protocol: VersionRef
    coordinates: VersionRef
    members: Annotated[list[CohortMember], Field(min_length=12, max_length=12)]

    @model_validator(mode='after')
    def admitted(self):
        ids = [m.patient_id for m in self.members]
        if ids != sorted(set(ids)):
            raise ValueError('cohort requires twelve distinct canonically ordered patients')
        if (self.scope == 'research') != (self.research_run_id is not None):
            raise ValueError('research run binding required only for research cohorts')
        if (self.scope == 'research') != (self.research_execution is not None):
            raise ValueError('research execution provenance required only for research cohorts')
        if self.protocol.model_dump() != PROTOCOL_REF or self.coordinates.model_dump() != COORDINATE_REF:
            raise ValueError('unsupported cohort protocol/coordinates')
        return self


class CohortHistory(StrictModel):
    schema: Literal['poc-cohort-history-v1/1.0.0']
    manifest: CohortManifest
    manifest_sha256: Sha256
    histories: Annotated[list[AnalysisHistory], Field(min_length=12, max_length=12)]

    @model_validator(mode='after')
    def admitted(self):
        manifest = self.manifest
        if self.manifest_sha256 != sha(manifest.model_dump(mode='json')):
            raise ValueError('cohort manifest checksum mismatch')
        seen = set()
        for member, history in zip(manifest.members, self.histories, strict=True):
            if (member.patient_id != history.patient_id or history.cutoff != manifest.cutoff
                    or history.origin != manifest.origin):
                raise ValueError('cohort member identity/common clock mismatch')
            if member.history_sha256 != sha(history.model_dump(mode='json')):
                raise ValueError('cohort member projection checksum mismatch')
            if member.provenance_sha256 != sha([r.model_dump(mode='json') for r in history.provenance]):
                raise ValueError('cohort member lineage checksum mismatch')
            ids = {r.record_id for r in history.provenance}
            if seen & ids:
                raise ValueError('record/likelihood ownership repeated across patients')
            seen.update(ids)
        return self


def admitted_configuration(ref):
    pair = CONFIGURATIONS.get(ref.id)
    if pair is None or ref.model_dump() != pair[1]:
        raise ValueError('unsupported cohort configuration')
    return pair[0]


class CohortInput(StrictModel):
    schema_version: Literal['3.0.0']
    synthetic: Literal[True]
    kind: Literal['poc_visit_cohort_input']
    attempt_id: Identifier
    request: FitRequest
    cohort: CohortHistory
    cohort_sha256: Sha256
    sources: SourceBundle | None
    source_set_sha256: Sha256 | None
    numerical_seeds: NumericalSeeds

    @model_validator(mode='after')
    def frozen(self):
        config = admitted_configuration(self.request.configuration)
        borrowed = config['id'] == COHORT_BORROW_CONFIG['id']
        ctx = self.request.context
        value = self.cohort.model_dump(mode='json')
        combined = dict(cohort=value, sources=self.sources.model_dump(mode='json') if self.sources else None)
        expected = [(ctx.estimand, ESTIMAND_REF), (ctx.comparator_estimand, ESTIMAND_REF),
            (ctx.dgp, DGP_REF), (ctx.scenario, SCENARIO_REF),
            (ctx.protocol, PROTOCOL_REF), (ctx.model, config['model']), (ctx.prior, config['prior']),
            (ctx.input_data, reference('poc-cohort-observed-input-v1', combined))]
        if any(a.model_dump() != b for a, b in expected):
            raise ValueError('cohort target/prior/input binding mismatch')
        if self.cohort_sha256 != sha(value) or ctx.observation_cutoff != self.cohort.manifest.cutoff:
            raise ValueError('cohort hash/cutoff mismatch')
        if (ctx.seed.namespace != 'fit' or ctx.seed.patient != self.cohort.manifest.cohort_id
                or ctx.seed.replicate != self.numerical_seeds.nuts):
            raise ValueError('cohort independent fit seed mismatch')
        if borrowed != (self.sources is not None) or borrowed != (self.source_set_sha256 is not None):
            raise ValueError('cohort V0/V1 source intent mismatch')
        if self.sources:
            self.sources.at_cutoff(self.cohort.manifest.cutoff)
            if (self.source_set_sha256 != self.sources.source_set_sha256
                    or APPROVED_BUNDLES.get(self.sources.bundle_id) != sha(combined['sources'])):
                raise ValueError('cohort source artifact mismatch')
            if any(min(.05, .1*s.se) < .03287180487219337 for s in self.sources.studies):
                raise ValueError('source SE outside qualified bridge precision')
        return self


def make_cohort_input(cohort, attempt_id, sources=None):
    config = COHORT_BORROW_CONFIG_REF if sources else COHORT_CONFIG_REF
    manifest = cohort.manifest
    seeds = dict(recipe='poc-pa3-seeds-v1', namespace='pa3-fit-20261021-v1')
    for key, purpose in [('nuts', 'nuts'), ('effect_rollout', 'effect-rollout'),
                         ('prior_check', 'prior-check'), ('bridge_reference', 'bridge-reference')]:
        seeds[key] = seed_value(seeds['namespace'], -1, -1, 0, manifest.cohort_id,
            manifest.cutoff.isoformat(), purpose+':'+config['sha256']+':'+attempt_id)
    base = make_input(cohort.histories[0], attempt_id, seeds['nuts']).model_dump(mode='json')
    value = cohort.model_dump(mode='json')
    source = sources.model_dump(mode='json') if sources else None
    ctx = base['request']['context']
    settings = CONFIGURATIONS[config['id']][0]
    ctx.update(model=settings['model'], prior=settings['prior'],
        input_data=reference('poc-cohort-observed-input-v1', dict(cohort=value, sources=source)))
    ctx['seed'].update(patient=manifest.cohort_id, protocol=config['id'])
    base['request']['configuration'] = config
    return CohortInput.model_validate_json(canonical(dict(schema_version='3.0.0', synthetic=True,
        kind='poc_visit_cohort_input', attempt_id=attempt_id, request=base['request'], cohort=value,
        cohort_sha256=sha(value), sources=source,
        source_set_sha256=sources.source_set_sha256 if sources else None, numerical_seeds=seeds)))


class PatientEffect(StrictModel):
    patient_id: Identifier
    history_sha256: Sha256
    status: Literal['completed', 'abstained', 'failed']
    reason: str | None
    effect: Effect | None
    diagnostics: dict

    @model_validator(mode='after')
    def accepted(self):
        if (self.status == 'completed') != (self.effect is not None) or (self.status == 'completed') != (self.reason is None):
            raise ValueError('unaccepted patient effect cannot expose an interval')
        return self


class CohortResult(StrictModel):
    schema_version: Literal['3.0.0']
    synthetic: Literal[True]
    kind: Literal['poc_visit_cohort_result']
    attempt_id: Identifier
    input_sha256: Sha256
    cohort_sha256: Sha256
    manifest: CohortManifest
    manifest_sha256: Sha256
    source_set_sha256: Sha256 | None
    configuration: VersionRef
    estimand: VersionRef
    status: Literal['completed', 'abstained', 'failed']
    reason: str | None
    patients: Annotated[list[PatientEffect], Field(min_length=12, max_length=12)]
    diagnostics: dict
    artifacts: list[dict]
    limitations: list[str]

    @model_validator(mode='after')
    def accepted(self):
        config = admitted_configuration(self.configuration)
        if self.estimand.model_dump() != ESTIMAND_REF or self.manifest_sha256 != sha(self.manifest.model_dump(mode='json')):
            raise ValueError('cohort result target/manifest mismatch')
        if (config['id'] == COHORT_BORROW_CONFIG['id']) != (self.source_set_sha256 is not None):
            raise ValueError('cohort result source intent mismatch')
        if [(p.patient_id, p.history_sha256) for p in self.patients] != [(m.patient_id, m.history_sha256) for m in self.manifest.members]:
            raise ValueError('cohort result patient/projection identity mismatch')
        if self.status != 'completed' and any(p.effect is not None for p in self.patients):
            raise ValueError('unaccepted joint fit cannot expose any interval')
        if (self.status == 'completed') != (self.reason is None):
            raise ValueError('cohort failure/abstention requires a reason')
        if self.status == 'completed' and (self.reason is not None or any(p.status != 'completed' for p in self.patients)):
            raise ValueError('cohort completion requires every patient gate')
        canonical(self.model_dump(mode='json'))
        return self


def require_executable(product):
    """No success fixture or new configuration enters the native allowlist."""
    cohort=getattr(product,'cohort',None)
    manifest=cohort.manifest if cohort is not None else getattr(product,'manifest',None)
    if manifest is not None and manifest.research_execution=='contract_fixture':
        raise ValueError('contract fixture cohort is never executable or acceptable fit evidence')
    raise ValueError('cohort execution unavailable pending independent numerical and role qualification')
