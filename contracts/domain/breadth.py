"""Explicit four-family observed profile; old history readers are unchanged.

Full available lineage is distinct from active likelihood observations and the
compact support working vector. No latent state, generation key or truth lives
in these learner/export types. SOURCE preparation is not model qualification.
"""
from datetime import datetime, timedelta, timezone
import hashlib
import json
from typing import Annotated, Literal

from pydantic import AwareDatetime, Field, field_validator, model_validator
from .common import Identifier, Record, StrictModel, VersionRef
from .boundaries import validate_lineage, visible_records, lineage_heads

LAW_VERSION='poc-breadth-longitudinal-v3'
HISTORY_VERSION='poc-breadth-history-v3'
FEATURE_VERSION='poc-breadth-features-v1'


def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def digest(value):return hashlib.sha256(canonical(value)).hexdigest()
def reference(name,version,value):return dict(id=name,version=version,sha256=digest(value))


# The exact numerical/clock descriptor is finalized with the accepted narrow
# design clarifications before the producer path is frozen for source review.
LAW_REF=reference(LAW_VERSION,'3.0.0','PR75 four-family fictional law; exact implementation descriptor bound by producer')
HISTORY_REF=reference(HISTORY_VERSION,'3.0.0','complete available observed lineage; active heads explicit; no implicit old-reader conversion')
FEATURE_REF=reference(FEATURE_VERSION,'1.0.0','support eight-column vector, S and prior-six interactions; source IDs and observation ages retained')
SOURCE_IDS=dict(demographic='poc-breadth-demographic-v3',clinical='poc-breadth-emr-v3',steroid_schedule='poc-breadth-emr-v3',
    steroid_exposure='poc-breadth-emr-v3',device_sleep='poc-breadth-device-v3',daily_report='poc-breadth-report-v3',
    isi='poc-breadth-report-v3',assignment='poc-breadth-treatment-v3',delivery='poc-breadth-treatment-v3')
ADAPTERS=dict(demographic='simulation',clinical='synthetic_fhir_shaped',steroid_schedule='synthetic_fhir_shaped',
    steroid_exposure='synthetic_fhir_shaped',device_sleep='synthetic_oura_like',daily_report='patient_report',
    isi='patient_report',assignment='synthetic_trial',delivery='synthetic_trial')
Kind=Literal['demographic','clinical','steroid_schedule','steroid_exposure','device_sleep','daily_report','isi','assignment','delivery']


class Header(Record):
    schema_version: Literal['3.0.0']
    kind: Kind

    @model_validator(mode='after')
    def source_profile(self):
        if (self.source.id,self.source.version,self.source.adapter)!=(SOURCE_IDS[self.kind],'3.0.0',ADAPTERS[self.kind]):
            raise ValueError('exact versioned breadth source required')
        if any(t.utcoffset()!=timedelta(0) for t in (self.event_at,self.recorded_at,self.available_at)):
            raise ValueError('breadth source clocks must be UTC')
        return self


class Demographic(Header):
    kind: Literal['demographic']
    age_years: Annotated[float,Field(ge=30,le=75)]
    age_unit: Literal['years']
    synthetic_sex_code: Literal[0,1]
    sex_concept: Literal['fictional-two-code-scenario-variable-not-general-sex-gender-ontology']

    @field_validator('synthetic_sex_code',mode='before')
    @classmethod
    def explicit_code(cls,value):
        if type(value) is not int:raise ValueError('sex scenario code must be an integer, not Boolean')
        return value


class Clinical(Header):
    kind: Literal['clinical']
    value: Annotated[float,Field(ge=0,le=10)] | None
    unit: Literal['synthetic_clinical_score_0_10']
    missingness: Literal['observed','missing']

    @model_validator(mode='after')
    def observed_value(self):
        if (self.value is not None)!=(self.missingness=='observed') or self.value is not None and abs(self.value*10-round(self.value*10))>1e-8:
            raise ValueError('clinical null/indicator/.1 resolution mismatch')
        return self


class SteroidSchedule(Header):
    kind: Literal['steroid_schedule']
    period_days: Literal[21]
    active_residues: tuple[Literal[0],Literal[1],Literal[2]]
    unit: Literal['binary_contextual_exposure_not_dose']


class SteroidExposure(Header):
    kind: Literal['steroid_exposure']
    active: bool
    schedule_id: Identifier
    unit: Literal['binary_contextual_exposure_not_dose']


