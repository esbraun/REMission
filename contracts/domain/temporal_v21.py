"""TIME2.1 public structural ordering; legacy TIME1/2 types stay unchanged."""
from typing import Annotated,Literal
from pydantic import Field,model_validator
from .common import Identifier,Name,StrictModel
from .temporal import Parent,ReportingRules

EstimandIDV21=Literal['EST-VISIT','EST-N1','EST-ESC-STAGE','EST-ESC-STRATEGY','EST-MRT','EST-POLICY','EST-INT','EST-MRT-BURDEN']
Role=Literal['covariate','treatment','mediator','outcome','observation_indicator','intercurrent_event','administrative']


class ReportingRulesV21(ReportingRules):
    equal_time:Literal['strict_before_excludes_equal_arrivals_committed_source_sequence_for_dependencies']
    completion:Literal['one_R_announced_08:01_before_values_shared_with_burden']
    state_publication:Literal['08:02_first_sweep_strictly_after_dependency_availability']
    link_publication:Literal['08:03_first_sweep_strictly_after_state_availability']
    report_likelihood:Literal['R_once_shared_delay_once_received_measurements_once']
    burden_missingness:Literal['same_R_and_delay_no_second_observation_or_upload_draw']
    current_admission:Literal['separate_committed_09_G_never_equal_time_learner_H']


class VariableV21(StrictModel):
    id:Identifier
    phase:Annotated[int,Field(ge=0)]
    unit:Name
    visibility:Literal['observed','evaluator_only','administrative']
    parents:list[Parent]
    role_by_estimand:dict[EstimandIDV21,Role]
    postassignment_role_by_estimand:dict[EstimandIDV21,Role]
    source_locator:Name


class TemporalContractV21(StrictModel):
    schema_version:Literal['2.1.0']
    synthetic:Literal[True]
    kind:Literal['temporal_contract']
    id:Literal['TIME-01']
    version:Literal['2.1.0']
    timestamp_rule:Literal['timezone_aware_utc_order_local_calendar_preserved']
    learner_cutoff_rule:Literal['event_at_lte_cutoff_recorded_and_available_strictly_before']
    tie_rule:Literal['committed_source_sequence_prefix_for_equal_clock_ancestry_not_record_id_authority']
    daily_factorization:Annotated[list[Name],Field(min_length=1)]
    initial_distribution:Literal['must_be_versioned_by_G0_DGP_before_generation']
    irregular_visit_process:Literal['must_be_versioned_by_G0_DGP_before_generation']
    variables:Annotated[list[VariableV21],Field(min_length=1)]
    pending_numerical_decisions:Annotated[list[Name],Field(min_length=1)]
    reporting:ReportingRulesV21

    @model_validator(mode='after')
    def complete_graph(self):
        vs={v.id:v for v in self.variables}
        if len(vs)!=len(self.variables):raise ValueError('duplicate TIME2.1 structural variable')
        ids={'EST-VISIT','EST-N1','EST-ESC-STAGE','EST-ESC-STRATEGY','EST-MRT','EST-POLICY','EST-INT','EST-MRT-BURDEN'}
        for v in self.variables:
            if set(v.role_by_estimand)!=ids or set(v.postassignment_role_by_estimand)!=ids:
                raise ValueError('complete pre/post role map for every estimand required')
            for p in v.parents:
                if p.variable not in vs or (p.day_offset==0 and vs[p.variable].phase>=v.phase):
                    raise ValueError('unknown/future/same-phase structural parent')
        required={
            'burden_full':{'support_window_counts','innovations'},
            'report_completion':{'report_observation'},
            'burden_rating_availability':{'burden_full','report_observation','innovations'},
            'report_upload_receipt':{'report_completion','report_availability','burden_rating_availability'},
            'burden_assessment_state':{'report_completion','report_upload_receipt'},
            'support_burden_outcome_link':{'burden_assessment_state'},
            'current_synthetic_assessment':{'clinical_L','intercurrent_events','committed_safety_prefix'},
            'episode_review_readiness':{'current_synthetic_assessment','intercurrent_events','committed_safety_prefix'},
            'current_admission_G':{'current_synthetic_assessment','episode_review_readiness','current_consent_and_holds'},
            'eligibility':{'current_admission_G'}}
        for name,parents in required.items():
            if name not in vs or not parents<={p.variable for p in vs[name].parents}:
                raise ValueError('TIME2.1 required source/factor missing: '+name)
        if vs['burden_full'].visibility!='evaluator_only':raise ValueError('full burden remains private')
        if any(p.variable=='burden_full' for v in self.variables if v.id in ('clinical_L','severity','report_observation','support_propensity') for p in v.parents):
            raise ValueError('burden cannot acquire new clinical/reporting/policy causal arrows')
        if any(p.variable=='current_admission_G' for p in vs['available_history'].parents):
            raise ValueError('equal09 admissionG cannot be a learnerH covariate')
        return self


