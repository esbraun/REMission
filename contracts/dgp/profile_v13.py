"""Accepted DGP1.3 contract data and finite laws; no production simulator.

Legacy1.2 authoring functions are deliberately unchanged. Consumers must select
and submit the entire new profile; missing bindings never acquire defaults.
"""
from copy import deepcopy
from datetime import date,datetime,time,timedelta,timezone
from hashlib import sha256
import json
from pathlib import Path
from zoneinfo import ZoneInfo

from .parameters import reference_parameters as legacy_parameters
from .scenarios import scenario_manifest as legacy_scenarios
from .truth import seed_words

ROOT=Path(__file__).parent
VERSION='1.3.0'
OBSERVED_VERSION='2.1.0'
CATALOG_VERSION='1.1.0'
PLAN_SHA256='87e5b95f93f97d2beb19bef9ac159c8293655589c637668b948ff69ac39d17b5'
LAW_VERSION='1.0.0-r1'
LAW_IDS=('SIM-REVIEW-01','SIM-BURDEN-01','REPORT-STATUS-01','EST-MRT-BURDEN','BURDEN-PRECISION-01')
FROZEN_DATA={'cell-law-bindings-v1.3.json':'017643b46921f9cc1956da13438f6170a1444845a15538a8ff824e3923d11467',
    'review-scripts-v1.3.json':'9e5fceb29dd31ee60d5cae5d08088d8539396d7f1d21a6de07c69172dbef222c'}


def encoded(value):
    return (json.dumps(value,indent=2,sort_keys=True,ensure_ascii=True,allow_nan=False)+'\n').encode()


def reference_laws():
    return dict(version=VERSION,synthetic=True,execution='contract_data_not_qualified_engine',
        review=dict(id='SIM-REVIEW-01',version=LAW_VERSION,threshold_entry='any_coordinate_strictly_greater_than_3',
            threshold_measurement='all_coordinates_less_than_or_equal_to_3',earliest_review='next_local_date_09:00',
            resolution='assessment_only',earliest_resume='next_local_date_09:00_with_fresh_all_condition_assessment',
            current_sources='committed_same_09_source_sequence_prefix',unknown='retain_entire_hold',
            live_authority=False),
        burden=dict(id='SIM-BURDEN-01',version=LAW_VERSION,instrument='synthetic-support-burden-item',
            categories=[0,1,2,3,4],unit='synthetic_burden_score',window='local_07_to_next_local_07_half_open',
            previous_windows=6,delivered_domain=[0,1],rolling_maximum=4,no_delivery_score=0,
            trials=4,base_probability=.25,prior_count_slope=.05,
            reporting='same_single_R_and_delay_as_DailyReport',outgoing_causal_arrows=[]),
        report_status=dict(id='REPORT-STATUS-01',version=LAW_VERSION,decision='08:01',
            parent_publication='08:01',state_sweep='08:02',support_link_sweep='08:03',
            shared_indicator=True,shared_upload_delay=True,burden_in_DailyReport=None,
            likelihood='R_once_then_shared_delay_and_received_measurements_once',
            missing='R0_without_numeric_response',pending='R1_not_yet_received',
            undefined='terminal_or_outside_horizon_not_missingness'),
        target=dict(id='EST-MRT-BURDEN',version=LAW_VERSION,unit=['probability','synthetic_burden_score'],
            required_times=[0,21,42,83],horizon_control=84,definition_indicator='Z',report_indicator='R',
            native_q='one_for_enrolled_alive_decisions_t_lte83_zero_at84_by_horizon',
            history='strict_H_and_separate_current_committed_G_conditioned_on_I1',
            comparator='evaluator_complete_outcome_randomized_reference',
            information_role='private_evaluator',ratio_denominator='sum(Z)',q_denominator='assigned_arm_n'),
        precision=dict(id='BURDEN-PRECISION-01',version=LAW_VERSION,trials=1000,
            conditional_trial_environments=60,conditional_arm_n=30,availability_candidate_cap=10000,
            truth_draws_per_batch=10000,truth_first_assessment_batches=32,truth_max_batches=1000,
            particle_levels=[1024,4096,16384,65536],truth_filters_per_level=32,
            environment_filters_per_level_history=60000,absolute_probability_mcse=.001,
            absolute_mean_mcse=.01,relative_binding_fraction=.1,budget_fraction=.25,
            lower_limit_multiplier=1.645,agreement_multiplier=1.96,interval_alpha=.05/6,
            ratio_variance='v_times_E_inverse_positive_Binomial_denominator',
            structural_proof='independent_derived_and_source_bound',
            sampled_zero='unresolved_without_structural_proof',
            actual_execution='future_measured_gate_not_finite_fixture'))


def artifact_ref(path,identifier,version,*,temporal_source=False):
    raw=Path(path).read_bytes()
    if temporal_source:raw=raw.replace(b'\r\n',b'\n')
    return dict(id=identifier,version=version,sha256=sha256(raw).hexdigest())


