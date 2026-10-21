"""Pure wire fixtures; these tests perform no calibration or truth simulation."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

from fixtures import CUTOFF, ROOT, artifact, full_key, load, setup
from contracts.dgp.calibration import calibration_request
from contracts.runs.common import Authority, canonical, sha256
from contracts.runs.private import CalibrationArtifact, CELLS, ConditionalAccuracy, TruthRequest, TruthResponse, validate_truth_response
from contracts.runs.private_admission import verify_calibration, verify_truth


class EvaluatorContracts(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);self.data=setup(self.root)
        self.producer=dict(id='contract-fixture-evaluator',version='1.0.0',role='contract_fixture')
        self.pilot=artifact(self.root,'pilot','reports/pilot.json',dict(kind='contract_fixture_only',computed=False),'evaluator_result')
        self.authority=load(Authority,{**self.data['authority'].model_dump(mode='json'),'producer':self.producer})

    def tearDown(self):self.temp.cleanup()

    def request(self,*,cell='S01.reference.n60',method='numerical',truth_kind='marginal_contrast'):
        rows=json.loads((ROOT/'tests/contracts/fixtures/estimands-v1.json').read_text(encoding='utf-8'))['contracts']
        estimand=copy.deepcopy(next(row for row in rows if row['estimand_id']==CELLS[cell]['estimand']))
        estimand.update(observation_cutoff=CUTOFF,time_zero=CUTOFF,intervention=CELLS[cell]['intervention'],comparator=CELLS[cell]['comparator'])
        data=dict(schema_version='1.0.0',synthetic=True,kind='evaluator_request',contract_version='1.0.0',id='request-one',run_id=self.data['run'].run_id,
            run_manifest=self.data['export'].run_manifest.model_dump(mode='json'),producer=self.producer,execution='contract_fixture',source_commit=self.data['run'].source_commit,
            runtime=self.data['run'].runtime.model_dump(mode='json'),bindings=self.data['run'].bindings.model_dump(mode='json'),unit_id='unit-one',cell_id=cell,
            target=dict(kind='clinical',truth_kind=truth_kind,estimand=estimand),information_set='structural_population',method=method,cutoff=CUTOFF,
            patient_id=None,observed_history=None,generating_policy=None,coupling=None,seeds=[full_key(namespace='truth',scenario=cell)],batch_size=10000,batch_cap=1000,
            comparator_pilot=self.pilot if method=='numerical' else None,smallest_estimator_se=.1 if method=='numerical' else None)
        return data

    def response(self,request,*,status='computed',result=None):
        request=load(TruthRequest,request) if isinstance(request,dict) else request
        if result is None and status=='computed':
            seed=request.seeds[0]
            result=dict(schema_version='1.0.0',synthetic=True,kind='truth_result',estimand=dict(id=request.target.estimand.estimand_id,version='1.0.0',sha256=sha256(canonical(request.target.estimand.model_dump(mode='json')))),
                method=request.method,estimate=dict(status='estimated',value=-1.0,unit=request.target.estimand.unit,standard_error=None,interval=None),numerical_standard_error=.005 if request.method=='numerical' else 0.0,
                information_set='evaluator_only_structural_system',privileged_information=True,dgp=request.bindings.dgp.model_dump(mode='json'),
                seed=dict(namespace='truth',protocol=seed.protocol,scenario=seed.scenario,replicate=seed.replicate,patient=seed.patient,time_index=seed.time_index,process=seed.process),
                draws=10000 if request.method=='numerical' else 0,independent_implementation=dict(id='contract-fixture-not-executed',version='1.0.0',sha256='a'*64))
        report=artifact(self.root,'report','reports/result.json',result or dict(status=status,fixture=True),'evaluator_result')
        return dict(schema_version='1.0.0',synthetic=True,kind='evaluator_response',contract_version='1.0.0',id='response-one',run_id=request.run_id,
            request=dict(id=request.id,version='1.0.0',sha256=sha256(canonical(request.model_dump(mode='json')))),producer=self.producer,execution='contract_fixture',source_commit=request.source_commit,runtime=request.runtime.model_dump(mode='json'),
            status=status,reason=None if status=='computed' else 'Pure contract fixture; computation not executed',result=result,batches=1000 if status=='capped' else 1 if request.method=='numerical' else 0,
            report=report,diagnostics=[],conditional_accuracy=None,interruption_precision=[])

    def test_numeric_scalar_bound_to_target_seed_pilot_runtime_and_both_precision_limits(self):
        request=load(TruthRequest,self.request());response=load(TruthResponse,self.response(request))
        validate_truth_response(request,response)
        raw_request=canonical(request.model_dump(mode='json'));raw_response=canonical(response.model_dump(mode='json'))
        verify_truth(raw_request,raw_response,self.root,request_sha256=sha256(raw_request),response_sha256=sha256(raw_response),evaluator=self.authority)
        for change in [('numerical_standard_error',.011),('draws',9999),('method','analytic')]:
            data=response.model_dump(mode='json');data['result'][change[0]]=change[1]
            with self.subTest(change=change),self.assertRaises(ValueError):validate_truth_response(request,load(TruthResponse,data))
        data=request.model_dump(mode='json');data['smallest_estimator_se']=0.0;zero=load(TruthRequest,data)
        response=self.response(zero)
        with self.assertRaises(ValueError):validate_truth_response(zero,load(TruthResponse,response))
        data=request.model_dump(mode='json');data['comparator_pilot']=None
        with self.assertRaises(ValueError):load(TruthRequest,data)
        data=request.model_dump(mode='json');data['target']['estimand']['outcome']='daily_sleep_quality'
        with self.assertRaises(ValueError):load(TruthRequest,data)

    def test_pending_failed_undefined_capped_are_explicit_not_success(self):
        request=load(TruthRequest,self.request())
        for status in ['pending','failed','undefined','capped']:
            response=self.response(request,status=status)
            self.assertEqual(load(TruthResponse,response).status,status)
            bad=copy.deepcopy(response);bad['reason']=None
            with self.assertRaises(ValueError):load(TruthResponse,bad)
            bad=copy.deepcopy(response);bad['result']=self.response(request)['result']
            with self.assertRaises(ValueError):load(TruthResponse,bad)
        bad=self.response(request,status='capped');bad['batches']=999
        with self.assertRaises(ValueError):load(TruthResponse,bad)
        fixture_policy=self.authority.model_dump(mode='json');fixture_policy['allow_contract_fixture']=False
        raw_request=canonical(request.model_dump(mode='json'));response=load(TruthResponse,self.response(request));raw_response=canonical(response.model_dump(mode='json'))
        with self.assertRaises(ValueError):verify_truth(raw_request,raw_response,self.root,request_sha256=sha256(raw_request),response_sha256=sha256(raw_response),evaluator=load(Authority,fixture_policy))

    def test_conditional_history_is_strict_and_particle_refinement_not_just_rollout_mcse(self):
        data=self.request(truth_kind='observed_history_conditional_average');data.update(information_set='available_observed_history',patient_id='SYN-02',observed_history=self.data['export'].partitions[0].history.model_dump(mode='json'))
        request=load(TruthRequest,data)
        response=self.response(request)
        with self.assertRaises(ValueError):validate_truth_response(request,load(TruthResponse,response))
        response['conditional_accuracy']=dict(particle_levels=[1024,4096,16384],filters_per_level=32,successive_differences=[.0001,.0001],paired_standard_errors=[.0001,.0001],quadrature_change=.0001,within_filter_mcse=.0001,between_filter_mcse=.0001,independent_reduced_checks=[self.pilot])
        validate_truth_response(request,load(TruthResponse,response))
        response['conditional_accuracy']['particle_levels']=[1024,65536]
        with self.assertRaises(ValueError):validate_truth_response(request,load(TruthResponse,response))
        data['information_set']='realized_latent_oracle'
        with self.assertRaises(ValueError):load(TruthRequest,data)

    def test_conditioning_file_must_be_strict_projected_history_not_future_lineage(self):
        from contracts.domain.boundaries import ObservedHistory
        from services.foundation.store import instant
        data=self.request(truth_kind='observed_history_conditional_average')
        original=self.data['export'].partitions[0].history
        full=ObservedHistory.model_validate_json((self.root/original.path).read_bytes())
        projection=full.project(instant(CUTOFF))
        self.assertEqual(projection.records,[])
        data.update(information_set='available_observed_history',patient_id=full.patient_id,observed_history=artifact(self.root,'strict-H','conditioning/H.json',projection.model_dump(mode='json'),'observed'))
        request=load(TruthRequest,data);response=self.response(request,status='pending')
        def verify(req,res):
            reqraw=canonical(req.model_dump(mode='json'));resraw=canonical(res)
            return verify_truth(reqraw,resraw,self.root,request_sha256=sha256(reqraw),response_sha256=sha256(resraw),evaluator=self.authority)
        verify(request,response)
        # A future correction/value may exist in retained lineage, but cannot
        # become H_t merely because its enclosing file has a trusted hash.
        data['observed_history']=original.model_dump(mode='json');request=load(TruthRequest,data)
        with self.assertRaises(ValueError):verify(request,self.response(request,status='pending'))

    def test_catalog_fixture_system_and_standalone_native_quantities_remain_distinct(self):
        data=self.request();bindings=data['bindings']
        for cell,kind in [('S03.constant.n60','fixture'),('S12.IPD_and_summary.n60','system')]:
            catalog=CELLS[cell];request=copy.deepcopy(data);request.update(cell_id=cell,method='analytic' if kind=='fixture' else 'deterministic_check',information_set='deterministic_fixture',comparator_pilot=None,smallest_estimator_se=None,seeds=[full_key(namespace='truth',scenario=cell)])
            if kind=='fixture':
                request['target']=dict(kind=kind,truth_kind='marginal_contrast',estimand=catalog['estimand'],outcome='linear_Y',unit='fixture_points',intervention=catalog['intervention'],comparator=catalog['comparator'],fixture_manifest=bindings['analytic_fixtures'])
                answer=dict(kind='fixture_answer',estimand=catalog['estimand'],unit='fixture_points',value=-1.0)
            else:
                request['target']=dict(kind=kind,estimand=catalog['estimand'],outcome='rejection',unit='none',expected_fault=catalog['variant'])
                answer=dict(kind='system_answer',estimand=catalog['estimand'],fault=catalog['variant'],detected=True)
            parsed=load(TruthRequest,request);response=self.response(parsed,result=answer);validate_truth_response(parsed,load(TruthResponse,response))
            if kind=='system':
                response['result']['detected']=False
                with self.assertRaises(ValueError):load(TruthResponse,response)
            else:
                request['target']['unit']='ISI_points'
                with self.assertRaises(ValueError):load(TruthRequest,request)
        request=copy.deepcopy(data);request.update(cell_id=None,unit_id=None,method='analytic',information_set='deterministic_fixture',comparator_pilot=None,smallest_estimator_se=None,seeds=[full_key(namespace='truth',scenario='normal')],
            target=dict(kind='analytic_fixture',fixture='normal',quantity='truth_mean',unit='fixture_native_units',fixture_manifest=bindings['analytic_fixtures']))
        parsed=load(TruthRequest,request);answer=dict(kind='analytic_fixture_answer',fixture='normal',quantity='truth_mean',unit='fixture_native_units',value=40/81)
        validate_truth_response(parsed,load(TruthResponse,self.response(parsed,result=answer)))
        request['cell_id']='S03.constant.n60'
        with self.assertRaises(ValueError):load(TruthRequest,request)

    def test_estint_retains_per_arm_vector_and_unresolved_probability_precision(self):
        cell=next(key for key,value in CELLS.items() if value['estimand']=='EST-INT')
        request=load(TruthRequest,self.request(cell=cell))
        def arm(action,n):return dict(action=action,survival_day42=.9,admission_by_day42=.2,alive_outpatient_day42=n/10,
            conditional_isi=dict(numerator_count=n,denominator_count=10,conditioning_probability=n/10,isi=dict(status='estimated',value=14.0,unit='ISI_points',standard_error=.01,interval=None)),death_times_days=[10.0],admission_times_days=[20.0])
        vector=dict(schema_version='1.0.0',synthetic=True,kind='interruption_result',estimand_id='EST-INT',estimand_version='1.0.0',horizon_days=42,intervention=arm(request.target.estimand.intervention,7),comparator=arm(request.target.estimand.comparator,8),interpretation='intervention_specific_conditional_populations_not_common_survivors',overall_ranking='suppressed')
        response=self.response(request,status='pending',result=vector)
        response['interruption_precision']=[dict(component=which+'.'+name,status='pending' if name=='conditional_isi' else 'unresolved_probability_precision',numerical_standard_error=.005,smallest_estimator_se=.1,matched_pilot=self.pilot) for which in ['intervention','comparator'] for name in ['survival_day42','admission_by_day42','alive_outpatient_day42','conditional_isi']]
        validate_truth_response(request,load(TruthResponse,response))
        response['status']='computed';response['reason']=None
        with self.assertRaises(ValueError):load(TruthResponse,response)
        response['interruption_precision'][0]['status']='computed'
        with self.assertRaises(ValueError):load(TruthResponse,response)
        response['status']='pending';response['reason']='Unresolved';response['interruption_precision'][0]['status']='unresolved_probability_precision';response['result']['intervention']['conditional_isi'].update(numerator_count=1,conditioning_probability=.1)
        response['result']['intervention']['alive_outpatient_day42']=.1
        with self.assertRaises(ValueError):load(TruthResponse,response)

    def test_calibration_cannot_lower_sample_or_substitute_target_and_fixture_cannot_authorize_engine(self):
        bindings=self.data['run'].bindings
        sample=artifact(self.root,'calibration-sample','calibration/sample.json',dict(kind='pure_contract_fixture',executed=False),'calibration')
        seeds=artifact(self.root,'calibration-seeds','calibration/seeds.json',dict(kind='pure_contract_fixture',executed=False),'seed_ledger')
        expected=calibration_request(cell_id='S23.MAR_20.n60',dgp=bindings.dgp)
        binding=dict(schema_version='1.1.0',synthetic=True,**expected,status='inconclusive',calibration_sample_sha256=sample['sha256'],seed_key_sha256=seeds['sha256'],sample_size=200000,achieved=None,achieved_mcse=None,coefficient=None,iterations=0,frozen_before='development_and_confirmation')
        data=dict(schema_version='1.0.0',synthetic=True,kind='calibration_artifact',contract_version='1.0.0',run_id=self.data['run'].run_id,producer=self.producer,execution='contract_fixture',source_commit=self.authority.source_commit,runtime=self.authority.runtime.model_dump(mode='json'),binding=binding,sample=sample,seeds=seeds,source_reference=None,source_pilot=None,comparator_pilots=[])
        raw=canonical(data);verify_calibration(raw,self.root,expected_sha256=sha256(raw),evaluator=self.authority,bindings=bindings)
        bad=copy.deepcopy(data);bad['binding']['sample_size']=1000
        with self.assertRaises(ValueError):load(CalibrationArtifact,bad)
        bad=copy.deepcopy(data);bad['binding']['target']=.4;raw=canonical(bad)
        with self.assertRaises(ValueError):verify_calibration(raw,self.root,expected_sha256=sha256(raw),evaluator=self.authority,bindings=bindings)
        authority=self.authority.model_dump(mode='json');authority['allow_contract_fixture']=False
        raw=canonical(data)
        with self.assertRaises(ValueError):verify_calibration(raw,self.root,expected_sha256=sha256(raw),evaluator=load(Authority,authority),bindings=bindings)


if __name__=='__main__':unittest.main()
