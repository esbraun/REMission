"""Fixed P1 protocol records and minor-version dispatch; no activation authority."""
from typing import Annotated, Literal, Union

from pydantic import AwareDatetime, Discriminator, Field, Tag, TypeAdapter, model_validator

from .analysis import reference
from .common import Identifier, StrictModel, VersionRef
from .observed_v2 import (ExactRef, LearnerHistoryV2, ObservedHistoryV2,
                          RecordProvenanceV2, RecordV2, SupportDecision,
                          _V1, _V2, record_tag, validate_lineage_v2)
from .boundaries import lineage_heads, no_postdeath_outcomes, visible_records

LAW = 'poc-longitudinal-v2'
LAW_REF = reference(LAW, 'PA4/5 20261021: v1 base streams; separate medication/support streams; observed-only interface')
NOF1_REF = reference('poc-nof1-template-v1', '8 independent .5 seven-night blocks + two washout nights each; review36/72; frozen continuation/no-prompt; no efficacy stopping')
SUPPORT_REF = reference('poc-support-envelope-v1', 'noon decision/20h delivery/next morning quality; max3 rolling7; no consecutive; hold denies; S0 no prompt/S1 .5/S2 bounded')
PROTOCOL_REFS = {'nof1_med': NOF1_REF, 'support': SUPPORT_REF}


class ProtocolPanel(StrictModel):
    schema_version: Literal['2.0.0']
    kind: Literal['poc_protocol_panel']
    seed: Annotated[int, Field(ge=0, le=2147483647)]
    count: Annotated[int, Field(ge=2, le=24)]
    family: Literal['nof1_med', 'support']
    law: VersionRef
    protocol: VersionRef

    @model_validator(mode='after')
    def selected(self):
        if self.law.model_dump() != LAW_REF or self.protocol.model_dump() != PROTOCOL_REFS[self.family]:
            raise ValueError('unsupported explicit protocol/law identity')
        return self


class PolicyConstraint(StrictModel):
    allowed_actions: list[Literal['support_prompt', 'no_prompt']]
    reason: Literal['unrestricted', 'fixed_no_prompt', 'nof1_snapshot']
    snapshot_ref: ExactRef | None

    @model_validator(mode='after')
    def restriction(self):
        if self.reason == 'unrestricted':
            if set(self.allowed_actions) != {'support_prompt', 'no_prompt'} or len(self.allowed_actions) != 2 or self.snapshot_ref is not None:
                raise ValueError('unrestricted policy permits both actions without a snapshot restriction')
        elif self.allowed_actions != ['no_prompt'] or self.snapshot_ref is None:
            raise ValueError('fixed/frozen policy requires exact no-prompt snapshot')
        return self


class SupportDecisionV21(SupportDecision):
    schema_version: Literal['2.1.0']
    policy_constraint: PolicyConstraint

    @model_validator(mode='after')
    def executed_vector(self):
        actions = {'support_prompt', 'no_prompt'}
        if set(self.probabilities) != actions or len(self.eligibility) != 2 or {e.action for e in self.eligibility} != actions:
            raise ValueError('complete clinical eligibility and final distribution required')
        if any(e.status != 'eligible' and not e.reasons for e in self.eligibility):
            raise ValueError('excluded clinical actions require reasons')
        expected = {'fixed': 'fixed_no_prompt', 'frozen': 'nof1_snapshot', 'mrt': 'unrestricted', 'adaptive': 'unrestricted'}
        if self.mode != 'paused' and self.policy_constraint.reason != expected[self.mode]:
            raise ValueError('support mode/policy restriction mismatch')
        clinical = {e.action for e in self.eligibility if e.status == 'eligible'}
        executed = clinical & set(self.policy_constraint.allowed_actions) if self.mode != 'paused' else set()
        if self.event_at != self.cutoff or self.outcome_window.starts_at != self.cutoff:
            raise ValueError('support event/cutoff/window mismatch')
        if not self.event_at <= self.distribution_persisted_at <= self.recorded_at:
            raise ValueError('pre-outcome distribution persistence clock required')
        p = self.probabilities
        if self.availability == 'unavailable':
            if executed or any(p.values()) or self.assignment_id is not None or not self.unavailable_reasons:
                raise ValueError('unavailable requires empty executed set/zero masses/no assignment/reasons')
        else:
            if self.unavailable_reasons or self.assignment_id is None or abs(sum(p.values()) - 1) > 1e-12:
                raise ValueError('available vector must normalize and identify assignment')
            if self.availability == 'deterministic':
                if len(executed) != 1 or any(p[a] != float(a in executed) for a in actions):
                    raise ValueError('determinism must equal clinical intersection policy')
            elif executed != actions or any(not .1 <= p[a] <= .9 for a in actions):
                raise ValueError('randomized final masses require both executed actions and bounds')
            if self.mode == 'mrt' and self.availability == 'randomized' and any(p[a] != .5 for a in actions):
                raise ValueError('canonical S1 probability is exactly .5')
        return self


