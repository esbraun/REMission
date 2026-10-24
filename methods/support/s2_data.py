"""Observed-only S2 preparation. Stdlib/scalar contracts; no Store or science.

Current SOURCE stage supports common-origin activation and reconstructable
active-head contexts only. Delayed activation/corrected-context coverage stays
pending; these are not final eligibility exclusions. No target sample minimum.
"""
from dataclasses import dataclass
from datetime import timedelta
from contracts.domain.analysis import sha
from contracts.domain.protocol_analysis import ProtocolHistory, nested_refs
from contracts.domain.support_s2_fit import S2FitProvenance

ACTIONS={'support_prompt','no_prompt'}


class InvalidInput(ValueError):pass
class UnsupportedInput(InvalidInput):pass
class Unavailable(ValueError):pass


def require(value,reason):
    if not value:raise InvalidInput(reason)


@dataclass(frozen=True)
class DecisionData:
    patient_id: str
    night: int
    index: int
    decision_id: str
    window_id: str
    outcome_id: str
    reward_revision: tuple[str,int,str] | None
    status: str
    action: int | None
    probability: float
    x: tuple[float,float,float,float] | None
    quality: float | None
    two_action: bool
    context_sha256: str
    source_ids: tuple[str,...]


@dataclass(frozen=True)
class MemberData:
    patient_id: str
    nights: tuple[int,...]
    night_status: tuple[str,...]
    rows: tuple[DecisionData,...]
    observed_counts: tuple[int,int]
    missing_counts: tuple[int,int]
    history_sha256: str
    revisions_sha256: str
    activation_id: str

    @property
    def observed(self):return tuple(r for r in self.rows if r.quality is not None)

    @property
    def prior_hierarchy_only(self):return not self.observed


@dataclass(frozen=True)
class CohortData:
    provenance: S2FitProvenance
    members: tuple[MemberData,...]
    contribution_sha256: str

    @property
    def target_index(self):return [m.patient_id for m in self.members].index(self.provenance.target_id)


def resolve(active,ref,kind):
    value=active.get(ref.record_id)
    require(value is not None and value.kind==kind
            and sha(value.model_dump(mode='json'))==ref.projection_sha256,'changed/unresolved reduced reference')
    return value


def consent_at(active,at):
    consents=[r for r in active.values() if r.kind=='consent' and r.component=='mrt_bandit' and r.available_at<=at]
    current=max(consents,key=lambda r:(r.available_at,r.recorded_at,r.revision,r.record_id),default=None)
    require(current is not None and current.consent_status=='active' and current.oversight_status=='approved_synthetic'
        and current.effective_at<=at and (current.expires_at is None or at<current.expires_at)
        and (current.withdrawn_at is None or at<current.withdrawn_at),'support consent/oversight unavailable')


def activation(history,binding,active):
    snapshot=resolve(active,binding.activation_ref,'protocol_snapshot')
    require(snapshot.family=='support' and snapshot.protocol==history.protocol and snapshot.template==history.protocol,
            'support activation protocol/template mismatch')
    if snapshot.activation_at!=history.origin:
        raise UnsupportedInput('pending delayed-activation alignment coverage; common-origin SOURCE stage only')
    require(bool(snapshot.consent_refs) and bool(snapshot.approval_refs),'activation consent/approval references required')
    consent_at(active,snapshot.activation_at)
    for ref in snapshot.consent_refs:
        r=resolve(active,ref,'consent');require(r.available_at<=snapshot.activation_at,'future activation consent')
    for ref in snapshot.approval_refs:
        r=resolve(active,ref,'approval')
        require(r.available_at<=snapshot.activation_at and r.purpose=='randomization_protocol' and r.option is None
            and len(r.permitted_options)==2 and set(r.permitted_options)==ACTIONS,'approved binary support snapshot required')
        d=active.get(r.decision_id)
        require(d is not None and d.kind=='decision_snapshot' and d.available_at<=r.event_at,'activation approval context missing')
    background=resolve(active,snapshot.background_ref,'assignment')
    require(background.option=='behavioral_continue' and not background.experimental and background.component is None
        and background.clinician_override is None and background.available_at<=snapshot.activation_at,'fixed public background required')
    for ref in snapshot.support_refs:
        r=active[ref.record_id]
        require(r.available_at<=snapshot.activation_at and (
            r.kind=='assignment' and r.option=='no_prompt' or
            r.kind=='support_decision' and r.availability!='randomized' and r.probabilities['support_prompt']==0),
            'activation support reference is not fixed known no-prompt')
    return snapshot


