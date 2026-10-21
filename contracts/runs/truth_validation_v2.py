"""Version-specific binding plus frozen accepted scientific checks.

The v1 parser remains byte-exact. Only v2 function/type names and the request
binding version differ; source comparison prevents scientific policy drift.
"""
from contracts.domain.estimands import InterruptionResult
from contracts.domain.evaluation import TruthResult
from contracts.dgp.truth import truth_status
from .common import canonical, sha256
from .private import FixtureAnswer, SystemAnswer, ParameterAnswer, AnalyticAnswer
from .private_v2 import TruthRequestV2, TruthResponseV2


def validate_truth_response_v2(request: TruthRequestV2, response: TruthResponseV2, *, qualified_probability=None):
    """Called after out-of-band producer/run and all artifact hashes are verified."""
    if response.run_id!=request.run_id or response.request.id!=request.id or response.request.version!='2.0.0' or response.request.sha256!=sha256(canonical(request.model_dump(mode='json'))):
        raise ValueError('result/request binding mismatch')
    if response.runtime!=request.runtime or response.source_commit!=request.source_commit or response.execution!=request.execution:
        raise ValueError('evaluator runtime/source/execution provenance changed')
    if response.status=='capped' and request.method!='numerical':raise ValueError('analytic/deterministic result cannot consume a numerical truth batch cap')
    result=response.result;target=request.target
    if target.kind=='clinical' and target.estimand.estimand_id=='EST-INT' and result is not None:
        if not isinstance(result,InterruptionResult) or (result.intervention.action,result.comparator.action)!=(target.estimand.intervention,target.estimand.comparator):raise ValueError('EST-INT requires its separate intervention vector, including unresolved results')
        if any(p.status=='computed' for p in response.interruption_precision):
            if request.method!='numerical' or qualified_probability is None:raise ValueError('partial/undefined vectors cannot bypass authenticated component qualification')
            from .probability import COMPONENTS
            precision={p.component:p for p in response.interruption_precision}
            for index,component in enumerate(COMPONENTS):
                p=precision[component]
                if p.status!='computed':continue
                if p.method=='numerical' and p.matched_pilot!=request.comparator_pilot:raise ValueError('reported probability matched pilot differs from authenticated request plan')
                arm,name=component.split('.')
                if (p.method!='numerical')!=(component in qualified_probability['structural_proofs']):raise ValueError('structural versus numerical component method mismatch')
                if abs(getattr(getattr(result,arm),name)-float(qualified_probability['mean'][index]))>1e-12 or abs(p.numerical_standard_error-float(qualified_probability['mcse'][index]))>1e-12 or abs(p.smallest_estimator_se-float(qualified_probability['matched_se'][index]))>1e-12:raise ValueError('reported probability component differs from qualified files')
            if response.batches!=qualified_probability['batches']:raise ValueError('reported probability batch count differs')
            for index,arm_name in enumerate(('intervention','comparator')):
                arm=getattr(result,arm_name);actual=qualified_probability['conditional_isi'][index];p=precision[arm_name+'.conditional_isi']
                for name,times in qualified_probability['event_times'][arm_name].items():
                    if sorted(getattr(arm,name))!=times:raise ValueError('reported event-time multiset differs from all qualified day42 paths')
                if arm.conditional_isi.numerator_count!=actual['count'] or arm.conditional_isi.denominator_count!=response.batches*10000:raise ValueError('conditional ISI must use its own actual eligible count and full denominator, including partial vectors')
                estimate=arm.conditional_isi.isi
                if estimate.status=='estimated':
                    if actual['status']!='computed' or abs(estimate.value-actual['value'])>1e-12:raise ValueError('reported symptom mean differs from qualified eligible paths')
                    if estimate.standard_error is not None and abs(estimate.standard_error-actual['mcse'])>1e-12:raise ValueError('nested symptom uncertainty conflicts with qualified MCSE')
                    if estimate.interval is not None:raise ValueError('no independently qualified symptom interval method; retain interval=None')
                if p.status=='computed':
                    if estimate.status!='estimated' or actual['status']!='computed' or abs(p.numerical_standard_error-actual['mcse'])>1e-12:raise ValueError('computed conditional ISI needs its actual eligible mean and batch uncertainty')
                    matched=qualified_probability['symptom_matched_se'].get(p.component)
                    if matched is None or abs(p.smallest_estimator_se-matched)>1e-12:raise ValueError('claimed symptom SE differs from its authenticated raw pilot and actual tighter comparison')
                    if target.truth_kind=='observed_history_conditional_average':
                        if response.conditional_accuracy is None:raise ValueError('computed conditional ISI needs separate symptom accuracy evidence')
                        from .probability import SymptomPilotQualification
                        qualification=qualified_probability.get('symptom_qualifications',{}).get(p.component)
                        levels=response.conditional_accuracy.particle_levels
                        if (not isinstance(qualification,SymptomPilotQualification) or levels!=qualification.particle_levels or levels[-1]!=qualification.final_particle_level
                            or levels!=qualified_probability.get('probability_truth_particle_levels') or levels[-1]!=qualified_probability.get('probability_truth_final_particle_level')):
                            raise ValueError('symptom accuracy must match authenticated symptom pilot and probability truth particle levels/final level')
                        response.conditional_accuracy.require_accuracy(min(.05,.1*matched))
    if response.status!='computed':return
    if target.kind=='clinical':
        if target.estimand.estimand_id=='EST-INT':
            if not isinstance(result,InterruptionResult) or (result.intervention.action,result.comparator.action)!=(target.estimand.intervention,target.estimand.comparator):raise ValueError('EST-INT requires its unordered separate intervention vector')
            return
        if not isinstance(result,TruthResult) or result.estimand.id!=target.estimand.estimand_id or result.estimand.version!=target.estimand.estimand_version or result.estimand.sha256!=sha256(canonical(target.estimand.model_dump(mode='json'))) or result.dgp!=request.bindings.dgp or result.method!=request.method:
            raise ValueError('scalar truth target/DGP/method mismatch')
        if result.estimate.unit!=target.estimand.unit:raise ValueError('truth outcome unit mismatch')
        if not any(result.seed.namespace=='truth' and (result.seed.protocol,result.seed.scenario,result.seed.replicate,result.seed.patient,result.seed.time_index,result.seed.process)==(key.protocol,key.scenario,key.replicate,key.patient,key.time_index,key.process) for key in request.seeds):
            raise ValueError('canonical truth seed does not match an authorized full key')
        if result.method=='numerical':
            if result.draws!=response.batches*10000 or truth_status(result.numerical_standard_error,request.smallest_estimator_se,result.estimate.unit,batches=response.batches,cap=1000)!='resolved':
                raise ValueError('numeric truth has not achieved both absolute and matched-SE precision')
            if target.truth_kind=='observed_history_conditional_average':
                if response.conditional_accuracy is None:raise ValueError('rollout MCSE alone cannot resolve conditional particle bias')
                response.conditional_accuracy.require_accuracy(min(.05 if result.estimate.unit=='ISI_points' else .01,.1*request.smallest_estimator_se))
    elif target.kind=='fixture':
        if not isinstance(result,FixtureAnswer) or result.estimand!=target.estimand:raise ValueError('fixture answer mismatch')
    elif target.kind=='system':
        if not isinstance(result,SystemAnswer) or result.estimand!=target.estimand or result.fault!=target.expected_fault:raise ValueError('fault answer mismatch')
    elif target.kind=='parameter':
        if not isinstance(result,ParameterAnswer) or result.symbol!=target.symbol or result.parameters!=target.parameters:raise ValueError('structural parameter answer mismatch')
    elif not isinstance(result,AnalyticAnswer) or (result.fixture,result.quantity)!=(target.fixture,target.quantity):
        raise ValueError('native analytic fixture answer mismatch')
