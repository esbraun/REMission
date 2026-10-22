"""Reduced protocol wire types. Full ExactRef/source hashes never enter H*."""
from typing import Annotated, Literal
from datetime import timedelta
from pydantic import AwareDatetime, BaseModel, Field, model_validator
from .analysis import canonical, sha
from .common import Action, Identifier, Name, Sha256, StrictModel, VersionRef
from .entities import Eligibility, Workflow
from .observed_v2 import OutcomeWindow, Reward as FullReward, OperationalBurden
from .protocol import PROTOCOL_REFS, PolicyConstraint

Kinds = Literal['daily_report', 'isi', 'assignment', 'delivery', 'consent', 'approval',
                'decision_snapshot', 'protocol_snapshot', 'support_decision',
                'support_outcome_link', 'support_stage_closure', 'intercurrent_event', 'patient']


class ReducedHeader(StrictModel):
    record_id: Identifier
    patient_id: Identifier
    kind: Kinds
    record_schema: Literal['1.0.0', '2.0.0', '2.1.0']
    event_at: AwareDatetime
    recorded_at: AwareDatetime
    available_at: AwareDatetime
    lineage_id: Identifier
    revision: Annotated[int, Field(ge=1)]
    supersedes: Identifier | None
    duplicate_of: Identifier | None
    record_status: Literal['active', 'corrected', 'retracted']


def reduced_header(record):
    return record.model_dump(include=set(ReducedHeader.model_fields), mode='json') | {'record_schema': record.schema_version}


class ReducedRef(StrictModel):
    record_id: Identifier
    projection_sha256: Sha256


class Quality(ReducedHeader):
    kind: Literal['daily_report']
    sleep_quality: Annotated[float, Field(ge=0, le=10)] | None
    missingness: Literal['observed', 'missing', 'pending']

    @model_validator(mode='after')
    def indicator(self):
        if (self.missingness == 'observed') != (self.sleep_quality is not None):
            raise ValueError('quality indicator/value mismatch')
        if self.sleep_quality is not None and abs(self.sleep_quality*1000-round(self.sleep_quality*1000)) > 1e-8:
            raise ValueError('quality resolution .001 required')
        return self


class ISI(ReducedHeader):
    kind: Literal['isi']
    total: Annotated[int, Field(ge=0, le=28)]
    instrument_version: Literal['ISI-7-synthetic-14d-v1']
    recall_days: Literal[14]
    recall_start: AwareDatetime
    recall_end: AwareDatetime


class Assigned(ReducedHeader):
    kind: Literal['assignment']
    decision_id: Identifier
    approval_id: Identifier
    option: Action
    experimental: bool
    component: Literal['nof1', 'mrt_bandit'] | None
    probability: Annotated[float, Field(gt=0, le=1)] | None
    support_policy: VersionRef
    patient_blinded: Literal[False]
    clinician_blinded: Literal[False]
    clinician_override: Action | None
    override_reason: Name | None


class Delivered(ReducedHeader):
    kind: Literal['delivery']
    assignment_id: Identifier
    option: Action
    stage: Literal['offered', 'delivered', 'taken', 'not_taken', 'unknown']
    adherence: Annotated[float, Field(ge=0, le=1)] | None
    rescue: bool
    protocol_deviations: list[Name]


class Consent(ReducedHeader):
    kind: Literal['consent']
    component: Literal['nof1', 'mrt_bandit']
    consent_status: Literal['active', 'missing', 'expired', 'withdrawn']
    oversight_status: Literal['approved_synthetic', 'pending', 'expired', 'withdrawn']
    effective_at: AwareDatetime
    expires_at: AwareDatetime | None
    withdrawn_at: AwareDatetime | None


class Approved(ReducedHeader):
    kind: Literal['approval']
    decision_id: Identifier
    option: Action | None
    permitted_options: list[Action]
    purpose: Literal['ordinary_treatment', 'randomization_protocol']


class Decision(ReducedHeader):
    kind: Literal['decision_snapshot']
    cutoff: AwareDatetime
    workflow: Workflow
    eligibility: list[Eligibility]


class Snapshot(ReducedHeader):
    kind: Literal['protocol_snapshot']
    family: Literal['nof1_med', 'support']
    protocol: VersionRef
    template: VersionRef
    consent_refs: list[ReducedRef]
    approval_refs: list[ReducedRef]
    background_ref: ReducedRef
    support_refs: list[ReducedRef]
    activation_at: AwareDatetime


class Constraint(PolicyConstraint):
    allowed_actions: list[Literal['support_prompt', 'no_prompt']]
    reason: Literal['unrestricted', 'fixed_no_prompt', 'nof1_snapshot']
    snapshot_ref: ReducedRef | None


