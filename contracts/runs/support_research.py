"""Restricted offline support artifacts; no archive admission or live authority.

Actual receipt clocks describe execution now. Simulated clocks describe the
historical synthetic trajectory. These are deliberately separate domains.
"""
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Literal

from pydantic import AwareDatetime, Field, model_validator
from contracts.domain.common import Identifier, Name, Sha256, StrictModel, VersionRef
from contracts.domain.evidence_v2 import exact_ref, resolve
from contracts.domain.protocol import LAW_REF, SUPPORT_REF
from contracts.domain.protocol_request import S1_ESTIMAND
from .common import Artifact, Commit, RestrictedRuntime, Token, canonical, sha256, unique
from .coverage_v2 import StageLedgerV2


class SupportRuntime(RestrictedRuntime):
    seed_derivation: Literal['poc-support-research-map-v1']


class SupportCompletion(StrictModel):
    version: Literal['poc-support-stage-completion-v1']
    id: Token
    run_id: Token
    partition_id: Token
    patient_id: Identifier
    source_commit: Commit
    runtime: SupportRuntime
    frozen_plan_sha256: Sha256
    status: Literal['complete', 'partial', 'failed']
    reason: Name | None
    stage_ledgers: list[VersionRef]
    output_artifacts: list[Artifact]
    output_counts: dict[Identifier, Annotated[int, Field(ge=0)]]
    simulated_completed_through: AwareDatetime
    simulated_available_at: AwareDatetime
    execution_started_at: AwareDatetime
    execution_ended_at: AwareDatetime
    published_at: AwareDatetime

    @model_validator(mode='after')
    def clocks_and_outputs(self):
        if not self.execution_started_at <= self.execution_ended_at <= self.published_at:
            raise ValueError('actual_execution_publication_chronology')
        if self.simulated_completed_through > self.simulated_available_at:
            raise ValueError('simulated_completion_availability_chronology')
        if (self.status == 'complete') != (self.reason is None):
            raise ValueError('incomplete_receipt_requires_reason')
        unique([r.id for r in self.stage_ledgers], 'receipt ledger')
        unique([r.id for r in self.output_artifacts], 'preclosure output')
        if not self.stage_ledgers or not self.output_artifacts or any(a.role != 'observed' for a in self.output_artifacts):
            raise ValueError('independent_preclosure_outputs_and_ledgers_required')
        return self


class Trajectory(StrictModel):
    member_id: Token
    paired_member_id: Token
    mode: Literal['S0', 'S1']
    partition_id: Token
    history: Artifact
    projections: dict[Literal['14', '42', '84'], Artifact]
    stage_ledgers: Artifact
    completions: Artifact


class SupportResearchIndex(StrictModel):
    version: Literal['poc-support-research-v1']
    synthetic: Literal[True]
    execution: Literal['historical-research-only']
    run_id: Token
    cohort_id: Token
    members: Annotated[list[Token], Field(min_length=12, max_length=12)]
    origin: AwareDatetime
    horizon: Literal[84]
    cuts: tuple[Literal[14], Literal[42], Literal[84]]
    law: VersionRef
    protocol: VersionRef
    estimand: VersionRef
    source_commit: Commit
    generator_sources: dict[str, Sha256]
    runtime: SupportRuntime
    frozen_plan_sha256: Sha256
    private_recipe_sha256: Sha256
    shared_pair_sha256: Sha256
    trajectories: Annotated[list[Trajectory], Field(min_length=24, max_length=24)]

    @model_validator(mode='after')
    def bound_panel(self):
        unique(self.members, 'support member')
        if self.origin!=datetime(2026,1,1,12,tzinfo=timezone.utc):
            raise ValueError('fixed_restricted_support_origin_required')
        if set(self.generator_sources)!={'restricted.py','restricted_v2.py','research_support.py'}:
            raise ValueError('consumed_generator_source_digests_required')
        if (self.law.model_dump() != LAW_REF or self.protocol.model_dump() != SUPPORT_REF
                or self.estimand.model_dump() != S1_ESTIMAND):
            raise ValueError('exact_support_scientific_identities_required')
        if {(r.member_id, r.mode) for r in self.trajectories} != {(p, s) for p in self.members for s in ('S0', 'S1')}:
            raise ValueError('one_matched_S0_S1_trajectory_per_member_required')
        unique([r.partition_id for r in self.trajectories], 'support partition')
        unique([r.paired_member_id for r in self.trajectories if r.mode=='S0'], 'paired support member')
        for patient in self.members:
            pair=[r.paired_member_id for r in self.trajectories if r.member_id == patient]
            if pair[0] != pair[1]:
                raise ValueError('paired_identity_mismatch')
        return self


