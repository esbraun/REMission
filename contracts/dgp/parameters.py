"""Complete DGP v1.2.0 inventory. Values are synthetic engineering choices.

Rows are the authoritative parameter table, not runtime fallbacks. A consumer
must submit the complete table to validate_parameters before resolving a cell.
Normal second parameters are SDs; covariance entries are variances.
"""
import json
from copy import deepcopy

VERSION = "1.2.0"
REFERENCE = "docs/spec/dgp-reference.md"
CATALOG = "docs/spec/scenario-catalog.md"
DECISIONS = "docs/implementation/dgp-decisions.md"

# symbol | JSON value | unit | distribution/equation | parents | source
ROWS = r'''
start_day|-14|days|integer deterministic|clock|reference
end_day|84|days|integer deterministic|clock|reference
initial_day|-15|days|integer deterministic|clock|reference
visit_days|[0,21,42]|days|scheduled integer days|clock|reference
isi_days|[0,14,28,42,56,70,84]|days|scheduled integer days|clock|reference
recall_days|14|days|arithmetic mean of preceding nights|z|reference
visit_horizon|42|days|endpoint d+42|visit|reference
X_law|[0,1]|dimensionless|Normal(mean,SD)|none|reference
age_years_law|[18,80]|years|DiscreteUniform inclusive adults, descriptive only|none|choice
M_probability|0.5|probability|Bernoulli|none|reference
U_law|[0,1]|dimensionless|Normal(mean,SD), measured except S07|none|reference
b_law|[0,0.2]|dimensionless|Normal(mean,SD), prognostic only|none|reference
phase_offset_law|[0,20]|days|DiscreteUniform inclusive|none|reference
site_probabilities|[0.3333333333333333,0.3333333333333333,0.3333333333333333]|probability|Categorical sites 0,1,2|none|reference
leukemia_probabilities|[0.5,0.3,0.2]|probability|Categorical fictional strata L1,L2,L3; descriptive only|none|choice
therapy_probabilities|[0.6,0.4]|probability|Categorical fictional therapy T1,T2; descriptive only|none|choice
comorbidity_probability|0.3|probability|Bernoulli; descriptive/exclusion review|none|choice
preference_probabilities|[0.5,0.3,0.2]|probability|Categorical behavioral,medication,undecided|none|choice
prompt_preference_probability|0.8|probability|Bernoulli acceptance; availability constraint|none|choice
med_benefit_law|[1,0]|dimensionless|Normal multiplicative factor mean,SD; zero SD reference, 0.15 variation fixture|none|choice
med_harm_law|[1,0]|dimensionless|Normal multiplicative factor mean,SD; zero SD reference, 0.1 variation fixture|none|choice
site_intercepts|[0,0,0]|severity units|additive by site; site-shift sensitivity [0,0.15,-0.15]|site|choice
initial_L|[0,0,0]|dimensionless|point mass day -15|none|reference
initial_states|[0,0,0,0,0,0,0]|dimensionless|point mass z,B,C_A,C_B,R,T,cumulative_prompts day -15|none|reference
initial_living_outpatient|[1,1]|indicator|point mass alive,outpatient|none|choice
initial_taken|[0,0]|indicator|point mass MED_A,MED_B|none|choice
initial_quality|7|quality_points|missing-history initializer, paired missing flag always exported|none|reference
initial_n1_residual_sd|0.4|severity units|Normal stationary SD|none|catalog
phase_period|21|days|phase=(t+J) mod period|clock,J|reference
steroid_phase_days|[0,1,2,3]|days|membership indicator S|clock,J|reference
regimen_phase_days|[0,1,2,3,4,5,6]|days|replacement steroid window after shift_day|clock,J|reference
shift_day|42|days|abrupt boundary inclusive|clock|catalog
L_ar|0.6|dimensionless|coordinatewise L_previous coefficient|L_previous|reference
L_z|0.15|dimensionless|coordinatewise z_previous coefficient|z_previous|reference
L_steroid|0.25|dimensionless|coordinatewise S coefficient|S|reference
L_X|0.1|dimensionless|coordinatewise X coefficient|X|reference
L_U|0.1|dimensionless|coordinatewise U coefficient|U|reference
L_T|-0.1|dimensionless|coordinatewise assigned T_previous coefficient|T_previous|reference
L_covariance|[0.09,0.027,0.027,0.027,0.09,0.027,0.027,0.027,0.09]|variance units|MVNormal row-major 3x3 innovation covariance|none|reference
B_retention|0.995|dimensionless|B=min(1,retention*B_previous+gain*D*(1-B_previous))|B_previous,D|reference
B_gain|0.08|dimensionless|delivered program increment|B_previous,D|reference
carry_half_life|1|days|lambda=2**(-1/h), h=0 => lambda=0|C_previous,Taken|reference
rebound_enabled|0|indicator|zero unless enabled|Taken_previous,Taken|reference
R_ar|0.5|dimensionless|R_previous coefficient|R_previous|reference
R_stop|0.5|dimensionless|any previously taken drug stopped today indicator|Taken_previous,Taken|reference
z_ar|0.5|dimensionless|z_previous coefficient|z_previous|reference
z_X|0.2|dimensionless|X coefficient|X|reference
z_M|0|dimensionless|additional prognostic binary M coefficient, S05 0.2|M|choice
z_U|0.15|dimensionless|U coefficient|U|reference
z_L|0.15|dimensionless|mean current L coefficient|L|reference
z_steroid|0.2|dimensionless|S coefficient|S|reference
z_phase|0.1|dimensionless|sin(2*pi*(t+J)/21) coefficient|clock,J|reference
z_b|1|dimensionless|latent intercept coefficient; never assignment parent|b|reference
z_B|-0.15|dimensionless|skill coefficient|B|reference
z_med_A|-0.2|dimensionless|C_A coefficient times patient med benefit factor|C_A,med_benefit|reference
z_med_B|-0.12|dimensionless|C_B coefficient times patient med benefit factor|C_B,med_benefit|reference
z_med_A_modifier|0|dimensionless|C_A*(2M-1) coefficient; medication modifier fixture -0.25|C_A,M|reference
z_T|0|dimensionless|direct assigned behavioral T coefficient, only explicit reductions|T|choice
z_T_modifier|0|dimensionless|T*(2M-1) coefficient, only explicit reductions|T,M|choice
z_R|0.2|dimensionless|rebound coefficient|R|reference
z_prompt|-0.08|dimensionless|offered prompt A coefficient times delivery, not program T|A,delivered_prompt|reference
z_delayed_prompt|0|dimensionless|yesterday offered/delivered prompt coefficient, delayed-harm 0.15|A_previous,delivered_prompt_previous|reference
z_rescue|-0.1|dimensionless|fictional rescue same-night contribution|rescue|reference
z_nonlinear|0|dimensionless|L_pain**2-1 coefficient, nonlinear 0.15|L_pain|reference
z_innovation_sd|0.4|severity units|Normal(0,SD) or t3 scaled SD/sqrt(3)|none|reference
heavy_tail_enabled|0|indicator|replace severity innovation with t df3 scaled to same SD|none|reference
n1_rho|0.4|dimensionless|e_t=rho*e_prev+sqrt(1-rho**2)*N(0,0.4); replaces eta, not added twice|e_previous|catalog
Q_intercept|7|quality_points|clip(intercept+z_coef*z+error,0,10)|z|reference
Q_z|-2|quality_points|severity coefficient|z|reference
Q_sd|0.5|quality_points|Normal(0,SD)|none|reference
F_intercept|7|function_points|clip(intercept+z_coef*z+L_coef*mean(L)+med_coef*(C_A+C_B)*harm+error,0,10)|z,L,C_A,C_B,med_harm|reference
F_z|-1|function_points|severity coefficient|z|reference
F_L|-0.4|function_points|mean L coefficient|L|reference
F_med|-0.5|function_points|carryover sum coefficient times med harm factor|C_A,C_B,med_harm|reference
F_sd|0.5|function_points|Normal(0,SD)|none|reference
clinical_scale_bounds|[0,10]|quality_points|clip daily Q,F,fatigue|z,L|reference
fatigue_max|10|function_points|10-previous morning F, never next morning F|F_previous_morning|reference
nap_logit|[-1,0.15]|dimensionless|Bernoulli expit(intercept+slope*available fatigue)|F_previous_morning|choice
assignment_logit|[0,0.4,0.5,0.3]|dimensionless|expit(intercept+X*coef+mean(L)*coef+U*coef)|X,L,U|reference
assignment_floor|0.2|probability|clip assignment p to [floor,1-floor]|X,L,U|reference
randomized_probability|0.5|probability|Bernoulli known assignment probability|approved_protocol|reference
structural_zero_enabled|0|indicator|when enabled P(T=1)=0 if X>1, otherwise reference p|X|choice
structural_zero_X_cutoff|1|dimensionless|unsupported region X>cutoff|X|choice
delivery_logit|[1.5,-0.2]|dimensionless|Bernoulli expit(intercept+coef*mean(L)) conditional T=1|T,L|reference
override_probability|0|probability|Bernoulli; switch T proposal to usual_care, keep original assignment|assignment|choice
med_taken_probability|0.9|probability|Bernoulli conditional assigned medication|med_assignment|reference
rescue_enabled|0|indicator|rescue Bernoulli only when enabled|z_previous|reference
rescue_logit|[-3,0.5]|dimensionless|expit(intercept+coef*z_previous), evaluator mechanism only|z_previous|reference
prompt_probability|0.5|probability|MRT offer Bernoulli conditional available|available_history|reference
prompt_delivery_probability|1|probability|offered support delivered Bernoulli; missed scenario 0.8|A|choice
prompt_max_day|1|count|burden cap before assignment|available_history|reference
prompt_max_week|4|count|rolling seven-day cap before assignment|available_history|reference
prompt_window_days|7|days|rolling burden window|clock|reference
habituation_rate|0|dimensionless|z_prompt/(1+rate*cumulative delivered prompts); stress 0.2|past_delivered_prompts|reference
prompt_state_gain|0|dimensionless|additional B gain from prompts; reference zero, null must zero|A,delivered_prompt|choice
irregular_visit_enabled|0|indicator|extra visit Bernoulli outside scheduled visits|available_history|choice
irregular_visit_logit|[-4,0.2]|dimensionless|expit(intercept+coef*previous observed pain), no record => pain 0 plus missing flag|previous_observed_pain|choice
visit_jitter_days|[-2,-1,0,1,2]|days|Categorical actual-scheduled offset when irregular enabled; day0 fixed|schedule|choice
visit_jitter_probabilities|[0.1,0.2,0.4,0.2,0.1]|probability|Categorical jitter, clamp actual to [0,84], coalesce same-day visits|schedule|choice
recall_sd|0.2|severity units|Normal(0,SD) added to 14-night mean z|z_previous14|reference
item_cutpoints|[-1.5,-0.5,0.5,1.5]|severity units|P(item<=c)=expit(cutpoint-recall-offset)|recall|reference
item_offsets|[-0.3,-0.2,-0.1,0,0.1,0.2,0.3]|severity units|seven item offsets|item_index|reference
item_copula_rho|0|dimensionless|equicorrelated Gaussian copula uniforms; retains logistic ordinal margins|recall,common_item_error|choice
item_phase_offsets|[0,0,0,0,0,0,0]|severity units|offset increment times steroid indicator at assessment|S_assessment|choice
W_intercept|60|minutes|clip(intercept+slope*z,0,480)|z|reference
W_z|20|minutes|wake severity slope|z|reference
sleep_window|480|minutes|true sleep=window-true wake|z|reference
diary_sd|20|minutes|true sleep+Normal(0,SD); diary not clipped|true_sleep|reference
wearable_wake_bias|0.3|dimensionless|wearable sleep=true sleep+bias*W+noise then clip|true_sleep,W|reference
wearable_sd|15|minutes|Normal(0,SD)|none|reference
device_shift_minutes|0|minutes|added to wearable from shift_day; stress 30|clock|reference
missing_fraction|0|probability|target nonreport rate, calibration output required for MAR/MNAR|report_process|catalog
report_mode|0|code|0 complete,1 MCAR,2 MAR,3 MNAR,4 action_MNAR|report_process|choice
report_MAR_coefficients|[-0.4,-0.2]|dimensionless|logit observation a+c1*(10-prev observed Q)/2+c2*current observed pain|previous_observed_Q,current_observed_pain|reference
report_MNAR_quality|0.5|dimensionless|additional (current unobserved Q-7) coefficient|Q_current_unobserved|reference
report_action_quality|0|dimensionless|additional A_previous*(current unobserved Q-7); action_MNAR 1|A_previous,Q_current_unobserved|choice
delay_days|[0,1,3]|days|upload delay Categorical; report from 08:01 recording, wearable from 07:00 sync; separate keys|report_recording,wearable_sync|reference
delay_probabilities|[1,0,0]|probability|reference immediate; stress [0.7,0.2,0.1]|measurement|reference
death_enabled|0|indicator|absorbing death, applied before decisions|L,U|reference
admission_enabled|0|indicator|admission only alive/outpatient, assignments suspended|L,U|reference
death_logit|[-7,0.3,0.2]|dimensionless|expit(intercept+coef*mean(L)+coef*U)|L,U|reference
admission_logit|[-5,0.4,0.2]|dimensionless|expit(intercept+coef*mean(L)+coef*U)|L,U|reference
admission_days|7|days|discharge at admission day+7 unless dead; no assignment during admission|admission_time|reference
discontinuation_enabled|0|indicator|stop delivery after day21 while retaining assignment|L_day21|reference
discontinuation_day|21|days|decision once end of day21; D=0 from day22|clock|reference
discontinuation_logit|[-2,0.3]|dimensionless|expit(intercept+coef*mean(L_day21))|L_day21|reference
regimen_change_enabled|0|indicator|steroid window switches at shift_day|clock|reference
adverse_logit|[-5,0.4,0.3]|dimensionless|Bernoulli expit(intercept+coef*previous carry sum*harm+coef*available fatigue)|C_previous,F_previous_morning,med_harm|choice
adverse_enabled|0|indicator|reference off; enabled eligibility fixtures simulate observed review trigger|C_previous,F_previous_morning|choice
exclusion_probability|0.05|probability|baseline fictional medication exclusion, review not clinical recommendation|none|choice
stability_max_L|3|dimensionless|if any L>threshold remove experimental eligibility and require review|L|choice
n1_blocks|4|count|even blocks arranged equal probability AB/BA pairs|approved_protocol|choice
n1_active_days|7|days|active block duration|approved_protocol|reference
n1_washout_days|2|days|default washout, not clinical adequate-washout claim|approved_protocol|reference
n1_phase_mode|0|code|0 random AB/BA;1 A starts phase0/B phase9;2 balanced crossover start phases0,9 then swap next pair|clock,J|choice
n1_stop_mode|0|code|0 protocol complete;1 stop after two blocks if mean available Q<3 or observed adverse;2 stop after one block|available_history|choice
n1_stop_quality|3|quality_points|mean reported Q trigger after two complete blocks|available_history|choice
n1_min_blocks|2|count|at least one completed A and B; otherwise inconclusive|available_history|choice
n1_min_reporting_fraction|0.7|probability|minimum per-block reports for informative block|available_history|choice
response_day|28|days|behavioral response review; seven-item 14-day recall endpoint|ISI_day0,ISI_day28|choice
strategy_endpoint_day|84|days|continuing behavioral strategy final ISI|ISI_day84|choice
response_ISI_improvement|6|ISI_points|response if baseline ISI-current ISI>=threshold; engineering only|observed_ISI|choice
response_flip_probability|0|probability|independent label flip; noisy fixture 0.2, true response retained evaluator only|observed_response|choice
sparse_response_probability|0|probability|when >0 replace response classification with Bernoulli(p); sparse fixture 0.9|response_fixture|choice
escalation_B_gain|0.12|dimensionless|replace B_gain after assigned escalation, continue durable B|escalation_assignment,B_previous,D|choice
external_sizes|[150,180,220,250]|count|four independent 1:1 trials|study_id|reference
external_X_law|[0,1]|dimensionless|Normal(mean,SD); shifted [1,1]|none|reference
external_M_probability|0.5|probability|Bernoulli; shifted 0.8|none|reference
external_shift_SE|0|source_SE|requested marginal source contrast shift; stresses1,2|independent_source_pilot|catalog
external_reverse_sign|0|indicator|target source contrast=-reference source contrast|independent_source_truth|catalog
external_modifier_export|1|indicator|source M omitted in S11 only|M|catalog
export_U|1|indicator|remove U from learner export in S07 only|U|reference
calibration_sample|200000|count|independent nuisance calibration population before development|calibration_namespace|choice
calibration_bracket|[-30,30]|logit|bisection bracket for report/event intercept|nuisance_covariates|choice
calibration_rate_tolerance|0.0001|probability|absolute numerical mean-rate tolerance|calibration_sample|choice
calibration_max_iterations|100|count|bisection cap; infeasible/cap => blocked, no substitution|solver|choice
external_coefficient_bracket|[-5,5]|severity units|bisection direct behavioral z_T source shift, base z_T=0|source_intervention_rollouts|choice
external_contrast_tolerance|0.005|ISI_points|absolute achieved-target difference plus reported truth MCSE|source_intervention_rollouts|choice
source_SE_pilot_replicates|1000|count|independent n200 1:1 trials, freeze sqrt(mean(SE**2))|pilot_namespace|choice
source_SE_pilot_n|200|count|pilot study size, equal arms|pilot_namespace|choice
truth_ISI_MCSE|0.05|ISI_points|absolute MCSE maximum|independent_batches|catalog
truth_quality_MCSE|0.01|quality_points|absolute MCSE maximum|independent_batches|catalog
truth_relative_MCSE|0.1|dimensionless|also <=fraction*smallest estimator SE|pilot_then_final_SE|catalog
truth_batch_size|10000|count|independent paired rollout batches|truth_namespace|choice
truth_max_batches|1000|count|compute cap; exhausted precision => inconclusive|truth_namespace|choice
meaningful_ISI|3|ISI_points|synthetic meaningful improvement threshold|decision_contract|choice
meaningful_quality|0.5|quality_points|synthetic meaningful improvement threshold|decision_contract|choice
minimum_overlap|0.05|probability|comparative claim requires all target actions >=threshold|observed_assignment_support|choice
maximum_weight|20|dimensionless|abstain if declared target weight exceeds threshold; no clipping to identification|propensities|choice
minimum_effective_sample|20|count|support precision gate for ranking, not clinical precision|weights|choice
maximum_ISI_interval_width|6|ISI_points|claim precision gate|accepted_fit|choice
tail_probability_MCSE|0.0025|probability|claim precision gate|posterior_tail|choice
probability_cutoffs|[0.95,0.975,0.99,0.995]|probability|development only select least stringent satisfying exact clinic-wide null bound|development_complete_null_runs|catalog
false_claim_upper|0.05|probability|one-sided95% exact upper bound, all locked null development cells|development_null_runs|catalog
MNAR_sensitivity_quality|[-0.5,0,0.5]|dimensionless|unobserved quality coefficient sensitivity grid|report_model|choice
MNAR_sensitivity_action|[-1,0,1]|dimensionless|action-quality coefficient sensitivity grid, separately reported|report_model|choice
bandit_bounds|[0.1,0.9]|probability|feasible final two-action assignment bounds|availability|choice
bandit_probability_MCSE|0.005|probability|otherwise fixed support fallback|policy_draws|choice
smoke_sizes|[100,6,30,30]|count|historical,prospective,external1,external2|preset|choice
demo_sizes|[2000,60]|count|historical,prospective|preset|reference
repetitions|[5,200,1000,1000,2000]|count|smoke,development,recovery,policy,null|protocol|catalog
root_seed|20261020|integer|explicit root entropy for seed derivation v1|none|choice
fault_logged_propensity|0.5|probability|S32 persist this p while executing fault_executed_propensity|fault_fixture|choice
fault_executed_propensity|0.8|probability|S32 wrong-propensity actual Bernoulli p, must be rejected|fault_fixture|choice
fault_action_lower_bounds|[0.6,0.6]|probability|S32 two-action bounds sum>1, must be rejected|fault_fixture|choice
'''


