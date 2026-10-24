"""Saved joint posterior prediction entry. SOURCE prepared, execution OFF.

No fit/model import, RNG or conditioning on postfit outcomes. Reference numeric
prediction remains unchanged. Future independent parent supervision must veto
blocked native work and reserve collection/ingestion/reaping within 600s.
"""
import argparse
import math
import os
from pathlib import Path
import sys
import time


class Budget:
    def __init__(self,origin_epoch,*,clock=time.time,monotonic=time.monotonic):
        self.clock=clock;self.monotonic=monotonic
        if type(origin_epoch) not in (int,float) or not math.isfinite(origin_epoch):
            raise ValueError('S2_prediction_common_operation_origin_required')
        age=clock()-origin_epoch
        if not 0<=age<570:raise ValueError('S2_prediction_operation_origin_expired_or_future')
        self.origin=origin_epoch;self.start=monotonic();self.remaining=570-age;self.segment_start=None
    def check(self):
        if self.clock()>=self.origin+570 or self.monotonic()-self.start>=self.remaining:
            raise TimeoutError('S2_prediction_absolute_work_deadline')
        if self.segment_start is not None and self.monotonic()-self.segment_start>=300:
            raise TimeoutError('S2_prediction_segment_deadline')
    def segment(self):
        self.check()
        if self.segment_start is not None:raise ValueError('S2_prediction_segment_cannot_reset')
        self.segment_start=self.monotonic()


def reference_predict(module,request,arrays,patients,*,check):
    """Stage veto around actual numerical calls, without modifying their values.

    Dedicated one-job worker only. A blocked call still needs the independently
    owned parent watchdog; checks here do not claim syscall preemption.
    """
    names=('expected_quality','indicator_diagnostics');original={n:getattr(module,n) for n in names}
    def checked(fn):
        def call(*args,**kwargs):
            check();value=fn(*args,**kwargs);check();return value
        return call
    try:
        for name in names:setattr(module,name,checked(original[name]))
        check();value=module.predict(request,arrays,patients);check()
        return value
    finally:
        for name in names:setattr(module,name,original[name])


def _qualified_predict(product,posterior,out,*,budget,trusted,progress):
    from contracts.domain.analysis import canonical,sha
    from contracts.domain.support_s2_saved import (SavedPredictionResult,CONFIG_REF,RESULT_CAP,
        validate_saved_result,PredictionLaunch)
    from .support_s2_artifacts import load_joint
    from .support_s2_worker import publish
    launch=PredictionLaunch.model_validate_json(canonical(trusted))
    if (launch.attempt_id!=product.attempt_id or launch.input_sha256!=sha(product.model_dump(mode='json'))):
        raise ValueError('S2_prediction_trusted_launch_input_mismatch')
    sequence=0
    def stage(name):
        nonlocal sequence
        budget.check();sequence+=1
        progress(dict(schema='s2-saved-prediction-progress-v1',attempt_id=product.attempt_id,
            input_sha256=launch.input_sha256,sequence=sequence,stage=name))
        budget.check()
    binary=None;candidate=None;status='fallback';reason='current_mask_not_binary';probability=.5
    try:
        stage('preparing')
        if product.context.allowed_actions==('support_prompt','no_prompt'):
            stage('validating_saved_posterior')
            arrays,patients,binary=load_joint(posterior,product.fit.product,product.fit.result.semantics,check=budget.check)
            import methods.support.s2_prediction as algorithm
            stage('predicting');budget.segment()
            candidate,_,_=reference_predict(algorithm,product.request,arrays,patients,check=budget.check)
            # Full candidate contains primary + ALL nine cells and original
            # chain-aware diagnostics. No invalid draw/cell is discarded.
            if candidate.status=='candidate_ready':status='candidate_ready';reason='candidate_evidence_only';probability=candidate.probability
            else:reason='numerical_or_precision_unready'
            del arrays
        stage('summarizing')
    except TimeoutError:status='failed';reason='deadline_exceeded';probability=.5;candidate=None
    except ValueError:status='failed';reason='worker_refused';probability=.5;candidate=None
    result=SavedPredictionResult.model_validate_json(canonical(dict(schema_version='s2-saved-prediction-source-1.0.0',
        kind='poc_support_s2_saved_prediction_result',attempt_id=product.attempt_id,input_sha256=launch.input_sha256,
        context_reference=product.context.reference.model_dump(),fit_collection_reference=product.fit.collection_reference.model_dump(),
        configuration=CONFIG_REF,launch=launch.model_dump(mode='json'),binary=None if binary is None else binary.model_dump(mode='json'),
        candidate=None if candidate is None else candidate.model_dump(mode='json'),status=status,reason=reason,
        probability=probability,serving_authority=False)))
    # Synthetic clinical cutoff and host operation wall time are different
    # clocks. Foundation rechecks the ACTUAL current clinical context/expiry at
    # ingestion. Worker validates its frozen context and the absolute budget.
    validate_saved_result(result,product,trusted,at=product.context.decision.cutoff)
    budget.check();publish(out/'result.json',result.model_dump(mode='json'),RESULT_CAP)
    return result


def run(input_path,posterior,out,*,origin_epoch=None,trusted=None,progress=None):
    from contracts.domain.support_s2_saved import require_executable
    require_executable()  # before any private stat/read, environment or calls
    from .support_s2_worker import construction_policy,strict_json
    construction_policy(os.environ)
    from contracts.domain.analysis import canonical
    from contracts.domain.support_s2_saved import SavedPredictionInput,INPUT_CAP
    budget=Budget(origin_epoch)
    if (input_path.is_symlink() or not input_path.is_file() or input_path.stat().st_size>INPUT_CAP
            or posterior.is_symlink() or not posterior.is_dir() or out.is_symlink() or not out.is_dir()):
        raise ValueError('S2_prediction_owned_bounded_input_posterior_output_required')
    with input_path.open('rb') as stream:raw=stream.read(INPUT_CAP+1)
    if len(raw)>INPUT_CAP:raise ValueError('S2_prediction_input_cap')
    product=SavedPredictionInput.model_validate_json(canonical(strict_json(raw)))
    if trusted is None or progress is None:raise ValueError('S2_prediction_owned_launch_supervisor_required')
    return _qualified_predict(product,posterior,out,budget=budget,trusted=trusted,progress=progress)


def main():
    parser=argparse.ArgumentParser()
    for name in ('input','posterior','output'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args()
    try:run(args.input,args.posterior,args.output)
    except Exception:return 1  # bounded refusal; no private traceback stream
    return 0


if __name__=='__main__':sys.exit(main())