class ProtocolSnapshot(RecordV2):
    schema_version: Literal['2.1.0']
    kind: Literal['protocol_snapshot']
    family: Literal['nof1_med', 'support']
    protocol: VersionRef
    template: VersionRef
    consent_refs: Annotated[list[ExactRef], Field(min_length=1)]
    approval_refs: Annotated[list[ExactRef], Field(min_length=1)]
    background_ref: ExactRef
    support_refs: list[ExactRef]
    activation_at: AwareDatetime

    @model_validator(mode='after')
    def public_design(self):
        if self.protocol.model_dump() != PROTOCOL_REFS[self.family] or self.template != self.protocol or self.activation_at != self.event_at:
            raise ValueError('unsupported snapshot family/template/activation')
        if self.family=='nof1_med' and not self.support_refs:
            raise ValueError('N-of-1 snapshot requires explicit frozen no-prompt evidence')
        return self


_V21 = [SupportDecisionV21, ProtocolSnapshot]
ObservedRecordV21 = Annotated[Union[tuple(Annotated[m, Tag(f'{m.model_fields["schema_version"].annotation.__args__[0]}:{m.model_fields["kind"].annotation.__args__[0]}')] for m in [*_V1, *_V2, *_V21])], Discriminator(record_tag)]
RECORD_ADAPTER_V21 = TypeAdapter(ObservedRecordV21)


class RecordProvenanceV21(RecordProvenanceV2):
    schema_version: Literal['1.0.0', '2.0.0', '2.1.0']


def provenance_v21(record):
    return RecordProvenanceV21.model_validate(record.model_dump(include=set(RecordProvenanceV21.model_fields)))


class LearnerHistoryV21(LearnerHistoryV2):
    schema_version: Literal['2.1.0']
    records: list[ObservedRecordV21]
    provenance: list[RecordProvenanceV21]

    @model_validator(mode='after')
    def projection(self):
        if any(r.patient_id != self.patient_id for r in [*self.records, *self.provenance]):
            raise ValueError('projection patient mismatch')
        validate_lineage_v2(self.provenance)
        if len(visible_records(self.provenance, self.cutoff)) != len(self.provenance):
            raise ValueError('strict-before cutoff required')
        expected = {r.record_id: r for r in lineage_heads(self.provenance) if r.record_status != 'retracted'}
        if len({r.record_id for r in self.records}) != len(self.records) or {r.record_id for r in self.records} != set(expected):
            raise ValueError('values must exactly match active visible heads')
        if any(provenance_v21(r) != expected[r.record_id] for r in self.records):
            raise ValueError('projection provenance mismatch')
        no_postdeath_outcomes(self.records)
        return self


class ObservedHistoryV21(ObservedHistoryV2):
    schema_version: Literal['2.1.0']
    records: list[ObservedRecordV21]

    def project(self, cutoff):
        return LearnerHistoryV21(schema_version='2.1.0', synthetic=True, kind='learner_history', patient_id=self.patient_id,
            cutoff=cutoff, records=self.as_known_at(cutoff), provenance=[provenance_v21(r) for r in visible_records(self.records, cutoff)])