class Support(ReducedHeader):
    kind: Literal['support_decision']
    decision_snapshot: ReducedRef
    decision_index: Annotated[int, Field(ge=0)]
    cutoff: AwareDatetime
    context: list[ReducedRef]
    context_projection_sha256: Sha256
    policy: VersionRef
    mode: Literal['fixed', 'mrt', 'adaptive', 'frozen', 'paused']
    eligibility: list[Eligibility]
    policy_constraint: Constraint
    availability: Literal['unavailable', 'deterministic', 'randomized']
    unavailable_reasons: list[Name]
    probabilities: dict[Literal['support_prompt', 'no_prompt'], Annotated[float, Field(ge=0, le=1)]]
    assignment_id: Identifier | None
    distribution_persisted_at: AwareDatetime
    execution_receipt_id: Identifier
    outcome_window: OutcomeWindow
    outcome_link_id: Identifier


class Reward(FullReward):
    status: Literal['observed', 'pending', 'missing', 'undefined']
    report_ref: ReducedRef | None
    field: Literal['sleep_quality']
    unit: Literal['quality_points']
    reason: Name | None
    evidence_refs: list[ReducedRef]
    definition_refs: list[VersionRef]


class Burden(OperationalBurden):
    definition: VersionRef
    type: Literal['offered_prompt_count', 'delivered_prompt_count']
    unit: Literal['count']
    status: Literal['observed', 'pending', 'missing']
    value: Annotated[int, Field(ge=0)] | None
    source_refs: list[ReducedRef]


class Outcome(ReducedHeader):
    kind: Literal['support_outcome_link']
    support_decision: ReducedRef
    assignment_ref: ReducedRef | None
    window_id: Identifier
    assessment_at: AwareDatetime
    evaluated_as_of: AwareDatetime
    reward: Reward
    burden: list[Burden]
    offered_closure_ref: ReducedRef | None
    delivered_closure_ref: ReducedRef | None


class Closure(ReducedHeader):
    kind: Literal['support_stage_closure']
    support_decision: ReducedRef
    assignment_ref: ReducedRef | None
    window_id: Identifier
    decision_index: Annotated[int, Field(ge=0)]
    stage: Literal['offered', 'delivered']
    stage_completed_at: AwareDatetime
    status: Literal['complete', 'pending', 'missing']
    stage_event_refs: list[ReducedRef]
    row_count: Annotated[int, Field(ge=0)]
    reason: Name
    stage_ledger_id: Identifier
    completion_receipt_id: Identifier | None


class Interruption(ReducedHeader):
    kind: Literal['intercurrent_event']
    event_type: Literal['death', 'admission', 'discharge', 'regimen_change', 'steroid_change', 'discontinuation', 'override', 'rescue', 'fever_suspected_infection', 'confusion', 'fall']


class Patient(ReducedHeader):
    kind: Literal['patient']


ReducedRecord = Annotated[Quality | ISI | Assigned | Delivered | Consent | Approved | Decision | Snapshot | Support | Outcome | Closure | Interruption | Patient, Field(discriminator='kind')]
REDUCED_MODELS = {m.model_fields['kind'].annotation.__args__[0]: m for m in (Quality, ISI, Assigned, Delivered, Consent, Approved, Decision, Snapshot, Support, Outcome, Closure, Interruption, Patient)}


def nested_refs(value):
    if isinstance(value, ReducedRef):
        yield value
    elif isinstance(value, BaseModel):
        for name in type(value).model_fields:
            yield from nested_refs(getattr(value, name))
    elif isinstance(value, list):
        for item in value:
            yield from nested_refs(item)
    elif isinstance(value, dict):
        for item in value.values():
            yield from nested_refs(item)