def features(history,decision,active):
    at=decision.cutoff;context=[r.record_id for r in decision.context]
    require(len(context)==len(set(context)) and decision.context_projection_sha256==sha([r.model_dump(mode='json') for r in decision.context]),
            'duplicate or changed original predecision context')
    for ref in decision.context:
        r=active[ref.record_id];require(r.available_at<at,'postdecision feature reference')
    if any(r.kind=='daily_report' and r.event_at<at<=r.available_at and r.supersedes for r in active.values()):
        raise UnsupportedInput('pending corrected original-context reconstruction coverage')
    prior=[r for r in active.values() if r.kind=='daily_report' and r.missingness=='observed'
           and r.event_at<at and r.available_at<at]
    previous=max(prior,key=lambda r:(r.event_at,r.available_at,r.recorded_at,r.record_id),default=None)
    delivered=[r for r in active.values() if r.kind=='delivery' and r.option=='support_prompt' and r.stage=='delivered'
        and at-timedelta(days=6)<=r.event_at<at and r.available_at<at]
    require(len({r.assignment_id for r in delivered})==len(delivered) and len({r.event_at for r in delivered})==len(delivered),
            'duplicate delivered prompt feature')
    for r in delivered:
        owner=active.get(r.assignment_id)
        require(owner is not None and owner.kind=='assignment' and owner.option=='support_prompt'
            and owner.event_at==r.event_at-timedelta(hours=8)
            and ((r.event_at-history.origin).total_seconds()/3600-8)%24==0,'unowned/misaligned public delivery')
    sources=tuple(sorted(([previous.record_id] if previous else [])+[r.record_id for r in delivered]))
    require(set(sources)<=set(context),'required original predecision feature reference missing')
    night=int((at-history.origin).total_seconds()/86400)+1
    return (7. if previous is None else float(previous.sleep_quality),float(previous is None),float(len(delivered)),night/84.),sources