class DeviceSleep(Header):
    kind: Literal['device_sleep']
    episode_start: AwareDatetime
    episode_end: AwareDatetime
    time_in_bed: Literal[480.0]
    sleep_minutes: Annotated[float,Field(ge=0,le=480)] | None
    estimated_wake_minutes: Annotated[float,Field(ge=0,le=480)] | None
    status: Literal['observed','nonwear','quality_rejected']
    unit: Literal['minutes']

    @model_validator(mode='after')
    def one_device_measurement(self):
        observed=self.status=='observed'
        if observed!=(self.sleep_minutes is not None) or observed!=(self.estimated_wake_minutes is not None):
            raise ValueError('device missing/rejected values must be null')
        if (self.episode_end-self.episode_start!=timedelta(hours=8) or self.episode_end!=self.event_at
                or self.episode_start.utcoffset()!=timedelta(0) or self.episode_end.utcoffset()!=timedelta(0)):
            raise ValueError('device episode must end at observation with eight-hour bed interval')
        if observed and (abs(self.sleep_minutes*10-round(self.sleep_minutes*10))>1e-8 or abs(self.estimated_wake_minutes-(480-self.sleep_minutes))>1e-8):
            raise ValueError('wake is the exact derived complement, not another measurement')
        return self


class Quality(Header):
    kind: Literal['daily_report']
    value: Annotated[float,Field(ge=0,le=10)] | None
    unit: Literal['quality_points_0_10']
    missingness: Literal['observed','missing']

    @model_validator(mode='after')
    def observed_value(self):
        if (self.value is not None)!=(self.missingness=='observed') or self.value is not None and abs(self.value*1000-round(self.value*1000))>1e-8:
            raise ValueError('report null/indicator/.001 resolution mismatch')
        return self


class ISI(Header):
    kind: Literal['isi']
    total: Annotated[int,Field(ge=0,le=28)]
    unit: Literal['ISI_points']
    instrument: Literal['synthetic-rounded-clipped-ISI-total-v3']
    recall_days: Literal[14]
    recall_start: AwareDatetime
    recall_end: AwareDatetime

    @model_validator(mode='after')
    def recall(self):
        if (self.recall_end-self.recall_start!=timedelta(days=14) or self.recall_end>self.event_at
                or self.recall_start.utcoffset()!=timedelta(0) or self.recall_end.utcoffset()!=timedelta(0)):
            raise ValueError('one total-score observation with complete14-night recall')
        return self


Component=Literal['behavioral','medication','support']
Option=Literal['behavioral_continue','behavioral_escalate','MED_A','MED_B','support_prompt','no_prompt']


class Assignment(Header):
    kind: Literal['assignment']
    component: Component
    option: Option | None
    policy: VersionRef
    chosen_probability: Annotated[float,Field(gt=0,le=1)]
    support_available: tuple[bool,bool] | None
    support_probabilities: tuple[Annotated[float,Field(ge=0,le=1)],Annotated[float,Field(ge=0,le=1)]] | None
    unit: Literal['assigned_action']

    @model_validator(mode='after')
    def action_domain(self):
        allowed={'behavioral':('behavioral_continue','behavioral_escalate'),'medication':('MED_A','MED_B',None),'support':('no_prompt','support_prompt')}
        if self.option not in allowed[self.component]:raise ValueError('assignment option/component mismatch')
        if (self.component=='support')!=(self.support_available is not None):raise ValueError('support assignment requires actual availability mask')
        if (self.component=='support')!=(self.support_probabilities is not None):raise ValueError('actual full support distribution required')
        if self.component=='support':
            index=int(self.option=='support_prompt')
            if not self.support_available[index]:raise ValueError('unavailable support action selected')
            if (abs(sum(self.support_probabilities)-1)>1e-12 or self.chosen_probability!=self.support_probabilities[index]
                    or any(p!=0 for p,available in zip(self.support_probabilities,self.support_available) if not available)):
                raise ValueError('logged selected probability/full distribution/mask mismatch')
        return self


class Delivery(Header):
    kind: Literal['delivery']
    component: Component
    assignment_id: Identifier
    option: Option
    taken: bool
    unit: Literal['actual_delivery_taking']

    @model_validator(mode='after')
    def action_domain(self):
        allowed={'behavioral':('behavioral_continue','behavioral_escalate'),'medication':('MED_A','MED_B'),'support':('no_prompt','support_prompt')}
        if self.option not in allowed[self.component]:raise ValueError('delivery option/component mismatch')
        return self


ObservedEvent=Annotated[Demographic|Clinical|SteroidSchedule|SteroidExposure|DeviceSleep|Quality|ISI|Assignment|Delivery,Field(discriminator='kind')]


