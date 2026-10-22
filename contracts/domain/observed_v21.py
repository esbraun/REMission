"""Consumer-safe REPORT-STATUS/SIM-BURDEN 2.1 wire contracts.

These are public representation and exact-evidence checks, not a stochastic
producer, execution qualifier, or LIVE clearance authority. Legacy models and
their exports remain separate. SIM-REVIEW's intrinsic mapping is not defined
here while its bounded proposal is under independent critique.
"""
from datetime import date, datetime, time, timedelta, timezone
from typing import Annotated, Literal, Union
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import AwareDatetime, Discriminator, Field, Tag, TypeAdapter, model_validator

from .boundaries import lineage_heads, validate_lineage, visible_records
from .common import Identifier, Name, Record, Sha256, StrictModel, VersionRef, Versioned
from .evidence_v2 import exact_ref, payload_hash
from .observed_v2 import (DailyReportV2, ExactRef, SupportDecision, SupportOutcomeLink,
                         SupportStageClosureV2, _V1, record_tag)

LAW_VERSION = '1.0.0-r1'
INSTRUMENT_ID = 'synthetic-support-burden-item'


def _version(ref, identity, version):
    if (ref.id, ref.version) != (identity, version):
        raise ValueError('unsupported_scientific_reference_identity_version')


def _unique_refs(refs):
    if len({r.record_id for r in refs}) != len(refs):
        raise ValueError('duplicate_exact_reference')


class VersionedV21(Versioned):
    schema_version: Literal['2.1.0']


class RecordV21(Record):
    schema_version: Literal['2.1.0']
    run_id: Identifier
    partition_id: Identifier


class RatingWindowV21(StrictModel):
    starts_at: AwareDatetime
    ends_at: AwareDatetime
    timezone: Name
    local_date: date

    @model_validator(mode='after')
    def exact_local_window(self):
        try:
            zone = ZoneInfo(self.timezone)
        except ZoneInfoNotFoundError as error:
            raise ValueError('unknown_reporting_timezone') from error
        end = datetime.combine(self.local_date, time(7), zone).astimezone(timezone.utc)
        start = datetime.combine(self.local_date - timedelta(days=1), time(7), zone).astimezone(timezone.utc)
        if self.starts_at != start or self.ends_at != end:
            raise ValueError('rating_window_requires_exact_half_open_local_07_endpoints')
        return self


class ReportObservationDecisionV21(RecordV21):
    kind: Literal['report_observation_decision']
    assessment_local_date: date
    report_event_at: AwareDatetime
    decision_at: AwareDatetime
    temporal: VersionRef
    law: VersionRef
    reporting_process_ref: VersionRef
    indicator: Annotated[int, Field(ge=0, le=1)]
    pain_ref: ExactRef
    previous_quality_ref: ExactRef | None
    absent_history: bool
    pre_report_projection_sha256: Sha256
    execution_receipt_ref: VersionRef
    source_correction_receipt_ref: VersionRef | None

    @model_validator(mode='after')
    def public_completion(self):
        if (self.source.id, self.source.version, self.source.adapter) != ('dgp-report-status', LAW_VERSION, 'simulation'):
            raise ValueError('unregistered_report_status_source')
        _version(self.temporal, 'TIME-01', '2.1.0')
        _version(self.law, 'REPORT-STATUS-01', LAW_VERSION)
        if self.report_event_at != self.event_at or self.decision_at != self.event_at + timedelta(minutes=61):
            raise ValueError('report_completion_requires_original_07_to_0801_clock')
        if self.absent_history != (self.previous_quality_ref is None):
            raise ValueError('absent_history_requires_no_previous_quality_reference')
        if self.revision == 1:
            if self.recorded_at != self.decision_at or self.available_at != self.decision_at or self.source_correction_receipt_ref is not None:
                raise ValueError('original_completion_is_immediately_public_at_0801')
        elif self.recorded_at <= self.decision_at or self.source_correction_receipt_ref is None:
            raise ValueError('completion_correction_requires_later_publication_and_exact_source_error_receipt')
        return self