def decision_row(history,decision,active):
    at=decision.cutoff;elapsed=(at-history.origin).total_seconds()/86400
    require(elapsed==int(elapsed) and 0<=elapsed<84,'public support decision night required')
    night=int(elapsed)+1;assessment=history.origin+timedelta(days=night,minutes=-1)
    require(decision.record_schema=='2.1.0' and decision.event_at==at==decision.outcome_window.starts_at
        and decision.outcome_window.assessment_at==decision.outcome_window.ends_at==assessment,'support decision/window clock mismatch')
    require(at<=decision.distribution_persisted_at<=decision.recorded_at and decision.available_at<assessment,'distribution must precede outcome')
    snapshot=resolve(active,decision.decision_snapshot,'decision_snapshot')
    require(snapshot.cutoff==at and snapshot.workflow.support_policy==decision.policy
        and snapshot.workflow.support_mode==decision.mode
        and [e for e in snapshot.eligibility if e.action in ACTIONS]==decision.eligibility,'original snapshot policy/eligibility mismatch')
    require(len(decision.eligibility)==2 and {e.action for e in decision.eligibility}==ACTIONS
        and set(decision.probabilities)==ACTIONS,'complete executed support vector required')
    expected_reason={'fixed':'fixed_no_prompt','frozen':'nof1_snapshot','mrt':'unrestricted','adaptive':'unrestricted'}
    require(decision.mode=='paused' or decision.policy_constraint.reason==expected_reason[decision.mode],'mode/policy constraint mismatch')
    executed={e.action for e in decision.eligibility if e.status=='eligible'}&set(decision.policy_constraint.allowed_actions)
    if decision.mode=='paused':executed=set()
    if decision.policy_constraint.snapshot_ref is not None:
        frozen=resolve(active,decision.policy_constraint.snapshot_ref,'protocol_snapshot')
        require(frozen.activation_at<=at and frozen.available_at<=at,'future frozen policy snapshot')
    outcome=active.get(decision.outcome_link_id)
    require(outcome is not None and outcome.kind=='support_outcome_link','missing resolved outcome link')
    require(outcome.support_decision.record_id==decision.record_id and outcome.window_id==decision.outcome_window.id
        and outcome.event_at==outcome.assessment_at==assessment and assessment<=outcome.evaluated_as_of<=outcome.recorded_at,
        'outcome ownership/window/clock mismatch')
    require(sum(r.kind=='support_outcome_link' and r.support_decision.record_id==decision.record_id for r in active.values())==1,
            'duplicate/conflicting resolved outcome contribution')
    status=outcome.reward.status;p=decision.probabilities['support_prompt'];action=None;quality=None;revision=None;x=None;sources=()
    two_action=False
    if decision.availability=='unavailable':
        require(not executed and not any(decision.probabilities.values()) and decision.assignment_id is None
            and outcome.assignment_ref is None and bool(decision.unavailable_reasons),'unavailable decision has assignment or probability')
        require(status in ('undefined','pending'),'unavailable assignment cannot supply reward likelihood')
    else:
        require(not decision.unavailable_reasons and abs(sum(decision.probabilities.values())-1.)<=1e-12,'final probabilities do not normalize')
        require(not snapshot.workflow.hold_reasons and snapshot.workflow.clinical!='clinical_hold','held support cannot assign')
        consent_at(active,at)
        assignment=active.get(decision.assignment_id)
        require(assignment is not None and assignment.kind=='assignment' and assignment.option in executed
            and assignment.decision_id==snapshot.record_id and assignment.support_policy==decision.policy
            and decision.distribution_persisted_at<=assignment.event_at and assignment.available_at<assessment
            and assignment.clinician_override is None and assignment.override_reason is None,'executed assignment/context/persistence mismatch')
        require(outcome.assignment_ref is not None and resolve(active,outcome.assignment_ref,'assignment')==assignment,'outcome assignment mismatch')
        approval=active.get(assignment.approval_id)
        require(approval is not None and approval.kind=='approval' and approval.decision_id==snapshot.record_id
            and approval.available_at<=assignment.event_at,'assignment approval missing/future')
        action=int(assignment.option=='support_prompt')
        if decision.availability=='randomized':
            require(executed==ACTIONS and all(.1<=v<=.9 for v in decision.probabilities.values())
                and assignment.experimental and assignment.component=='mrt_bandit'
                and assignment.probability==decision.probabilities[assignment.option]
                and approval.purpose=='randomization_protocol' and approval.option is None
                and len(approval.permitted_options)==2 and set(approval.permitted_options)==ACTIONS,'randomized assignment/final probability/approval mismatch')
            require(decision.mode!='mrt' or p==.5,'canonical MRT final probability mismatch')
            two_action=True
        else:
            require(len(executed)==1 and all(decision.probabilities[a]==float(a in executed) for a in ACTIONS)
                and action==p and not assignment.experimental and assignment.component is None and assignment.probability is None
                and approval.purpose=='ordinary_treatment' and approval.option==assignment.option,'deterministic approved A=p required')
        x,sources=features(history,decision,active)
        if status=='observed':
            require(outcome.reward.report_ref is not None,'observed reward report reference required')
            report=resolve(active,outcome.reward.report_ref,'daily_report')
            require(report.event_at==assessment and report.missingness=='observed' and report.available_at<outcome.evaluated_as_of,
                    'observed reward clock/availability mismatch')
            quality=float(report.sleep_quality);revision=(report.lineage_id,report.revision,report.record_id)
        elif status=='missing':
            reports=[active[r.record_id] for r in outcome.reward.evidence_refs if active[r.record_id].kind=='daily_report']
            require(any(r.event_at==assessment and r.missingness=='missing' for r in reports),'missing reward needs matching public missing report')
    return DecisionData(history.patient_id,night,night-1,decision.record_id,decision.outcome_window.id,outcome.record_id,
        revision,status,action,float(p),x,quality,two_action,decision.context_projection_sha256,sources)


