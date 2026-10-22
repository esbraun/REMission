"""Doubled lifecycle/failure controls; no model, sampling or genuine fit evidence."""
from contextlib import ExitStack, nullcontext
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch

import numpy as np
from services.learner import cohort_worker as worker
from tests.contracts.test_cohort_qualification import qualified_input


class StructuralTrace(dict):
    def __init__(self):super().__init__(posterior=object())
    def to_netcdf(self,path,**kwargs):Path(path).write_text('STRUCTURAL-NO-FIT')


class WorkerLifecycleControls(unittest.TestCase):
    def run_doubled(self,directory,*,failed_patient=None,gate='integration',fit_acceptance=(True,)):
        product=qualified_input();patients=[m.patient_id for m in product.cohort.manifest.members]
        counts=dict(effect=0,diagnostics=0)
        def integrate(*args,**kwargs):
            index=counts['effect'];counts['effect']+=1
            return (None if gate=='integration' and failed_patient==index else np.zeros((4,4))),dict(status='accepted')
        def diagnostics(trace,**kwargs):
            if kwargs:
                return dict(accepted=not(gate=='mcmc' and failed_patient==counts['effect']-1))
            index=counts['diagnostics'];counts['diagnostics']+=1
            return dict(accepted=fit_acceptance[min(index,len(fit_acceptance)-1)])
        def sample(*args,**kwargs):
            kwargs['on_compile'](dict(index=1,structural_no_fit=True))
            return StructuralTrace()
        with ExitStack() as stack:
            stack.enter_context(patch.dict(os.environ,dict(REMISSION_LEARNER_IMAGE='sha256:'+'1'*64,
                REMISSION_SOURCE_COMMIT='2'*40,REMISSION_COHORT_REVIEWED_LEARNER_IMAGE='sha256:'+'1'*64,
                REMISSION_COHORT_REVIEWED_SOURCE_COMMIT='2'*40)))
            replacements=dict(cohort_inputs=lambda cohort:[(p,dict(day=14,c=[0.],e=[0.],
                record_ids=[],likelihood_blocks=[],deliveries=0,taken=0,arms=[])) for p in patients],
                build_cohort=MagicMock(),owned_callables=lambda *a,**k:nullcontext(),
                _observed=lambda *a,**k:(np.zeros((4,4)),np.zeros((4,4))),
                diagnostics=diagnostics,patient_parameters=lambda *a:object(),integrate=integrate,
                predictive=lambda *a,**k:np.zeros((4,4)))
            for name,value in replacements.items():stack.enter_context(patch.object(worker,name,value))
            stack.enter_context(patch.object(worker.pm,'sample_prior_predictive',return_value={'prior':object()}))
            sampler=stack.enter_context(patch.object(worker,'sample',side_effect=sample))
            result=worker.run(product,directory)
            return result,sampler.call_args_list

    def test_any_patient_gate_failure_suppresses_every_effect(self):
        for gate in ('integration','mcmc'):
            for index in range(12):
                with self.subTest(gate=gate,index=index),tempfile.TemporaryDirectory() as directory:
                    result,_=self.run_doubled(directory,failed_patient=index,gate=gate)
                    self.assertEqual(result['status'],'abstained',result['reason'])
                    self.assertTrue(all(p['effect'] is None and p['status']=='abstained' for p in result['patients']))
                    self.assertTrue(Path(directory,'failure.log').is_file())

    def test_worker_extension_only_after_diagnostic_failure_and_original_seed(self):
        for decisions,expected in [((True,),1),((False,True),2),((False,False),2)]:
            with self.subTest(decisions=decisions),tempfile.TemporaryDirectory() as directory:
                result,calls=self.run_doubled(directory,fit_acceptance=decisions)
                self.assertEqual(len(calls),expected)
                for index,call in enumerate(calls):
                    self.assertEqual(call.args[1],qualified_input().numerical_seeds.nuts+index)
                    self.assertEqual(call.kwargs['extended'],bool(index))
                self.assertEqual(result['status'],'completed' if decisions[-1] else 'abstained')

    def test_unconfigured_runtime_rejects_before_data_or_model(self):
        with tempfile.TemporaryDirectory() as directory,patch.dict(os.environ,{},clear=True), \
                patch.object(worker,'build_cohort',side_effect=AssertionError('No model')), \
                patch.object(worker,'cohort_inputs',side_effect=AssertionError('No data work')):
            result=worker.run(qualified_input(),directory)
            self.assertEqual(result['status'],'failed')
            self.assertTrue(all(p['effect'] is None for p in result['patients']))


if __name__=='__main__':unittest.main()