def reference_parameters() -> dict:
    """Explicit authoring artifact; never merge this into an incomplete request."""
    records = {}
    for row in ROWS.strip().splitlines():
        symbol, value, unit, distribution, parents, source = row.split("|")
        if symbol in records:
            raise ValueError(f"duplicate parameter {symbol}")
        records[symbol] = {"value": json.loads(value), "unit": unit,
                           "distribution": distribution, "parents": parents.split(","),
                           "applicability": "reference and cells explicitly overriding this symbol",
                           "provenance": "synthetic_engineering",
                           "source": {"reference": REFERENCE, "catalog": CATALOG, "choice": DECISIONS}[source],
                           "source_kind": source}
    from .timing import TEMPORAL
    return {"version": VERSION, "synthetic": True, "temporal_contract": deepcopy(TEMPORAL), "parameters": records}


def validate_parameters(manifest: dict) -> dict:
    """Require the entire frozen table including metadata. No unknown/missing keys."""
    expected = reference_parameters()
    if json.dumps(manifest, sort_keys=True) != json.dumps(expected, sort_keys=True):
        supplied = manifest.get("parameters", {}) if isinstance(manifest, dict) else {}
        missing = sorted(set(expected["parameters"]) - set(supplied))
        raise ValueError(f"DGP v{VERSION} table mismatch; missing={missing}; changes require a reviewed new version")
    # Return isolated values so a resolved cell cannot mutate the frozen table.
    return deepcopy(manifest)