class DailyReportV21(DailyReportV2):
    schema_version: Literal['2.1.0']
    run_id: Identifier
    partition_id: Identifier
    report_decision_ref: ExactRef
    burden: Literal[None]

    @model_validator(mode='after')
    def observed_response(self):
        if (self.source.id, self.source.version, self.source.adapter) != ('dgp-patient-report', '1.3.0', 'patient_report'):
            raise ValueError('unregistered_v21_patient_report_source')
        if self.record_status != 'retracted' and self.missingness != 'observed':
            raise ValueError('only_actual_completed_responses_are_daily_report_records')
        if self.record_status == 'retracted' and any(v is not None for v in (self.sleep_quality, self.function, self.diary_sleep_minutes)):
            raise ValueError('retracted_response_requires_null_numeric_values')
        if self.revision == 1 and self.recorded_at != self.event_at + timedelta(minutes=61):
            raise ValueError('original_daily_report_is_recorded_at_0801')
        return self


class SubjectiveBurdenRatingV21(RecordV21):
    kind: Literal['subjective_burden_rating']
    instrument: VersionRef
    window: RatingWindowV21
    score: Annotated[int, Field(ge=0, le=4)] | None
    report_decision_ref: ExactRef

    @model_validator(mode='after')
    def actual_rating(self):
        if (self.source.id, self.source.version, self.source.adapter) != ('dgp-patient-report', '1.3.0', 'patient_report'):
            raise ValueError('unregistered_v21_patient_report_source')
        _version(self.instrument, INSTRUMENT_ID, LAW_VERSION)
        if self.window.ends_at != self.event_at:
            raise ValueError('rating_event_is_its_window_assessment')
        if (self.score is None) != (self.record_status == 'retracted'):
            raise ValueError('null_rating_is_only_a_retraction_never_missing_or_zero')
        if self.revision == 1 and self.recorded_at != self.event_at + timedelta(minutes=61):
            raise ValueError('original_rating_is_recorded_at_0801')
        return self


class ReportStatusRecordV21(RecordV21):
    @model_validator(mode='after')
    def metadata_source(self):
        if (self.source.id, self.source.version, self.source.adapter) != ('dgp-report-status', LAW_VERSION, 'simulation'):
            raise ValueError('unregistered_report_status_source')
        return self


class ReportUploadReceiptV21(ReportStatusRecordV21):
    kind: Literal['report_upload_receipt']
    report_decision_ref: ExactRef
    daily_report_ref: ExactRef
    rating_ref: ExactRef
    upload_delay_days: Annotated[int, Field(strict=True, ge=0, le=3, json_schema_extra={'enum': [0, 1, 3]})]
    payload_available_at: AwareDatetime
    completion_receipt_ref: VersionRef
    publication_sequence: Annotated[int, Field(ge=1)]

    @model_validator(mode='after')
    def actual_publication(self):
        if type(self.upload_delay_days) is not int or self.upload_delay_days not in (0, 1, 3):
            raise ValueError('upload_delay_is_a_strict_integer')
        if not self.event_at <= self.payload_available_at <= self.recorded_at:
            raise ValueError('upload_receipt_cannot_precede_actual_payload_availability')
        _unique_refs([self.report_decision_ref, self.daily_report_ref, self.rating_ref])
        return self