def temporal_definition():
    """Explicit new DAG preserves old coefficient laws and estimand role keys."""
    import json
    from copy import deepcopy
    from pathlib import Path
    value=json.loads(Path(__file__).with_name('temporal-v2.json').read_bytes())
    value.update(schema_version='2.1.0',version='2.1.0',tie_rule='committed_source_sequence_prefix_for_equal_clock_ancestry_not_record_id_authority')
    variables=value['variables'];by_id={v['id']:v for v in variables}
    for v in variables:
        v['phase']*=10
        v['role_by_estimand']['EST-MRT-BURDEN']=v['role_by_estimand']['EST-MRT']
        v['postassignment_role_by_estimand']['EST-MRT-BURDEN']=v['postassignment_role_by_estimand']['EST-MRT']
    def add(name,phase,visibility,parents,role='administrative',unit='none'):
        v=dict(id=name,phase=phase,unit=unit,visibility=visibility,
            parents=[dict(variable=n,day_offset=d) for n,d in parents],
            role_by_estimand={k:'administrative' for k in by_id['M']['role_by_estimand']},
            postassignment_role_by_estimand={k:'administrative' for k in by_id['M']['role_by_estimand']},
            source_locator='docs/spec/dgp-reference-v1.3.md; accepted5409 scientific contract')
        v['role_by_estimand']['EST-MRT-BURDEN']=role;v['postassignment_role_by_estimand']['EST-MRT-BURDEN']=role
        variables.append(v);by_id[name]=v
    add('support_delivery',181,'observed',[('support_assignment',0),('intercurrent_events',0),('innovations',0)],'mediator','count')
    add('support_window_counts',5,'administrative',[('support_delivery',-d) for d in range(1,8)],'covariate','count')
    add('burden_full',12,'evaluator_only',[('support_window_counts',0),('innovations',0)],'outcome','synthetic_burden_score')
    add('report_completion',71,'observed',[('report_observation',0)],'observation_indicator','indicator')
    add('burden_rating_availability',80,'observed',[('burden_full',0),('report_observation',0),('innovations',0)],'outcome','synthetic_burden_score')
    add('report_upload_receipt',81,'administrative',[('report_completion',0),('report_availability',0),('burden_rating_availability',0)])
    add('burden_assessment_state',82,'administrative',[('report_completion',0),('report_upload_receipt',0)])
    add('support_burden_outcome_link',83,'administrative',[('burden_assessment_state',0),('support_assignment',-1)])
    by_id['available_history']['parents'] += [dict(variable=n,day_offset=0) for n in ('report_completion','burden_rating_availability','burden_assessment_state','support_burden_outcome_link')]
    # New completion is an observed deterministic child of the single private
    # reporting draw. MNAR current quality remains an integration variable.
    by_id['report_observation']['visibility']='evaluator_only'
    by_id['report_observation']['parents'].append(dict(variable='morning_measurements',day_offset=0))
    add('committed_safety_prefix',101,'administrative',[('intercurrent_events',0),('available_history',0)])
    add('current_synthetic_assessment',102,'observed',[('clinical_L',0),('intercurrent_events',0),('committed_safety_prefix',0)],'covariate','indicator')
    add('episode_review_readiness',103,'administrative',[('current_synthetic_assessment',0),('intercurrent_events',0),('committed_safety_prefix',0)])
    by_id['current_consent_and_holds']['parents'].append(dict(variable='episode_review_readiness',day_offset=0))
    add('current_admission_G',119,'administrative',[('current_synthetic_assessment',0),('episode_review_readiness',0),('current_consent_and_holds',0),('support_window_counts',0)],'covariate')
    by_id['eligibility']['parents'].append(dict(variable='current_admission_G',day_offset=0))
    value['variables']=sorted(variables,key=lambda v:(v['phase'],v['id']))
    value['reporting'].update(equal_time='strict_before_excludes_equal_arrivals_committed_source_sequence_for_dependencies',
        completion='one_R_announced_08:01_before_values_shared_with_burden',
        state_publication='08:02_first_sweep_strictly_after_dependency_availability',
        link_publication='08:03_first_sweep_strictly_after_state_availability',
        report_likelihood='R_once_shared_delay_once_received_measurements_once',
        burden_missingness='same_R_and_delay_no_second_observation_or_upload_draw',
        current_admission='separate_committed_09_G_never_equal_time_learner_H')
    value['daily_factorization'] += [
        'p(B_full_t | current07 window delivered countD,six previous windowsN); no new outgoing clinical/policy/report arrow',
        'p(R_t | accepted report predictors; integrated currentQ only in declared MNAR modes); one sharedR, separate shared delta',
        'publicR08:01 -> response upload -> receipt ->08:02 state ->08:03 link; strict learner availability always excludes equality',
        '09a events/schedules ->09b qualified binary/current assessment ->09c union/review ->09d eligibility ->09e assignment',
        'conditional burden target integrates permittedH plus committed currentG givenI1; descendants recomputed under each arm']
    return deepcopy(value)
