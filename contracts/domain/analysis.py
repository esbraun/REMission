"""Restricted, versioned H* product. No raw envelopes or simulator state cross it."""
from datetime import timedelta
import hashlib
import json
from typing import Annotated, Literal

from pydantic import AwareDatetime, Field, model_validator
from .common import Identifier, Sha256, StrictModel, VersionRef, Versioned
from .estimands import FitRequest


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def sha(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


CONFIG = dict(id="poc-visit-v1", chains=4, tune=1000, draws=1000, extension_tune=2000,
              extension_draws=2000, target_accept=.95, max_treedepth=12,
              batches=8, initial_k=1024, max_k=65536, integration_seconds=1800,
              bootstrap_resamples=1000, bootstrap_block=20, bootstrap_seed=721981,
              mean_se=.05, sd_floor=.10, absolute_stability=.01,
              relative_variance=.01, relative_stability=.02,
              cpu=2, memory_gib=2, model="rounded-clipped-state-space-v1",
              gaussian_integration="exact-conditional-on-adherence-v1")


def reference(identifier, value):
    return dict(id=identifier, version="1.0.0", sha256=sha(value))


CONFIG_REF = reference("poc-visit-v1", CONFIG)
HISTORY_REF = reference("poc-analysis-history-v1", "quality/ISI/indicators/assignments/deliveries/reduced-lineage-v1")
ESTIMAND_REF = reference("EST-VISIT:poc-hstar-v1", "Expected ISI at 42 future days: escalate minus continue conditional on reduced H*; retain plans; no prompt")
MODEL_REF = reference(CONFIG["model"], "contract 20261021: b hierarchy; independent beta hierarchy; sinusoid; AR; rounded clipped total ISI and quality")
PRIOR_REF = reference("poc-visit-prior-v1", "mu_b N(19,5);sd_b HN(3);beta N(0,4);sd_beta HN(1);a N(0,1);rho U(-.95,.95);sd_e,sd_isi HN(2);sd_quality HN(1);p Beta(1,1)")
PROTOCOL_REF = reference("poc-visit-retain-v1", "42 future nights; endpoint mean nights29..42; retain both plans at14/28; no prompt; C .65/.35 E .8/.2; untreated baseline")
DGP_REF = reference('poc-longitudinal-v1','public observed v1 interface; private realizations denied')
SCENARIO_REF = reference('poc-interactive-reference-v1','uninterrupted physician-selected behavioral plans')


class Header(StrictModel):
    record_id: Identifier
    patient_id: Identifier
    kind: Literal["daily_report", "isi", "assignment", "delivery"]
    event_at: AwareDatetime
    recorded_at: AwareDatetime
    available_at: AwareDatetime
    lineage_id: Identifier
    revision: Annotated[int, Field(ge=1)]
    supersedes: Identifier | None
    duplicate_of: Identifier | None
    record_status: Literal["active", "corrected", "retracted"]


class Quality(Header):
    kind: Literal["daily_report"]
    sleep_quality: Annotated[float, Field(ge=0, le=10)] | None
    missingness: Literal["observed", "missing", "pending"]

    @model_validator(mode="after")
    def observation(self):
        if (self.sleep_quality is not None) != (self.missingness == "observed"):
            raise ValueError("designated quality indicator/value mismatch")
        if self.sleep_quality is not None and abs(self.sleep_quality*1000-round(self.sleep_quality*1000)) > 1e-8:
            raise ValueError("quality resolution must be .001")
        return self


class ISI(Header):
    kind: Literal["isi"]
    total: Annotated[int, Field(ge=0, le=28)]
    instrument_version: Literal["ISI-7-synthetic-14d-v1"]
    recall_days: Literal[14]
    recall_start: AwareDatetime
    recall_end: AwareDatetime


class Plan(Header):
    kind: Literal["assignment"]
    option: Literal["behavioral_continue", "behavioral_escalate"]
    experimental: Literal[False]


class Taken(Header):
    kind: Literal["delivery"]
    assignment_id: Identifier
    option: Literal["behavioral_continue", "behavioral_escalate"]
    stage: Literal["taken", "not_taken"]
    adherence: Literal[0.0, 1.0]
    rescue: Literal[False]
    protocol_deviations: Annotated[list[str], Field(max_length=0)]


ReducedRecord = Annotated[Quality | ISI | Plan | Taken, Field(discriminator="kind")]


def header(record):
    return record.model_dump(include=set(Header.model_fields), mode="json")


class AnalysisHistory(Versioned):
    kind: Literal["poc_analysis_history"]
    version: Literal["poc-analysis-history-v1"]
    patient_id: Identifier
    cutoff: AwareDatetime
    origin: AwareDatetime
    protocol: VersionRef
    eligibility: Literal["uninterrupted-v1-behavioral-no-prompt"]
    records: list[ReducedRecord]
    provenance: list[Header]

    @model_validator(mode="after")
    def admitted(self):
        if self.protocol.model_dump() != PROTOCOL_REF:
            raise ValueError("unsupported public protocol")
        delta = (self.cutoff-self.origin).total_seconds()/86400
        if delta != int(delta) or not 0 <= delta <= 84:
            raise ValueError("invalid fictional noon cutoff")
        ids = {r.record_id: r for r in self.provenance}
        if len(ids) != len(self.provenance):
            raise ValueError("duplicate provenance ID")
        revisions = set()
        successors = set()
        for r in self.provenance:
            if r.patient_id != self.patient_id or not r.event_at <= r.recorded_at <= r.available_at < self.cutoff:
                raise ValueError("future/unavailable/patient header")
            if r.duplicate_of is None:
                key = (r.lineage_id, r.revision)
                if key in revisions:
                    raise ValueError("duplicate lineage revision")
                revisions.add(key)
            for prior_id, duplicate in ((r.supersedes, False), (r.duplicate_of, True)):
                if prior_id is None:
                    continue
                p = ids.get(prior_id)
                if p is None or p.kind != r.kind or p.event_at != r.event_at or p.available_at > r.available_at:
                    raise ValueError("invalid reduced lineage")
                if not duplicate:
                    if p.lineage_id != r.lineage_id or p.revision+1 != r.revision or prior_id in successors:
                        raise ValueError("invalid correction")
                    successors.add(prior_id)
        heads = {i: header(r) for i, r in ids.items() if i not in successors and r.duplicate_of is None and r.record_status != "retracted"}
        if len({r.record_id for r in self.records}) != len(self.records) or {r.record_id for r in self.records} != heads.keys():
            raise ValueError("active values must match distinct lineage heads")
        if any(header(r) != heads[r.record_id] for r in self.records):
            raise ValueError("reduced lineage/value mismatch")
        # These complete-grid checks also prevent a second contribution at one night.
        day = int(delta)
        reports = [r for r in self.records if r.kind == "daily_report"]
        if sorted(r.event_at for r in reports) != [self.origin+timedelta(days=t, minutes=-1) for t in range(1, day+1)]:
            raise ValueError("one quality indicator per observed night required")
        isi = [r for r in self.records if r.kind == "isi"]
        if sorted(r.recall_end for r in isi) != [self.origin+timedelta(days=t, hours=-1) for t in range(0, day+1, 14)]:
            raise ValueError("scheduled cumulative ISI required exactly once")
        for r in isi:
            if r.recall_end-r.recall_start != timedelta(days=14) or r.event_at != r.recall_end+timedelta(minutes=59):
                raise ValueError("ISI recall/assessment mismatch")
        plans = sorted((r for r in self.records if r.kind == "assignment"), key=lambda r:r.event_at)
        if len({r.event_at for r in plans}) != len(plans) or any((r.event_at-self.origin).total_seconds()%86400 or r.event_at<self.origin for r in plans):
            raise ValueError("invalid assignment clock")
        deliveries = {r.event_at:r for r in self.records if r.kind == "delivery"}
        if len(deliveries) != sum(r.kind == "delivery" for r in self.records):
            raise ValueError("duplicate delivery contribution")
        expected_times = set()
        for t in range(1, day+1):
            noon = self.origin+timedelta(days=t-1)
            plan = next((r for r in reversed(plans) if r.event_at <= noon), None)
            at = noon+timedelta(hours=8)
            if plan is not None:
                expected_times.add(at)
                r = deliveries.get(at)
                if r is None or r.assignment_id != plan.record_id or r.option != plan.option or r.adherence != float(r.stage == "taken"):
                    raise ValueError("complete consistent typed delivery required; missing is not zero")
        if set(deliveries) != expected_times:
            raise ValueError("unexpected delivery")
        return self


def project_history(projected):
    """Input must first pass authoritative typed available-at/lineage projection."""
    baseline = min((r for r in projected.records if r.kind == "isi"), key=lambda r:r.recall_end, default=None)
    if baseline is None:
        raise ValueError("baseline ISI required")
    selected = {"daily_report", "isi", "assignment", "delivery"}
    if any(r.kind == "intercurrent_event" for r in projected.records):
        raise ValueError("uninterrupted reference model only")
    # Admit the explicitly supported observed producer BEFORE stripping source
    # envelopes. This is engineering source qualification, not clinical review.
    for r in [*projected.records,*projected.provenance]:
        if r.kind not in selected:
            continue
        expected=('foundation-synthetic','research_configuration') if r.kind=='assignment' else ('poc-longitudinal-v1','simulation')
        if (r.source.id,r.source.adapter)!=expected or r.source.version!='1.0.0' or r.schema_version!='1.0.0':
            raise ValueError('unqualified observed producer for restricted v1 analysis')
    records = []
    for r in projected.records:
        if r.kind not in selected:
            continue
        value = header(r)
        if r.kind == "daily_report":
            value.update(sleep_quality=r.sleep_quality, missingness=r.missingness)
        elif r.kind == "isi":
            value.update(total=r.total, instrument_version=r.instrument_version, recall_days=r.recall_days,
                         recall_start=r.recall_start.isoformat(), recall_end=r.recall_end.isoformat())
        elif r.kind == "assignment":
            if r.clinician_override is not None or r.support_policy.id != "fixed-approved-support":
                raise ValueError("unsupported assignment/support")
            value.update(option=r.option, experimental=r.experimental)
        else:
            value.update(**r.model_dump(include={"assignment_id", "option", "stage", "adherence", "rescue", "protocol_deviations"}, mode="json"))
        records.append(value)
    return AnalysisHistory.model_validate_json(canonical(dict(schema_version="1.0.0", synthetic=True,
        kind="poc_analysis_history", version="poc-analysis-history-v1", patient_id=projected.patient_id,
        cutoff=projected.cutoff.isoformat(), origin=(baseline.recall_end+timedelta(hours=1)).isoformat(),
        protocol=PROTOCOL_REF, eligibility="uninterrupted-v1-behavioral-no-prompt", records=records,
        provenance=[header(r) for r in projected.provenance if r.kind in selected])))


class AnalysisInput(Versioned):
    kind: Literal["poc_visit_input"]
    attempt_id: Identifier
    request: FitRequest
    history: AnalysisHistory
    history_sha256: Sha256

    @model_validator(mode="after")
    def frozen(self):
        ctx = self.request.context
        expected = [(ctx.estimand, ESTIMAND_REF), (ctx.comparator_estimand, ESTIMAND_REF),
                    (ctx.model, MODEL_REF), (ctx.prior, PRIOR_REF), (ctx.protocol, PROTOCOL_REF),
                    (self.request.configuration, CONFIG_REF),(ctx.dgp,DGP_REF),(ctx.scenario,SCENARIO_REF)]
        if any(a.model_dump() != b for a,b in expected) or ctx.input_data.model_dump() != reference("poc-analysis-history-v1", self.history.model_dump(mode="json")):
            raise ValueError("unsupported configuration/input identity")
        if ctx.observation_cutoff != self.history.cutoff or self.history_sha256 != sha(self.history.model_dump(mode="json")):
            raise ValueError("history hash/cutoff mismatch")
        if ctx.seed.namespace != "fit" or ctx.seed.patient != self.history.patient_id:
            raise ValueError("independent fit seed required")
        return self


def make_input(history,attempt_id,replicate):
    value=history.model_dump(mode='json')
    ctx=dict(estimand=ESTIMAND_REF,dgp=DGP_REF,scenario=SCENARIO_REF,input_data=reference('poc-analysis-history-v1',value),
        prior=PRIOR_REF,model=MODEL_REF,protocol=PROTOCOL_REF,observation_cutoff=history.cutoff.isoformat(),
        seed=dict(namespace='fit',protocol='poc-visit-v1',scenario='interactive-reference',replicate=replicate,
                  patient=history.patient_id,time_index=(history.cutoff-history.origin).days,process='native-nuts'),
        allowed_information='available_observed_history_only',truth_access='denied',comparator_estimand=ESTIMAND_REF,
        comparator_information='same_permitted_history',source_ids=['BAYES-02','EST-VISIT','POC-4'],
        failure_policy='retain_all_attempts_fail_or_abstain_never_fabricate')
    return AnalysisInput.model_validate_json(canonical(dict(schema_version='1.0.0',synthetic=True,kind='poc_visit_input',attempt_id=attempt_id,
        request=dict(schema_version='1.0.0',synthetic=True,kind='fit_request',context=ctx,backend='pymc',sampler='native_nuts',precision='float64',configuration=CONFIG_REF),
        history=value,history_sha256=sha(value))))


class Effect(StrictModel):
    mean: float
    sd: Annotated[float, Field(ge=0)]
    lower: float
    upper: float
    unit: Literal["ISI_points"]
    kind: Literal["conditional_expected_assignment_contrast"]


class AnalysisResult(Versioned):
    kind: Literal["poc_visit_result"]
    attempt_id: Identifier
    input_sha256: Sha256
    history_sha256: Sha256
    cutoff: AwareDatetime
    configuration: VersionRef
    estimand: VersionRef
    status: Literal["completed", "abstained", "failed"]
    reason: str | None
    effect: Effect | None
    diagnostics: dict
    artifacts: list[dict]
    limitations: list[str]

    @model_validator(mode="after")
    def accepted(self):
        if self.configuration.model_dump() != CONFIG_REF or self.estimand.model_dump() != ESTIMAND_REF:
            raise ValueError("result configuration mismatch")
        if (self.status == "completed") != (self.effect is not None) or (self.status == "completed") != (self.reason is None):
            raise ValueError("failed/abstained result cannot expose accepted interval")
        canonical(self.model_dump(mode="json"))
        return self