class BurdenAssessmentStateV21(ReportStatusRecordV21):
    kind: Literal['burden_assessment_state']
    instrument: VersionRef
    window: RatingWindowV21
    status: Literal['pending', 'missing', 'observed', 'undefined']
    reason: Name
    report_decision_ref: ExactRef | None
    terminal_ref: ExactRef | None
    rating_ref: ExactRef | None
    receipt_ref: ExactRef | None
    evaluated_as_of: AwareDatetime
    source_refs: list[ExactRef]
    closure_refs: list[ExactRef]
    definition_refs: list[VersionRef]

    @model_validator(mode='after')
    def state_shape(self):
        _version(self.instrument, INSTRUMENT_ID, LAW_VERSION)
        if not self.event_at == self.window.ends_at <= self.evaluated_as_of <= self.recorded_at:
            raise ValueError('assessment_event_evaluation_publication_chronology')
        refs = [*self.source_refs, *self.closure_refs]
        _unique_refs(refs)
        if self.status == 'undefined':
            if self.report_decision_ref is not None or self.rating_ref is not None or self.receipt_ref is not None or not (self.terminal_ref or self.definition_refs):
                raise ValueError('undefined_requires_terminal_or_horizon_evidence_without_response')
        else:
            if self.report_decision_ref is None or self.terminal_ref is not None:
                raise ValueError('reporting_state_requires_exact_completion_parent')
            if self.evaluated_as_of < self.event_at + timedelta(minutes=61):
                raise ValueError('reporting_state_cannot_precede_0801')
            if (self.status == 'observed') != (self.rating_ref is not None and self.receipt_ref is not None):
                raise ValueError('observed_requires_rating_and_upload_receipt')
            if self.status != 'observed' and (self.rating_ref or self.receipt_ref):
                raise ValueError('pending_missing_are_not_observed_responses')
        return self


class SupportBurdenOutcomeLinkV21(ReportStatusRecordV21):
    kind: Literal['support_burden_outcome_link']
    support_decision: ExactRef
    assignment_ref: ExactRef | None
    instrument: VersionRef
    target_window: RatingWindowV21
    assessment_at: AwareDatetime
    state_ref: ExactRef | None
    terminal_ref: ExactRef | None
    reason: Literal['terminal_before_assessment', 'outside_generated_horizon'] | None
    evaluated_as_of: AwareDatetime
    source_refs: list[ExactRef]
    closure_refs: list[ExactRef]
    definition_refs: list[VersionRef]

    @model_validator(mode='after')
    def reserved_link(self):
        _version(self.instrument, INSTRUMENT_ID, LAW_VERSION)
        if not self.event_at == self.assessment_at == self.target_window.ends_at <= self.evaluated_as_of <= self.recorded_at:
            raise ValueError('no_futuredated_preassessment_burden_link')
        if self.state_ref is None:
            if self.reason is None or (self.reason == 'terminal_before_assessment' and self.terminal_ref is None) or (self.reason == 'outside_generated_horizon' and not self.definition_refs):
                raise ValueError('unassessed_link_requires_exact_terminal_or_horizon_reason')
        elif self.reason is not None or self.terminal_ref is not None:
            raise ValueError('assessed_link_uses_exact_state_without_alternative_reason')
        _unique_refs([*self.source_refs, *self.closure_refs])
        return self


# Unchanged 1.0 clinical products and 2.0 support products remain explicit tags.
# A 2.0 or 1.0 DailyReport is not a 2.1 response and cannot satisfy its graph.
_V21 = [DailyReportV21, ReportObservationDecisionV21, SubjectiveBurdenRatingV21,
        ReportUploadReceiptV21, BurdenAssessmentStateV21, SupportBurdenOutcomeLinkV21]
_UNCHANGED_V2 = [SupportDecision, SupportOutcomeLink, SupportStageClosureV2]
_MODELS = [*_V1, *_UNCHANGED_V2, *_V21]
ObservedRecordV21 = Annotated[Union[tuple(Annotated[model, Tag(f'{model.model_fields["schema_version"].annotation.__args__[0]}:{model.model_fields["kind"].annotation.__args__[0]}')] for model in _MODELS)], Discriminator(record_tag)]
RECORD_ADAPTER_V21 = TypeAdapter(ObservedRecordV21)


class RecordProvenanceV21(Record):
    schema_version: Literal['1.0.0', '2.0.0', '2.1.0']
    kind: Identifier


def provenance_v21(record):
    return RecordProvenanceV21.model_validate(record.model_dump(include=set(Record.model_fields) | {'kind'}))