class BreadthHistory(StrictModel):
    version: Literal['poc-breadth-history-v3']
    synthetic: Literal[True]
    law: VersionRef
    patient_id: Identifier
    origin: AwareDatetime
    records: list[ObservedEvent]

    @model_validator(mode='after')
    def complete_lineage(self):
        if self.law.model_dump()!=LAW_REF or self.origin.utcoffset()!=timedelta(0):raise ValueError('exact breadth law and UTC origin required')
        if any(r.patient_id!=self.patient_id for r in self.records):raise ValueError('single patient history required')
        validate_lineage(self.records)
        originals={}
        for r in self.records:
            if r.kind in ('demographic','steroid_schedule') and (r.revision!=1 or r.event_at>=self.origin-timedelta(days=14)):
                raise ValueError('immutable baseline demographics/schedule must precede prehistory')
            if r.duplicate_of is None:
                key=(r.kind,r.event_at,getattr(r,'component',None))
                if key in originals and originals[key]!=r.lineage_id:raise ValueError('ambiguous same-event independent lineages')
                originals[key]=r.lineage_id
        by_id={r.record_id:r for r in self.records}
        for r in self.records:
            if r.kind=='steroid_exposure':
                schedule=by_id.get(r.schedule_id);day=(r.event_at.date()-self.origin.date()).days
                if (schedule is None or schedule.kind!='steroid_schedule' or schedule.available_at>r.event_at
                        or r.active!=(day%schedule.period_days in schedule.active_residues)):
                    raise ValueError('actual contextual exposure differs from original planned schedule')
            if r.kind=='delivery':
                assigned=by_id.get(r.assignment_id)
                if (assigned is None or assigned.kind!='assignment' or (assigned.component,assigned.option)!=(r.component,r.option)
                        or assigned.available_at>r.event_at):raise ValueError('delivery requires original matching prior assignment')
        return self

    def project(self,cutoff):
        # Select visibility FIRST, then lineage heads; never let a future
        # correction erase the historical value at an earlier cutoff.
        rows=visible_records(self.records,cutoff)
        return BreadthProjection(version=HISTORY_VERSION,synthetic=True,law=self.law,patient_id=self.patient_id,origin=self.origin,
            cutoff=cutoff,lineage=rows,active_record_ids=[r.record_id for r in lineage_heads(rows) if r.record_status!='retracted'])


class BreadthProjection(StrictModel):
    version: Literal['poc-breadth-history-v3']
    synthetic: Literal[True]
    law: VersionRef
    patient_id: Identifier
    origin: AwareDatetime
    cutoff: AwareDatetime
    lineage: list[ObservedEvent]
    active_record_ids: list[Identifier]

    @model_validator(mode='after')
    def lawful_projection(self):
        BreadthHistory(version=HISTORY_VERSION,synthetic=True,law=self.law,patient_id=self.patient_id,origin=self.origin,records=self.lineage)
        if self.cutoff.utcoffset()!=timedelta(0) or len(visible_records(self.lineage,self.cutoff))!=len(self.lineage):
            raise ValueError('all lineage must be strictly available before cutoff')
        heads=[r.record_id for r in lineage_heads(self.lineage) if r.record_status!='retracted']
        if self.active_record_ids!=heads:raise ValueError('exact ordered active lineage heads required')
        return self

    def active(self):return [r for r in self.lineage if r.record_id in self.active_record_ids]


class SupportFeatures(StrictModel):
    version: Literal['poc-breadth-features-v1']
    history: VersionRef
    patient_id: Identifier
    cutoff: AwareDatetime
    day: Annotated[int,Field(ge=0,le=84)]
    prior_quality: Annotated[float,Field(ge=0,le=10)]
    prior_missing: bool
    previous_six_prompts: Annotated[int,Field(ge=0,le=3)]
    age_control: float
    clinical_control: float
    device_control: float
    scheduled_steroid: bool
    demographic_record: Identifier
    schedule_record: Identifier
    prior_quality_record: Identifier | None
    prompt_records: Annotated[list[Identifier],Field(max_length=3)]
    clinical_record: Identifier | None
    clinical_age_days: Annotated[float,Field(ge=0,le=7)] | None
    device_record: Identifier | None
    device_age_days: Annotated[float,Field(ge=0,le=7)] | None

    def prognostic(self):
        return (1.,self.prior_quality,float(self.prior_missing),self.previous_six_prompts/3,self.day/84,
            self.age_control,self.clinical_control,self.device_control)

    def effect_interactions(self):return (float(self.scheduled_steroid),self.previous_six_prompts/3)