def profile_bindings():
    from contracts.domain.temporal_v21 import TemporalContractV21,temporal_definition
    raw=(ROOT.parent/'domain/temporal-v2.1.json').read_bytes().replace(b'\r\n',b'\n')
    TemporalContractV21.model_validate_json(raw)
    if raw!=encoded(temporal_definition()):raise ValueError('TIME2.1 exact source drift; no new order under old binding')
    for path,digest in FROZEN_DATA.items():
        if sha256((ROOT/path).read_bytes()).hexdigest()!=digest:raise ValueError('accepted scientific contract data drift: '+path)
    return dict(dgp=VERSION,parameters=VERSION,observed=OBSERVED_VERSION,catalog=CATALOG_VERSION,
        scientific_plan=dict(id='G1-CLEARANCE-BURDEN-R1',version=LAW_VERSION,sha256=PLAN_SHA256),
        temporal=artifact_ref(ROOT.parent/'domain/temporal-v2.1.json','TIME-01',OBSERVED_VERSION,temporal_source=True),
        review_scripts=artifact_ref(ROOT/'review-scripts-v1.3.json','SIM-REVIEW-SCRIPTS',LAW_VERSION),
        cell_laws=artifact_ref(ROOT/'cell-law-bindings-v1.3.json','DGP-CELL-LAWS',CATALOG_VERSION),
        laws={name:dict(id=name,version=LAW_VERSION,sha256=sha256(encoded(reference_laws())).hexdigest()) for name in LAW_IDS})


def reference_parameters():
    result=deepcopy(legacy_parameters());result['version']=VERSION;result['profile']=profile_bindings()
    result['temporal_contract']=deepcopy(result['profile']['temporal'])
    rows={
        'burden_score_trials':(4,'count','Binomial trials','delivered_support_count'),
        'burden_base_probability':(.25,'probability','p=.25+.05*N when D=1','previous_six_local_window_deliveries'),
        'burden_prior_count_slope':(.05,'probability_per_count','p=.25+.05*N when D=1','previous_six_local_window_deliveries'),
        'burden_local_windows':(7,'local_calendar_windows','half-open07-to07; six previous plus current','local_calendar'),
        'review_earliest_next_date':(1,'local_calendar_days','no same-date resolution','episode_entry_local_date'),
        'resume_earliest_next_date':(1,'local_calendar_days','fresh all-condition assessment before assignment','resolution_local_date'),
        'report_completion_clock':('08:01','local_clock','immediate publicR parent before response publication','report_observation'),
        'report_status_sweep_clock':('08:02','local_clock','first sweep strictly after source availability','committed_source_prefix'),
        'burden_link_sweep_clock':('08:03','local_clock','state must already be strictly available','burden_assessment_state'),
        'availability_candidate_cap':(10000,'independent_generating_units','first eligible pre-enrollment candidate; no replacement','named_population_sampler')}
    for name,(value,unit,equation,parents) in rows.items():
        result['parameters'][name]=dict(value=value,unit=unit,distribution=equation,parents=[parents],
            applicability='explicit DGP1.3 only',provenance='synthetic_engineering',
            source='docs/spec/dgp-reference-v1.3.md',source_kind='accepted_scientific_contract_5409')
    return result


def scenario_manifest():
    old=legacy_scenarios();bindings=json.loads((ROOT/'cell-law-bindings-v1.3.json').read_bytes())
    rows=bindings['ordered_cells']
    if len(rows)!=82 or [r['cell_id'] for r in rows]!=[c['id'] for c in old['cells']]:
        raise ValueError('complete ordered82-cell law binding required')
    old.update(version=VERSION,catalog_binding=CATALOG_VERSION,profile=profile_bindings(),
               temporal_contract=profile_bindings()['temporal'])
    for cell,row in zip(old['cells'],rows,strict=True):
        if row['patients']!=cell['patients'] or row['original_overrides']!=cell['overrides']:
            raise ValueError('old catalog coefficients/sample sizes cannot change')
        cell.update(version=VERSION,scientific_law_binding=deepcopy(row))
    return old


def require_exact(value,expected,label):
    if encoded(value)!=encoded(expected):raise ValueError(label+' missing/unknown/mismatched version or binding; no fallback')
    return deepcopy(value)


def validate_parameters(value):return require_exact(value,reference_parameters(),'DGP1.3 parameters')
def validate_scenarios(value):return require_exact(value,scenario_manifest(),'DGP1.3 catalog')


def resolve_cell(parameters,scenarios,cell_id):
    p=validate_parameters(parameters);s=validate_scenarios(scenarios)
    cells=[c for c in s['cells'] if c['id']==cell_id]
    if len(cells)!=1:raise ValueError('unknown DGP1.3 cell; no legacy/reference fallback')
    cell=cells[0]
    for name,value in cell['overrides'].items():p['parameters'][name]['value']=deepcopy(value)
    return dict(cell=cell,parameters=p['parameters'],profile=p['profile'])


def burden_probability(delivered,previous):
    """Finite contract law, not a draw or a calibrated output."""
    if type(delivered) is not int or delivered not in (0,1) or type(previous) is not int or previous<0 or delivered+previous>4:
        raise ValueError('burden count outside declared local-window source profile; never clip')
    return None if delivered==0 else .25+.05*previous


def rating_window(local_date,timezone_id):
    if type(local_date) is not date:raise ValueError('local assessment date required')
    zone=ZoneInfo(timezone_id)
    end=datetime.combine(local_date,time(7),zone);start=datetime.combine(local_date-timedelta(days=1),time(7),zone)
    return start.astimezone(timezone.utc),end.astimezone(timezone.utc)


PROCESSES={
    'subjective_support_burden':('measurement','subjective_support_burden','synthetic-support-burden-item/1.0.0-r1'),
    'synthetic_eligibility_assessment':('measurement','synthetic_eligibility_assessment','SIM-REVIEW-01/1.0.0-r1'),
    'report_status_transform':('measurement','report_status_transform','REPORT-STATUS-01/1.0.0-r1')}


def process_seed_words(name,**identity):
    if name not in PROCESSES:raise ValueError('unknown DGP1.3 named process')
    ns,process,stream=PROCESSES[name]
    return seed_words(namespace=ns,process=process,stream=stream,**identity)