class ProtocolHistory(StrictModel):
    schema_version: Literal['2.0.0']
    synthetic: Literal[True]
    kind: Literal['poc_protocol_history']
    version: Literal['poc-analysis-history-v1-protocol-v2']
    patient_id: Identifier
    family: Literal['nof1_med', 'support']
    cutoff: AwareDatetime
    origin: AwareDatetime
    protocol: VersionRef
    records: list[ReducedRecord]
    provenance: list[ReducedHeader]

    @model_validator(mode='after')
    def reduced_lineage(self):
        if self.protocol.model_dump() != PROTOCOL_REFS[self.family]:
            raise ValueError('protocol family identity mismatch')
        ids = {r.record_id: r for r in self.provenance}
        if len(ids) != len(self.provenance):
            raise ValueError('duplicate reduced provenance')
        successors, revisions = set(), set()
        for r in self.provenance:
            if r.patient_id != self.patient_id or not r.event_at <= r.recorded_at <= r.available_at < self.cutoff:
                raise ValueError('unavailable or cross-patient reduced lineage')
            if (r.revision == 1) != (r.supersedes is None) or r.record_id in (r.supersedes, r.duplicate_of):
                raise ValueError('invalid reduced revision')
            if r.duplicate_of is None:
                if (r.lineage_id, r.revision) in revisions:
                    raise ValueError('duplicate reduced revision')
                revisions.add((r.lineage_id, r.revision))
            for prior, duplicate in ((r.supersedes, False), (r.duplicate_of, True)):
                if prior is None:
                    continue
                old = ids.get(prior)
                if old is None or old.kind != r.kind or old.record_schema != r.record_schema or old.event_at != r.event_at or old.available_at > r.available_at:
                    raise ValueError('invalid/cross-version reduced dependency')
                if not duplicate:
                    if old.lineage_id != r.lineage_id or old.revision+1 != r.revision or prior in successors:
                        raise ValueError('invalid reduced correction')
                    successors.add(prior)
        heads = {k: v for k,v in ids.items() if k not in successors and v.duplicate_of is None and v.record_status != 'retracted'}
        active = {r.record_id: r for r in self.records}
        if len(active) != len(self.records) or active.keys() != heads.keys():
            raise ValueError('active reduced values must match lineage heads')
        for record in self.records:
            if record.model_dump(include=set(ReducedHeader.model_fields)) != heads[record.record_id].model_dump():
                raise ValueError('reduced provenance/value mismatch')
            for ref in nested_refs(record):
                target = active.get(ref.record_id)
                if target is None or sha(target.model_dump(mode='json')) != ref.projection_sha256:
                    raise ValueError('unresolved or changed reduced dependency')
            if record.kind=='support_decision':
                if record.event_at!=record.cutoff or record.outcome_window.starts_at!=record.cutoff:
                    raise ValueError('reduced support decision clock mismatch')
                if any(active[r.record_id].available_at>=record.cutoff for r in record.context):
                    raise ValueError('reduced support context must be strictly predecision')
                if active[record.decision_snapshot.record_id].available_at>record.cutoff:
                    raise ValueError('future reduced decision snapshot')
            elif record.kind=='protocol_snapshot':
                if record.family!=self.family or record.activation_at!=record.event_at:
                    raise ValueError('reduced snapshot family/activation mismatch')
                if any(active[r.record_id].available_at>record.activation_at for r in nested_refs(record)):
                    raise ValueError('future reduced protocol snapshot dependency')
            elif record.kind=='support_outcome_link':
                if record.assessment_at>record.evaluated_as_of or any(active[r.record_id].available_at>=record.evaluated_as_of for r in nested_refs(record)):
                    raise ValueError('future reduced outcome dependency')
            if record.kind in ('assignment','delivery'):
                permitted={'behavioral_continue','MED_A','MED_B','no_prompt'} if self.family=='nof1_med' else {'behavioral_continue','support_prompt','no_prompt'}
                if record.option not in permitted:raise ValueError('cross-family protocol action')
        if len({(r.assignment_id, r.event_at, r.stage) for r in self.records if r.kind == 'delivery'}) != sum(r.kind == 'delivery' for r in self.records):
            raise ValueError('duplicate delivery ownership')
        elapsed=(self.cutoff-self.origin).total_seconds()/86400
        if elapsed!=int(elapsed) or not 0<=elapsed<=84:raise ValueError('protocol fictional noon cutoff required')
        day=int(elapsed)
        if sorted(r.event_at for r in self.records if r.kind=='daily_report')!=[self.origin+timedelta(days=t,minutes=-1) for t in range(1,day+1)]:
            raise ValueError('one quality/missingness indicator per night required')
        isi=[r for r in self.records if r.kind=='isi']
        expected_isi=[self.origin+timedelta(days=t,hours=-1) for t in range(0,day+1,14)] if self.family=='nof1_med' else []
        if sorted(r.recall_end for r in isi)!=expected_isi:
            raise ValueError('scheduled unique cumulative ISI required')
        if any(r.recall_end-r.recall_start!=timedelta(days=14) or r.event_at!=r.recall_end+timedelta(minutes=59) for r in isi):
            raise ValueError('ISI recall/assessment mismatch')
        for delivery in (r for r in self.records if r.kind=='delivery'):
            assignment=active.get(delivery.assignment_id)
            if assignment is None or assignment.kind!='assignment' or assignment.option!=delivery.option or assignment.event_at>delivery.event_at:
                raise ValueError('unowned/inconsistent delivery assignment')
        return self