def validate_lineage_v21(records):
    validate_lineage(records)
    by_id = {r.record_id: r for r in records}
    for r in records:
        for dependency in (r.supersedes, r.duplicate_of):
            if dependency and by_id[dependency].schema_version != r.schema_version:
                raise ValueError('cross_version_correction_duplicate_forbidden')
        if r.supersedes and hasattr(r, 'report_decision_ref'):
            old = by_id[r.supersedes]
            if r.report_decision_ref != old.report_decision_ref:
                raise ValueError('response_correction_must_retain_original_completion_parent')
            if r.kind == 'subjective_burden_rating' and (r.instrument != old.instrument or r.window != old.window):
                raise ValueError('rating_correction_changes_instrument_window')


def no_postdeath_responses(records):
    deaths = [r.event_at for r in records if r.kind == 'intercurrent_event' and r.event_type == 'death']
    if deaths:
        death = min(deaths)
        if any((r.kind in ('isi', 'daily_report', 'subjective_burden_rating') and r.event_at >= death)
               or (r.kind in ('report_observation_decision', 'daily_report', 'subjective_burden_rating') and
                   (r.decision_at if r.kind == 'report_observation_decision' else r.event_at + timedelta(minutes=61)) >= death)
               for r in records):
            raise ValueError('no_new_response_decision_after_death_prior_recorded_delayed_upload_survives')


class LearnerHistoryV21(VersionedV21):
    kind: Literal['learner_history']
    patient_id: Identifier
    cutoff: AwareDatetime
    records: list[ObservedRecordV21]
    provenance: list[RecordProvenanceV21]

    @model_validator(mode='after')
    def exact_projection(self):
        if any(r.patient_id != self.patient_id for r in [*self.records, *self.provenance]):
            raise ValueError('projection_patient_mismatch')
        validate_lineage_v21(self.provenance)
        if len(visible_records(self.provenance, self.cutoff)) != len(self.provenance):
            raise ValueError('strict_before_cutoff_required')
        expected = {r.record_id: r for r in lineage_heads(self.provenance) if r.record_status != 'retracted'}
        if len({r.record_id for r in self.records}) != len(self.records) or {r.record_id for r in self.records} != set(expected):
            raise ValueError('values_must_exactly_match_active_visible_heads')
        if any(provenance_v21(r) != expected[r.record_id] for r in self.records):
            raise ValueError('projection_provenance_mismatch')
        no_postdeath_responses(self.records)
        return self


class ObservedHistoryV21(VersionedV21):
    kind: Literal['observed_history']
    patient_id: Identifier
    records: list[ObservedRecordV21]

    @model_validator(mode='after')
    def complete_lineage(self):
        if any(r.patient_id != self.patient_id for r in self.records):
            raise ValueError('history_patient_mismatch')
        validate_lineage_v21(self.records)
        active = [r for r in lineage_heads(self.records) if r.record_status != 'retracted']
        no_postdeath_responses(active)
        for kinds in [('daily_report',), ('subjective_burden_rating',), ('report_observation_decision',), ('burden_assessment_state',)]:
            selected = [r for r in active if r.kind in kinds]
            if len({r.event_at for r in selected}) != len(selected):
                raise ValueError('one_logical_response_or_assessment_lineage_per_morning')
        return self

    def as_known_at(self, cutoff):
        return [r for r in lineage_heads(visible_records(self.records, cutoff)) if r.record_status != 'retracted']

    def project(self, cutoff):
        return LearnerHistoryV21(schema_version='2.1.0', synthetic=True, kind='learner_history', patient_id=self.patient_id,
            cutoff=cutoff, records=self.as_known_at(cutoff), provenance=[provenance_v21(r) for r in visible_records(self.records, cutoff)])