def prepare(histories,provenance):
    """Full12 trusted exported observed histories; no peer selection or fitting."""
    provenance=S2FitProvenance.model_validate(provenance)
    require(len(histories)==12 and all(isinstance(h,ProtocolHistory) for h in histories),'exact12 typed public ProtocolHistory required')
    histories=tuple(ProtocolHistory.model_validate(h.model_dump()) for h in histories)
    require([h.patient_id for h in histories]==[m.patient_id for m in provenance.members],'complete ordered fitted membership mismatch')
    require(sha([h.model_dump(mode='json') for h in histories])==provenance.histories_sha256,'full H* cohort digest mismatch')
    members=[];contributions=[]
    for h,binding in zip(histories,provenance.members):
        require(h.family=='support' and h.origin==provenance.origin and h.cutoff==provenance.cutoff,'incompatible family/common origin/cutoff')
        history_hash=sha(h.model_dump(mode='json'));revisions_hash=sha([r.model_dump(mode='json') for r in sorted(h.provenance,key=lambda r:r.record_id)])
        require(history_hash==binding.history_sha256 and revisions_hash==binding.revisions_sha256,'changed member H*/revision digest')
        active={r.record_id:r for r in h.records};snapshot=activation(h,binding,active)
        # ProtocolHistory validates exact active lineage heads and EVERY nested
        # reduced reference. No caller model_construct bypass is trusted here.
        require(all(r.kind!='isi' for r in h.records),'ISI is not a support likelihood input')
        for r in h.records:
            for ref in nested_refs(r):require(ref.record_id in active,'unresolved public reference')
            if r.kind=='support_outcome_link':
                owner=resolve(active,r.support_decision,'support_decision')
                require(owner.outcome_link_id==r.record_id,'unowned/duplicate active outcome link')
        decisions=sorted((r for r in h.records if r.kind=='support_decision'),key=lambda r:(r.cutoff,r.record_id))
        require(len({r.cutoff for r in decisions})==len(decisions),'duplicate decision on latent night')
        rows=tuple(decision_row(h,r,active) for r in decisions)
        require(all(1<=r.night<=provenance.cutoff_day for r in rows),'decision outside full latent grid')
        observed=[0,0];missing=[0,0];status={}
        for r in rows:
            status[r.night]=r.status if r.action is not None else 'unavailable:'+r.status
            if r.two_action and r.status in ('observed','missing'):
                (observed if r.status=='observed' else missing)[r.action]+=1
            if r.quality is not None:contributions.append((r.patient_id,r.decision_id,r.window_id,r.reward_revision))
        reports={int((r.event_at-h.origin+timedelta(minutes=1)).total_seconds()/86400):r for r in h.records if r.kind=='daily_report'}
        nights=tuple(range(1,provenance.cutoff_day+1))
        members.append(MemberData(h.patient_id,nights,tuple(status.get(t,'no_decision:'+reports[t].missingness) for t in nights),
            rows,tuple(observed),tuple(missing),history_hash,revisions_hash,snapshot.record_id))
    require(len(set(contributions))==len(contributions),'duplicate observed reward revision contribution')
    if not contributions:raise Unavailable('entirely observation-free cohort cannot establish a genuine observed representative')
    return CohortData(provenance,tuple(members),sha(contributions))