def version_ref(value):
    data=value.model_dump(mode='json') if hasattr(value, 'model_dump') else value
    return VersionRef(id=data['id'], version='1.0.0', sha256=sha256(canonical(data)))


def read_artifact(root, artifact):
    import stat
    root=Path(root).absolute();path=root/artifact.path
    # Windows junctions/reparse points are links too. Check the configured
    # root and its ancestry before resolving; resolve() would hide the link.
    try:
        if any(p.is_symlink() or getattr(p.lstat(), 'st_file_attributes', 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT
               for p in (path, *path.parents)):
            raise ValueError('symlink_support_artifact_denied')
        root=root.resolve(strict=True)
        if not path.resolve().is_relative_to(root):
            raise ValueError('support_artifact_escape')
        if not path.is_file() or path.stat().st_nlink!=1:raise ValueError('ordinary_unlinked_support_artifact_required')
        raw=path.read_bytes()
    except OSError as error:raise ValueError('support_artifact_unreadable') from error
    if len(raw) != artifact.bytes or sha256(raw) != artifact.sha256:
        raise ValueError('support_artifact_hash_or_size_mismatch')
    return raw


class SupplementalSupportArtifact(StrictModel):
    partition_id: Token | None
    artifact: Artifact


class SupportArchiveAuthority(StrictModel):
    """Independent host configuration, never an uploaded admission claim.

    The full descriptor pins source/runtime, pairs and every original artifact.
    Qualification references identify the independently reviewed invocation.
    Structural fixtures carry their own explicit scope and grant no authority.
    """
    kind: Literal['restricted_support_archive']
    manifest_sha256: Sha256
    descriptor: SupportResearchIndex
    producer_qualification: VersionRef
    outcome_qualification: VersionRef
    qualification_scope: Literal['accepted_saved_producer', 'structural_fixture']
    supplemental_public_artifacts: list[SupplementalSupportArtifact]

    @model_validator(mode='after')
    def supplemental_identity(self):
        unique([r.artifact.path for r in self.supplemental_public_artifacts],'supplemental public path')
        unique([(r.partition_id,r.artifact.id) for r in self.supplemental_public_artifacts],'supplemental public scoped ID')
        partitions={r.partition_id for r in self.descriptor.trajectories}
        if any(r.partition_id is not None and r.partition_id not in partitions for r in self.supplemental_public_artifacts):
            raise ValueError('supplemental_support_partition_not_qualified')
        if any(r.partition_id is not None and not r.artifact.path.startswith(r.partition_id+'/') for r in self.supplemental_public_artifacts):
            raise ValueError('supplemental_support_path_partition_mismatch')
        return self

    @property
    def admission_sha256(self):
        return sha256(canonical(self.model_dump(mode='json')))


class StageVerifier:
    """Bound installed verifier, never an uploaded callback or authority claim.

    The caller must separately qualify source/runtime/invocation before trusting
    the resulting index. This verifier proves closure within that invocation.
    """
    def __init__(self, history, ledgers, completions, root, *, run_id, partition_id,
                 source_commit, runtime, frozen_plan_sha256, artifact_reader=None):
        self.history=history
        self.ledgers={r.id:r for r in ledgers}
        self.completions={r.id:r for r in completions}
        if len(self.ledgers)!=len(ledgers) or len(self.completions)!=len(completions):
            raise ValueError('duplicate_stage_proof_identity')
        self.root=root
        self.artifact_reader=artifact_reader or (lambda artifact: read_artifact(root,artifact))
        self.identity=(run_id,partition_id,history.patient_id,source_commit,runtime,frozen_plan_sha256)

    def __call__(self, closure, cutoff):
        if not hasattr(closure, 'stage'):
            closure=resolve(self.history,closure,{'support_stage_closure'},cutoff=cutoff)
        else:
            resolve(self.history,exact_ref(closure),{'support_stage_closure'},cutoff=cutoff)
        decision=resolve(self.history,closure.support_decision,{'support_decision'},cutoff=cutoff)
        run,partition,patient,source,runtime,plan=self.identity
        if (closure.run_id,closure.partition_id,closure.patient_id)!=(run,partition,patient):
            raise ValueError('foreign_stage_closure')
        if (closure.window_id,closure.decision_index)!=(decision.outcome_window.id,decision.decision_index):
            raise ValueError('stage_decision_window_mismatch')
        assignment=None
        if closure.assignment_ref:
            assignment=resolve(self.history,closure.assignment_ref,{'assignment'},cutoff=cutoff)
        if (assignment.record_id if assignment else None)!=decision.assignment_id:
            raise ValueError('stage_assignment_mismatch')
        ledger=self.ledgers.get(closure.stage_ledger.id)
        receipt=self.completions.get(closure.completion_receipt.id) if closure.completion_receipt else None
        if ledger is None or version_ref(ledger)!=closure.stage_ledger or receipt is None or version_ref(receipt)!=closure.completion_receipt:
            raise ValueError('missing_or_substituted_stage_proof')
        if (ledger.run_id,ledger.partition_id,ledger.patient_id,ledger.window_id,ledger.decision_index,ledger.stage,ledger.rule)!=(
                run,partition,patient,closure.window_id,closure.decision_index,closure.stage,closure.rule):
            raise ValueError('foreign_or_changed_stage_ledger')
        if (receipt.run_id,receipt.partition_id,receipt.patient_id,receipt.source_commit,receipt.runtime,receipt.frozen_plan_sha256)!=(
                run,partition,patient,source,runtime,plan):
            raise ValueError('foreign_or_changed_completion_receipt')
        if (closure.status!='complete' or receipt.status!='complete' or version_ref(ledger) not in receipt.stage_ledgers
                or receipt.simulated_completed_through!=closure.stage_completed_at
                or receipt.simulated_available_at!=closure.available_at
                or not decision.cutoff <= closure.stage_completed_at <= decision.outcome_window.ends_at
                or not closure.stage_completed_at < cutoff):
            raise ValueError('stage_not_completed_and_available')
        # Only independently hashed delivery arrays are allowed receipt outputs.
        import json
        output=[]
        for artifact in receipt.output_artifacts:
            rows=json.loads(self.artifact_reader(artifact))
            if not isinstance(rows,list) or any(r.get('kind')!='delivery' for r in rows):
                raise ValueError('receipt_output_not_independent_stage_events')
            output.extend(rows)
        if len({r['record_id'] for r in output})!=len(output) or receipt.output_counts!={'stage_events':len(output)}:
            raise ValueError('preclosure_output_count_mismatch')
        start,end=decision.outcome_window.starts_at,decision.outcome_window.ends_at
        active=self.history.as_known_at(cutoff)
        # Inspect every support stage event in the window, not only claimed refs.
        events=[r for r in active if r.kind=='delivery' and r.stage==closure.stage
                and r.option in ('support_prompt','no_prompt') and start <= r.event_at < end]
        if any(r.assignment_id!=decision.assignment_id for r in events):
            raise ValueError('foreign_stage_assignment_in_window')
        if any(r.event_at>closure.stage_completed_at or r.available_at>closure.available_at for r in events):
            raise ValueError('stage_completion_precedes_stage_events')
        claimed=[resolve(self.history,r,{'delivery'},cutoff=cutoff) for r in ledger.event_refs]
        if any(r.stage!=closure.stage or r.assignment_id!=decision.assignment_id or not start <= r.event_at < end for r in claimed):
            raise ValueError('stage_event_outside_bound_window')
        expected=sorted([exact_ref(r).model_dump() for r in events],key=lambda r:r['record_id'])
        if (sorted([r.model_dump() for r in ledger.event_refs],key=lambda r:r['record_id'])!=expected
                or closure.stage_event_refs!=ledger.event_refs or closure.row_count!=len(events)):
            raise ValueError('stage_event_set_not_exhaustive')
        by_id={r['record_id']:r for r in output}
        if any(by_id.get(r.record_id)!=r.model_dump(mode='json') for r in events):
            raise ValueError('stage_event_absent_or_changed_in_preclosure_output')
        # Output events also cannot conceal another member, window or stage.
        history_by_id={r.record_id:r for r in self.history.records}
        for row in output:
            parsed=history_by_id.get(row['record_id'])
            if (parsed is None or row!=parsed.model_dump(mode='json') or parsed.patient_id!=patient
                    or parsed.assignment_id!=decision.assignment_id or parsed.stage not in ('offered','delivered')
                    or not start <= parsed.event_at < end):
                raise ValueError('foreign_or_out_of_window_preclosure_output')
        return events