class ReportingInputV21(VersionedV21):
    kind: Literal['reporting_input']
    temporal_version: Literal['2.1.0']
    patient_id: Identifier
    report_event_at: AwareDatetime
    decision_at: AwareDatetime
    pain_ref: ExactRef
    pre_report_history: LearnerHistoryV21
    pre_report_projection_sha256: Sha256
    previous_quality_ref: ExactRef | None
    absent_history: bool

    @model_validator(mode='after')
    def observed_only_input(self):
        if self.decision_at != self.report_event_at + timedelta(minutes=61):
            raise ValueError('report_input_requires_07_to_0801_clock')
        if self.pre_report_history.patient_id != self.patient_id or self.pre_report_history.cutoff != self.decision_at:
            raise ValueError('report_input_patient_projection_cutoff_mismatch')
        if payload_hash(self.pre_report_history) != self.pre_report_projection_sha256:
            raise ValueError('report_input_projection_hash_mismatch')
        pain = next((r for r in self.pre_report_history.records if exact_ref(r) == self.pain_ref), None)
        pain_at = self.report_event_at + timedelta(hours=1)
        if (pain is None or pain.kind != 'observation' or
            (pain.source.id, pain.source.version, pain.source.adapter) != ('dgp-clinical-pain', '1.3.0', 'synthetic_fhir_shaped') or
            (pain.event_at, pain.recorded_at, pain.available_at) != (pain_at, pain_at, pain_at) or
            (pain.measure.concept, pain.measure.unit) != ('pain', 'dimensionless')):
            raise ValueError('exact_independent_current_0800_pain_required')
        if any(r.kind in ('daily_report', 'subjective_burden_rating', 'report_observation_decision') and r.event_at >= self.report_event_at for r in self.pre_report_history.records):
            raise ValueError('report_input_excludes_current_future_report_channels')
        reports = [r for r in self.pre_report_history.records if r.kind == 'daily_report' and r.event_at < self.report_event_at and r.missingness == 'observed' and r.sleep_quality is not None]
        previous = max(reports, key=lambda r: r.event_at, default=None)
        if self.absent_history != (previous is None) or self.previous_quality_ref != (exact_ref(previous) if previous else None):
            raise ValueError('previous_quality_must_be_latest_available_prior_observed_report')
        if any(r.kind == 'intercurrent_event' and r.event_type == 'death' and r.event_at <= self.decision_at for r in self.pre_report_history.records):
            raise ValueError('known_death_forbids_new_reporting_decision')
        return self

    def mar_predictors(self):
        pain = next(r for r in self.pre_report_history.records if r.record_id == self.pain_ref.record_id)
        previous = next((r for r in self.pre_report_history.records if self.previous_quality_ref and r.record_id == self.previous_quality_ref.record_id), None)
        return dict(current_observed_pain=pain.measure.value, previous_observed_quality=previous.sleep_quality if previous else 7.0, absent_history=self.absent_history)


def reporting_input_v21(history, *, report_event_at, pain_record_id):
    """Pure composition from actual public records; no draws or hidden values."""
    history = ObservedHistoryV21.model_validate_json(history.model_dump_json())
    if report_event_at.tzinfo is None or report_event_at.timetz().replace(tzinfo=None) != time(7):
        raise ValueError('aware_local_0700_report_event_required')
    decision_at = report_event_at + timedelta(minutes=61)
    projection = history.project(decision_at)
    pain = next((r for r in projection.records if r.record_id == pain_record_id), None)
    if pain is None:
        raise ValueError('missing_current_pain')
    reports = [r for r in projection.records if r.kind == 'daily_report' and r.event_at < report_event_at and r.missingness == 'observed' and r.sleep_quality is not None]
    previous = max(reports, key=lambda r: r.event_at, default=None)
    return ReportingInputV21(schema_version='2.1.0', synthetic=True, kind='reporting_input', temporal_version='2.1.0', patient_id=history.patient_id,
        report_event_at=report_event_at, decision_at=decision_at, pain_ref=exact_ref(pain), pre_report_history=projection,
        pre_report_projection_sha256=payload_hash(projection), previous_quality_ref=exact_ref(previous) if previous else None, absent_history=previous is None)
