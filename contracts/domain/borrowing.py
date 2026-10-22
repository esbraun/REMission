"""Public PA3 summary-only source contract. Replay and participant keys are absent."""
import math
from typing import Annotated, Literal
from pydantic import AwareDatetime, Field, model_validator
from .common import Identifier, Sha256, StrictModel
from .analysis import sha


DESIGN = dict(endpoint_day=42, recall_first_night=29, recall_last_night=42,
    instrument='ISI-7-synthetic-14d-v1', unit='ISI_points', sign='escalate-minus-continue',
    assignment='random-permutation-60-per-arm-retained-at-14-28', support='fixed-no-prompt',
    baseline='untreated-nights-minus13-through0', population='shared-normal-independent-hierarchy-v1',
    source_target_assumption='common-population-adherence-process-measurement-law',
    protocol='poc-visit-retain-v1', producer='poc-pa3-study-producer-v1')


class StudySummary(StrictModel):
    schema: Literal['poc-study-summary-v1/1.0.0']
    study_id: Identifier
    dataset_id: Identifier
    synthetic: Literal[True]
    provenance: Literal['fictional-randomized-study']
    n_continue: Literal[60]
    n_escalate: Literal[60]
    d: float
    se: Annotated[float, Field(gt=0)]
    available_at: AwareDatetime
    design: dict[str, str | int]
    checksum: Sha256

    @model_validator(mode='after')
    def admitted(self):
        if not math.isfinite(self.d) or not math.isfinite(self.se) or self.design != DESIGN:
            raise ValueError('nonfinite or unsupported source summary/design')
        if self.checksum != sha(self.model_dump(mode='json', exclude={'checksum'})):
            raise ValueError('summary checksum mismatch')
        return self


class SourceBundle(StrictModel):
    schema: Literal['poc-source-bundle-v1/1.0.0']
    bundle_id: Identifier
    studies: Annotated[list[StudySummary], Field(min_length=2, max_length=2)]
    source_set_sha256: Sha256

    @model_validator(mode='after')
    def unique(self):
        if len({s.study_id for s in self.studies}) != 2 or len({s.dataset_id for s in self.studies}) != 2:
            raise ValueError('duplicate study or underlying dataset')
        if self.source_set_sha256 != sha([s.model_dump(mode='json') for s in self.studies]):
            raise ValueError('source set checksum mismatch')
        return self

    def at_cutoff(self, cutoff):
        if any(s.available_at >= cutoff for s in self.studies):
            raise ValueError('source unavailable at requested cutoff')
        return self