def support_features(projection):
    """Predecision scalar transforms only; no fit, imputation of truth or policy."""
    if type(projection) is not BreadthProjection:raise ValueError('exact breadth projection required')
    projection=BreadthProjection.model_validate_json(projection.model_dump_json())
    day=(projection.cutoff.date()-projection.origin.date()).days
    if projection.cutoff.hour!=12 or any((projection.cutoff.minute,projection.cutoff.second,projection.cutoff.microsecond)):
        raise ValueError('support features require the prescribed noon decision cutoff')
    rows=projection.active();demos=[r for r in rows if r.kind=='demographic'];schedules=[r for r in rows if r.kind=='steroid_schedule']
    if len(demos)!=1 or len(schedules)!=1:raise ValueError('one admitted demographic and baseline schedule required')
    demo=demos[0];schedule=schedules[0];steroid=day%schedule.period_days in schedule.active_residues
    def latest(kind):
        candidates=[r for r in rows if r.kind==kind and getattr(r,'value',getattr(r,'sleep_minutes',None)) is not None
            and 0<=(projection.cutoff-r.event_at).total_seconds()/86400<=7]
        return max(candidates,key=lambda r:(r.event_at,r.available_at,r.record_id),default=None)
    clinical=latest('clinical');device=latest('device_sleep')
    reports=[r for r in rows if r.kind=='daily_report' and r.event_at.date()==projection.cutoff.date()]
    if len(reports)>1:raise ValueError('ambiguous prior-night report')
    report=reports[0] if reports else None;missing=report is None or report.value is None
    prompts=[r for r in rows if r.kind=='assignment' and r.component=='support' and r.option=='support_prompt'
        and day-6<=(r.event_at.date()-projection.origin.date()).days<day]
    return SupportFeatures(version=FEATURE_VERSION,history=reference(HISTORY_VERSION,'3.0.0',projection.model_dump(mode='json')),
        patient_id=projection.patient_id,cutoff=projection.cutoff,day=day,prior_quality=7. if missing else report.value,prior_missing=missing,
        previous_six_prompts=len(prompts),age_control=(demo.age_years-52.5)/22.5+.25*(2*demo.synthetic_sex_code-1),
        clinical_control=(0. if clinical is None else (clinical.value-4)/2)+.5*steroid,
        device_control=0. if device is None else (device.sleep_minutes-360)/60,scheduled_steroid=steroid,
        demographic_record=demo.record_id,schedule_record=schedule.record_id,
        prior_quality_record=None if report is None else report.record_id,prompt_records=[r.record_id for r in prompts],
        clinical_record=None if clinical is None else clinical.record_id,clinical_age_days=None if clinical is None else (projection.cutoff-clinical.event_at).total_seconds()/86400,
        device_record=None if device is None else device.record_id,device_age_days=None if device is None else (projection.cutoff-device.event_at).total_seconds()/86400)


class BreadthExport(StrictModel):
    """New observed candidate, never silently passed to old run/Store readers."""
    version: Literal['poc-breadth-observed-export-v1']
    synthetic: Literal[True]
    run_id: Identifier
    cohort_id: Identifier
    replicate: Annotated[int,Field(ge=0)]
    role: Literal['prospective','external']
    law: VersionRef
    history_definition: VersionRef
    feature_definition: VersionRef
    source_commit: Annotated[str,Field(pattern=r'^[a-f0-9]{40}$')]
    runtime: VersionRef
    cutoff: AwareDatetime
    origin: AwareDatetime
    member_order: list[Identifier]
    histories: list[BreadthProjection]
    support: list[SupportFeatures]
    publication_status: Literal['candidate_requires_independent_source_runtime_export_admission']

    @model_validator(mode='after')
    def complete_observed_candidate(self):
        n=12 if self.role=='prospective' else 120
        if len(self.member_order)!=n or len(set(self.member_order))!=n or len(self.histories)!=n or len(self.support)!=n:
            raise ValueError('exact planned complete12 cohort or120 external-study roster required')
        if self.law.model_dump()!=LAW_REF or self.history_definition.model_dump()!=HISTORY_REF or self.feature_definition.model_dump()!=FEATURE_REF:
            raise ValueError('versioned law/history/feature definitions mismatch')
        if [h.patient_id for h in self.histories]!=self.member_order or [f.patient_id for f in self.support]!=self.member_order:
            raise ValueError('original member order must be preserved in whole export')
        if any(h.cutoff!=self.cutoff or h.origin!=self.origin for h in self.histories):raise ValueError('whole export cutoff/origin mismatch')
        if any(f!=support_features(h) for h,f in zip(self.histories,self.support)):
            raise ValueError('compact features must equal exact lawful history transforms')
        return self
