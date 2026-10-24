"""Inert fixtures are never real exports/posteriors/attestations or runtime proof."""
import ast
import copy
from contextlib import contextmanager
import json
import math
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from pydantic import ValidationError
from contracts.domain.analysis import canonical,reference,sha
from contracts.domain.borrow_runtime import NATIVE_OPTIMIZER
from contracts.domain.support_s2_native import *
from test_s2_app_source import namespace,InertDB,exported,fit_input,seed

ROOT=Path(__file__).resolve().parents[1]
WORKER='services/learner/support_s2_worker.py'
FIT='methods/support/s2_fit.py'
ARTIFACT='services/learner/support_s2_artifacts.py'


def source(path):return ast.parse((ROOT/path).read_text(encoding='utf-8'))


def functions(path,*names,**bindings):
    tree=source(path)
    selected=[node for node in tree.body if isinstance(node,(ast.FunctionDef,ast.ClassDef)) and node.name in names]
    result=dict(__name__='inert_actual_source_functions',**bindings)
    exec(compile(ast.Module(body=selected,type_ignores=[]),str(ROOT/path),'exec'),result)
    return result


def worker():
    ns=dict(__name__='inert_actual_worker_source')
    exec(compile(source(WORKER),str(ROOT/WORKER),'exec'),ns)
    return ns


def product():
    exported_input=exported(namespace(),InertDB(),target_missing=True)
    return NativeInput.model_validate_json(canonical(dict(schema_version='s2-native-source-1.0.0',
        kind='poc_support_s2_native_fit_input',initial=fit_input(exported_input).model_dump(mode='json'),
        extension=None,parent_result_reference=None,retained_initial_artifact=None,
        configuration=CONFIG_REF,posterior_schema=SCHEMA_REF,executable=False)))


def fake_diagnostics(**updates):
    result=dict(variables={name:dict(rhat=1.,ess_bulk=600.,ess_tail=500.,mcse=.1) for name in MONITORED},
        energy_min=[1.,1.,1.,1.],energy_max=[10.,10.,10.,10.],bfmi=[.5,.5,.5,.5],divergences=0,
        tree_depth_hits=0,maximum_tree_depth=8,sampler_warnings=0,python_warnings=0,accepted=True)
    result.update(updates)
    return result


def fake_result(p):
    owned=ownership(p);bound=dimension_bound(p.initial.export.provenance.cutoff_day,p.draws)
    trusted=dict(schema_version='s2-native-trusted-launch-v1',input_sha256=owned['input_sha256'],
        ownership_sha256=sha(owned),configuration=CONFIG_REF,source_commit='1'*40,
        learner_image='sha256:'+'2'*64,installed_closure_sha256='3'*64,claim_sha256='4'*64)
    vm=dict(vm_type='pytensor.link.c.cvm.CVM',linker='VMLinker',use_cloop=True,c_thunks=True,
        callback_empty=True,callback_input_empty=True,
        limitation='Whole VM checked; individual operations may use ordinary Python thunks.')
    compilation=dict(index=1,actual_vm=vm,compiled_optimizer=NATIVE_OPTIMIZER,
        coordinate_map=coordinate_layout(p.initial.export.provenance.cutoff_day),
        compiled_graph_float32_constants=0,unowned_random_variables=0,strict_prior_operands=True,finite_logp_dlogp=True)
    result=dict(schema_version='s2-native-source-1.0.0',kind='poc_support_s2_native_fit_result',
        attempt_id=p.attempt_id,configuration=CONFIG_REF,ownership=owned,diagnostics=fake_diagnostics(),
        semantics=dict(schema_version='s2-native-binary-v1',posterior_schema=SCHEMA_REF,
            input_sha256=owned['input_sha256'],ownership_sha256=sha(owned),chains=4,draws=p.draws,
            cutoff=p.initial.export.provenance.cutoff_day,artifact=dict(path='posterior.nc',bytes=1000,
                sha256='5'*64,uncompressed_bytes=bound['uncompressed_bytes']),roundtrip=True),
        execution=dict(launch=trusted,native_compilations=[compilation],callback_calls=8*p.draws,python_warnings=0),
        status='completed',reason=None,serving_authority=False)
    return NativeResult.model_validate_json(canonical(result)),trusted


class ContractChecks(unittest.TestCase):
    def test_max_shape_scalar_bound_and_retained_pair(self):
        for cutoff,count in ((14,407),(28,743),(84,2087)):
            for draws in (1000,2000):
                b=dimension_bound(cutoff,draws)
                self.assertEqual(b['posterior_bytes'],count*4*draws*8)
                self.assertLess(b['uncompressed_bytes']+8*MIB,b['file_cap'])
        self.assertLess(FILE_CAPS[1000]+FILE_CAPS[2000]+2*RESULT_CAP,TOTAL_CAP)
        for cutoff,draws in ((85,1000),(14,999),(14,True)):
            with self.assertRaises(ValueError):dimension_bound(cutoff,draws)
    def test_closed_schema_full_inventory_axes_dtype_units(self):
        schema=variable_schema(84)
        self.assertEqual(len(MONITORED),37)
        self.assertEqual(set(schema['posterior']),set(MONITORED))
        self.assertEqual(schema['posterior']['tau'],dict(dims=['chain','draw','patient'],dtype='float64',unit='quality_points_per_centered_assignment'))
        self.assertEqual(schema['posterior']['b']['dims'],['chain','draw','feature'])
        self.assertEqual(schema['posterior']['epsilon_11']['dims'],['chain','draw','night_11'])
        self.assertEqual(set(schema['sample_stats']),{'energy','lp','diverging','tree_depth','sampler_warning'})
    def test_immutable_old_contract_and_no_activation(self):
        from contracts.domain.support_s2_app import require_executable as old_gate,CONFIG as old
        self.assertFalse(old['execution']['executable']);self.assertFalse(CONFIG['executable'])
        for gate in (require_executable,old_gate):
            with self.assertRaises(ValueError):gate({'executable':True})
    def test_native_product_and_result_complete_identity(self):
        p=product();result,trusted=fake_result(p)
        self.assertEqual(validate_result(result,p,trusted),result)
        self.assertEqual(len(result.ownership.members),12)
        self.assertEqual(result.ownership.target_id,'UNIT-S2-07')
    def test_result_warning_counts_match_for_parser_typed_and_admission(self):
        p=product();result,trusted=fake_result(p)
        zero=result.model_dump(mode='json')
        parsed=parse_native_result(canonical(zero).encode())
        self.assertEqual(validate_result(parsed,p,trusted).status,'completed')
        self.assertTrue(parsed.diagnostics.accepted)
        for execution_count,diagnostic_count in ((1,0),(0,1)):
            mismatch=copy.deepcopy(zero)
            mismatch['execution']['python_warnings']=execution_count
            mismatch['diagnostics']['python_warnings']=diagnostic_count
            if diagnostic_count:
                mismatch['diagnostics']['accepted']=False
                mismatch.update(status='abstained',reason='fit_diagnostics_unmet')
            with self.assertRaisesRegex(ValueError,'warning_evidence_mismatch'):
                NativeResult.model_validate_json(canonical(mismatch))
            with self.assertRaisesRegex(ValueError,'warning_evidence_mismatch'):
                parse_native_result(canonical(mismatch).encode())
        # Nested model assignment cannot bypass the admission revalidation.
        result.execution.python_warnings=1
        with self.assertRaisesRegex(ValueError,'warning_evidence_mismatch'):
            validate_result(result,p,trusted)
        nonzero=copy.deepcopy(zero)
        nonzero['execution']['python_warnings']=1
        nonzero['diagnostics'].update(python_warnings=1,accepted=False)
        nonzero.update(status='abstained',reason='fit_diagnostics_unmet')
        abstained=parse_native_result(canonical(nonzero).encode())
        self.assertEqual(validate_result(abstained,p,trusted).status,'abstained')
        self.assertFalse(abstained.diagnostics.accepted)
    def test_missing_nonfinite_and_threshold_diagnostics_fail_closed(self):
        for key in ('bfmi','energy_min','variables','sampler_warnings','tree_depth_hits'):
            data=fake_diagnostics();data.pop(key)
            with self.assertRaises(ValidationError):FitDiagnostics.model_validate_json(canonical(data))
        for field,value in (('rhat',1.01),('ess_bulk',399.),('ess_tail',399.)):
            data=fake_diagnostics();data['variables']['tau'][field]=value
            with self.assertRaises(ValueError):FitDiagnostics.model_validate_json(canonical(data))
            data['accepted']=False;FitDiagnostics.model_validate_json(canonical(data))
        for field in ('rhat','ess_bulk','ess_tail','mcse'):
            data=fake_diagnostics();data['variables']['tau'][field]=float('nan')
            with self.assertRaises(ValueError):FitDiagnostics.model_validate_json(json.dumps(data))
        data=fake_diagnostics();data['variables'].pop('epsilon_11')
        with self.assertRaises(ValueError):FitDiagnostics.model_validate_json(canonical(data))
    def test_all_chain_energy_warning_divergence_depth_and_bfmi_gates(self):
        for updates in (dict(bfmi=[.5,.5,.5,.3]),dict(divergences=1),dict(tree_depth_hits=1,maximum_tree_depth=12),
                dict(sampler_warnings=1),dict(python_warnings=1)):
            data=fake_diagnostics(**updates)
            with self.assertRaises(ValueError):FitDiagnostics.model_validate_json(canonical(data))
            data['accepted']=False;FitDiagnostics.model_validate_json(canonical(data))
    def test_rehashed_ownership_semantic_and_execution_corruptions(self):
        p=product();result,trusted=fake_result(p)
        mutations=[lambda d:d['ownership']['members'][11].update(history_sha256='6'*64),
            lambda d:d['ownership'].update(owner_id='UNIT-foreign'),
            lambda d:d['ownership'].update(purpose='wrong'),
            lambda d:d['semantics'].update(draws=2000),
            lambda d:d['semantics']['artifact'].update(uncompressed_bytes=1),
            lambda d:d['execution']['native_compilations'][0].update(compiled_graph_float32_constants=1),
            lambda d:d['execution']['native_compilations'][0]['actual_vm'].update(c_thunks=False),
            lambda d:d['execution'].update(callback_calls=1),
            lambda d:d['execution']['launch'].update(claim_sha256='7'*64)]
        for mutate in mutations:
            data=result.model_dump(mode='json');mutate(data)
            if 'ownership' in data:data['semantics']['ownership_sha256']=sha(data['ownership'])
            with self.assertRaises(ValueError):validate_result(NativeResult.model_validate_json(canonical(data)),p,trusted)
    def test_manifest_rejects_extra_path_missing_fields_and_nonfinite_nested(self):
        p=product();r,_=fake_result(p)
        for name,mutate in (('extra',lambda d:d.update(extra=1)),('path',lambda d:d['semantics']['artifact'].update(path='../posterior.nc')),
                ('missing',lambda d:d['semantics'].pop('roundtrip')),('nonfinite',lambda d:d['execution'].update(extra=float('inf')))):
            with self.subTest(name=name):
                data=r.model_dump(mode='json');mutate(data)
                with self.assertRaises(ValueError):NativeResult.model_validate_json(json.dumps(data))
        self.assertEqual(parse_native_result(canonical(r.model_dump(mode='json')).encode()),r)
        for raw in (b'{"kind":1,"kind":1}',b'{"x":NaN}',b' '* (RESULT_CAP+1),b'['*22+b'0'+b']'*22):
            with self.assertRaises(ValueError):parse_native_result(raw)
    def test_explicit_one_extension_retains_original_and_distinct_purpose(self):
        p=product();r,trusted=fake_result(p)
        raw=p.model_dump(mode='json');initial=p.initial
        extension=dict(schema_version='s2-app-source-1.0.0',attempt_id='UNIT-extension',parent_attempt_id=initial.attempt_id,
            parent_input_reference=reference('poc-support-s2-app-fit-input-v1',initial.model_dump(mode='json')),
            original_export_reference=initial.export.reference.model_dump(),seed_record=seed(initial.export,
                job='UNIT-extension',replicate=556677,process='S2-refresh-fit-extension'),number=1,
            trigger='canonical_fit_diagnostics_failed',tune=2000,draws=2000,chains=4,
            retain_initial_artifacts=True,concatenate_attempts=False,executable=False)
        raw.update(extension=extension,parent_result_reference=reference('poc-support-s2-native-fit-result-v1',r.model_dump(mode='json')),
            retained_initial_artifact=r.semantics.artifact.model_dump())
        extended=NativeInput.model_validate_json(canonical(raw))
        with self.assertRaises(ValueError):validate_extension_admission(extended,r,p,trusted)
        extension['trigger']='required_indicator_precision_failed';raw['extension']=extension
        extended=NativeInput.model_validate_json(canonical(raw))
        validate_extension_admission(extended,r,p,trusted,indicator_failed=True)
        with self.assertRaises(ValueError):validate_extension_admission(extended,r,p,trusted)
        for mutate in (lambda d:d['extension'].update(number=2),
                lambda d:d['extension']['seed_record']['key'].update(process='S2-refresh-fit-initial'),
                lambda d:d.update(retained_initial_artifact=None)):
            bad=copy.deepcopy(raw);mutate(bad)
            with self.assertRaises(ValueError):NativeInput.model_validate_json(canonical(bad))


class WorkerSourceChecks(unittest.TestCase):
    def test_stdlib_entry_and_default_gate_before_private_io_and_policy(self):
        ns=worker()
        with patch.object(Path,'open',side_effect=AssertionError('private read')),patch.object(Path,'is_file',side_effect=AssertionError('private stat')):
            with self.assertRaisesRegex(ValueError,'unqualified'):ns['run'](Path('never-input'),Path('never-output'))
        imports=[]
        for node in source(WORKER).body:
            if isinstance(node,ast.Import):imports.extend(a.name.split('.')[0] for a in node.names)
            elif isinstance(node,ast.ImportFrom):imports.append(node.module.split('.')[0])
        self.assertTrue(set(imports)<={'argparse','hashlib','json','math','os','pathlib','sys','time'})
        run=next(n for n in source(WORKER).body if isinstance(n,ast.FunctionDef) and n.name=='run')
        calls=[n.func.id for n in ast.walk(run) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name)]
        self.assertLess(calls.index('require_executable'),calls.index('construction_policy'))
    def test_construction_policy_strict_before_imports(self):
        ns=worker();env={};ns['construction_policy'](env)
        self.assertEqual(env['PYTENSOR_FLAGS'],ns['FLAGS'])
        for bad in ({'PYTENSORRC':'/other/rc'},{'PYTENSOR_FLAGS':'floatX=float32'},{'OMP_NUM_THREADS':'2'}):
            with self.assertRaises(ValueError):ns['construction_policy'](bad)
        with patch.dict(ns['sys'].modules,{'pymc':SimpleNamespace()}):
            with self.assertRaises(ValueError):ns['construction_policy']({})
    def test_absolute_origin_backward_clock_extension_and_stage_veto(self):
        ns=worker();wall=[100.];mono=[10.]
        b=ns['Budget'](0.,clock=lambda:wall[0],monotonic=lambda:mono[0])
        b.require_preflight(False);b.stage({'stage':'fitting'})
        wall[0]=200.;b.require_preflight(True)
        with self.assertRaises(TimeoutError):b.require_preflight(False)
        wall[0]=50.;mono[0]=6810.
        with self.assertRaises(TimeoutError):b.check()
        b=ns['Budget'](0.,clock=lambda:100.,monotonic=lambda:10.)
        b.stage({'stage':'diagnostics'})
        with self.assertRaisesRegex(ValueError,'veto'):b.stage({'stage':'fitting'})
        with self.assertRaises(ValueError):ns['Budget'](101.,clock=lambda:100.)
    def test_bounded_closed_json_rejects_duplicates_nonfinite_depth_and_rows(self):
        parse=worker()['strict_json']
        for raw in ('{"a":1,"a":2}','{"x":NaN}','['*34+'0'+']'*34,json.dumps(['a']*12001)):
            with self.assertRaises(ValueError):parse(raw)
        self.assertEqual(parse('{"ok":true}'),{'ok':True})
    def sample_namespace(self,fake_sample):
        @contextmanager
        def guard(*args,**kwargs):yield [{'inert':True}]
        @contextmanager
        def model():yield None
        return functions(FIT,'sample',warnings=__import__('warnings'),np=SimpleNamespace(int64=int),
            actual_policy=lambda:{'mode':'inert-CVM'},build=lambda data:model(),construction_guards=lambda m:None,
            sampling_graph=guard,pm=SimpleNamespace(sample=fake_sample))
    def test_exact_native_sampler_kwargs_and_all_callbacks(self):
        calls={};events=[];checks=[]
        def blocked_sample(**kwargs):
            calls.update(kwargs)
            for chain in range(4):
                for i in range(2000):kwargs['callback'](None,SimpleNamespace(chain=chain,draw_idx=i,tuning=i<1000))
            return 'inert-not-a-posterior'
        p=product();trace,record=self.sample_namespace(blocked_sample)['sample']('inert',p,stage=events.append,check=lambda:checks.append(1))
        self.assertEqual(trace,'inert-not-a-posterior');self.assertEqual(record['callback_calls'],8000)
        expected=dict(draws=1000,tune=1000,chains=4,cores=1,random_seed=p.seed_record.sampler_seed,
            nuts_sampler='pymc',target_accept=.995,nuts={'max_treedepth':12},blas_cores=1,progressbar=False,
            return_inferencedata=True,compile_kwargs={'mode':'inert-CVM'},keep_warning_stat=True,
            discard_tuned_samples=True,idata_kwargs={'log_likelihood':False})
        self.assertEqual({k:v for k,v in calls.items() if k!='callback'},expected)
        self.assertGreater(len(checks),8000);self.assertLess(len(events),250)
    def test_deadline_and_stage_veto_observed_before_blocked_sample_returns(self):
        for error in (TimeoutError('inert deadline'),ValueError('inert monitor stage veto')):
            returned=[];count=[0]
            def blocked_sample(**kwargs):
                for i in range(5):kwargs['callback'](None,SimpleNamespace(chain=0,draw_idx=i,tuning=True))
                returned.append(True)
            def check():
                count[0]+=1
                if count[0]>=5:raise error
            with self.assertRaises(type(error)):
                self.sample_namespace(blocked_sample)['sample']('inert',product(),stage=lambda v:None,check=check)
            self.assertFalse(returned)
        def blocked(**kwargs):kwargs['callback'](None,SimpleNamespace(chain=0,draw_idx=0,tuning=True))
        def veto(v):
            if v.get('event')=='sampling':raise ValueError('monitor veto')
        with self.assertRaisesRegex(ValueError,'monitor veto'):
            self.sample_namespace(blocked)['sample']('inert',product(),stage=veto,check=lambda:None)
    def test_strict_prior_both_halfnormal_operands_RV_ownership_and_F32_constants(self):
        class Constant:
            def __init__(self,dtype='float64'):self.dtype=dtype
        class RandomVariable:pass
        class RV:
            def __init__(self,name):
                self.name=name;self.dtype='float64';self.owner=SimpleNamespace(op=RandomVariable(),inputs=[None,None,Constant(),Constant()])
        names=['mu_alpha','mu_tau','b','s_alpha','s_tau','s_e','s_Q','rho','z','u']+['epsilon_'+str(i) for i in range(12)]
        rvs=[RV(name) for name in names]
        model=SimpleNamespace(free_RVs=rvs,value_vars=rvs,named_vars={r.name:r for r in rvs},
            potentials=['inert'],deterministics=[],logp=lambda:'inert-logp',dlogp=lambda:'inert-dlogp')
        ancestry=list(rvs);constants=[Constant()]
        ns=functions(FIT,'construction_guards','reject_f32',Constant=Constant,RandomVariable=RandomVariable,
            ancestors=lambda outputs:ancestry,graph_inputs=lambda outputs:constants)
        ns['construction_guards'](model)
        for name,ordinal in (('mu_alpha',2),('s_alpha',2),('s_alpha',3),('rho',3)):
            before=model.named_vars[name].owner.inputs[ordinal]
            model.named_vars[name].owner.inputs[ordinal]=Constant('float32')
            with self.assertRaisesRegex(ValueError,'operand'):ns['construction_guards'](model)
            model.named_vars[name].owner.inputs[ordinal]=before
        ancestry.append(RV('rogue'))
        with self.assertRaisesRegex(ValueError,'unregistered'):ns['construction_guards'](model)
        ancestry.pop();constants.append(Constant('float32'))
        with self.assertRaisesRegex(ValueError,'Constant'):ns['construction_guards'](model)
    def test_actual_sampler_callable_graph_optimizer_layout_and_restore(self):
        class RandomVariable:pass
        class Constant:
            def __init__(self,dtype):self.dtype=dtype
        @contextmanager
        def unused():yield
        graph=SimpleNamespace(variables=[],outputs=[],toposort=lambda:[])
        fn=SimpleNamespace(maker=SimpleNamespace(mode=SimpleNamespace(provided_optimizer=NATIVE_OPTIMIZER),fgraph=graph))
        actual=SimpleNamespace(_pytensor_function=fn)
        class Model:
            continuous_value_vars=['inert-value-vars']
            def logp_dlogp_function(self,*args,**kwargs):return actual
            def initial_point(self):return {'inert':'point'}
        model=Model();events=[]
        ns=functions(FIT,'sampling_graph','reject_f32',contextmanager=contextmanager,Constant=Constant,
            RandomVariable=RandomVariable,graph_inputs=lambda v:[],actual_policy=lambda:None,
            verify_cvm=lambda f:{'inert':'CVM'},optimizer_identity=lambda value:value,NATIVE_OPTIMIZER=NATIVE_OPTIMIZER,
            native_call=lambda f,p,v:(1.,[],coordinate_layout(14)),coordinate_layout=coordinate_layout)
        with ns['sampling_graph'](model,cutoff=14,stage=events.append) as records:
            self.assertIs(model.logp_dlogp_function(),actual)
        self.assertEqual(records[0]['coordinate_map'],coordinate_layout(14));self.assertNotIn('logp_dlogp_function',model.__dict__)
        for case in ('optimizer','constant','rv','layout'):
            if case=='optimizer':fn.maker.mode.provided_optimizer={}
            if case=='constant':graph.variables=[Constant('float32')]
            if case=='rv':graph.toposort=lambda:[SimpleNamespace(op=RandomVariable())]
            if case=='layout':ns['native_call']=lambda f,p,v:(1.,[],[])
            with self.assertRaises(ValueError):
                with ns['sampling_graph'](model,cutoff=14,stage=lambda _:None):model.logp_dlogp_function()
            self.assertNotIn('logp_dlogp_function',model.__dict__)
            fn.maker.mode.provided_optimizer=NATIVE_OPTIMIZER;graph.variables=[];graph.toposort=lambda:[]
        with self.assertRaisesRegex(ValueError,'no_guarded'):
            with ns['sampling_graph'](model,cutoff=14,stage=lambda _:None):pass


class DispatchIngestSourceChecks(unittest.TestCase):
    def test_independent_existing_supervisor_polls_while_sampler_blocked(self):
        import contracts.domain.support_s2_native as contract
        clock=[100.];returned=[];entered=[]
        ns=functions('tooling/foundation/analysis_dispatcher.py','n_json','S2Monitor','supervise_s2',
            json=json,math=math,time=SimpleNamespace(monotonic=lambda:clock[0]),N_JSON_ROWS=12000)
        def blocked_supervise(cid,folder,deadline,on_poll,**kwargs):
            entered.append((cid,deadline,kwargs))
            on_poll();on_poll()  # call is still blocked; stage regression vetoes
            returned.append(True)
        ns['supervise']=blocked_supervise
        monitor=ns['S2Monitor'](0.,7200.,'UNIT-attempt','0'*64,clock=lambda:clock[0])
        events=[dict(schema='s2-native-progress-v1',attempt_id='UNIT-attempt',input_sha256='0'*64,
            sequence=1,stage='fitting',extension=False,elapsed_seconds=90.),
            dict(schema='s2-native-progress-v1',attempt_id='UNIT-attempt',input_sha256='0'*64,
            sequence=2,stage='preparing',extension=False,elapsed_seconds=91.)]
        # A labeled inert replacement of the production gate solely exercises
        # the prepared existing-supervisor seam. No native supervisor is run.
        with patch.object(contract,'require_executable',return_value=None):
            with self.assertRaisesRegex(ValueError,'stage_or_origin_reset'):
                ns['supervise_s2']('inert-CID','inert-folder',monitor,
                    lambda cap,deadline:canonical(events.pop(0)).encode(),lambda v:None)
        self.assertTrue(entered);self.assertFalse(returned)
        self.assertEqual(entered[0][1:],(7200.,{'discard_output':True}))
        monitor=ns['S2Monitor'](0.,7200.,'UNIT-attempt','0'*64,clock=lambda:clock[0])
        def blocked_deadline(cid,folder,deadline,on_poll,**kwargs):
            clock[0]=6900.;on_poll();returned.append(True)
        ns['supervise']=blocked_deadline
        with patch.object(contract,'require_executable',return_value=None):
            with self.assertRaises(TimeoutError):
                ns['supervise_s2']('inert-CID','inert-folder',monitor,lambda cap,deadline:None,lambda v:None)
        self.assertFalse(returned)
    def test_monitor_progress_closed_bounded_and_default_supervise_off(self):
        ns=functions('tooling/foundation/analysis_dispatcher.py','n_json','S2Monitor','supervise_s2',
            json=json,math=math,time=SimpleNamespace(monotonic=lambda:100.),N_JSON_ROWS=12000)
        m=ns['S2Monitor'](0.,7200.,'UNIT-attempt','0'*64,clock=lambda:100.)
        with self.assertRaises(ValueError):ns['supervise_s2']('never-CID',None,m,None,None)
        for raw in (b'x'*2049,b'{"a":1,"a":2}',canonical(dict(schema='bad')).encode()):
            with self.assertRaises(ValueError):m.admit(raw)
    def test_explicit_S2_dispatch_and_unknown_S2_never_generic(self):
        ns=functions('tooling/foundation/analysis_dispatcher.py','worker_module','require_dispatchable',json=json)
        self.assertEqual(ns['worker_module']({'kind':'poc_support_s2_native_fit_input'}),'services.learner.support_s2_worker')
        for kind in ('poc_support_s2_app_fit_input','poc_support_s2_native_fit_input','poc_support_s2_prediction_input','poc_support_s2_future'):
            with self.assertRaises(ValueError):ns['require_dispatchable']({'kind':kind,'executable':True})
            if kind!='poc_support_s2_native_fit_input':
                with self.assertRaises(ValueError):ns['worker_module']({'kind':kind})
        self.assertEqual(ns['worker_module']({'kind':'poc_nof1_input'}),'services.learner.nof1_worker')
    def test_claim_bind_ingest_intercept_S2_before_generic_parsers(self):
        text=(ROOT/'services/foundation/analysis.py').read_text()
        for name,first,second in (('claim','poc_support_s2_','token=secrets'),
                ('bind_execution','poc_support_s2_','product=parse_input'),('ingest','poc_support_s2_','result=parse_result')):
            node=next(n for n in source('services/foundation/analysis.py').body if isinstance(n,ast.FunctionDef) and n.name==name)
            body=ast.get_source_segment(text,node)
            self.assertLess(body.index(first),body.index(second))
        ns=namespace()
        with self.assertRaises(ValueError):ns['ingest_native'](None,None,None,None,None)
    def test_owned_collection_current_authority_and_rehashed_custody(self):
        p=product();r,trusted=fake_result(p);ns=namespace()
        custody=dict(schema='s2-native-owned-collection-v1',attempt_id=p.attempt_id,
            input_sha256=ownership(p)['input_sha256'],claim_sha256=trusted['claim_sha256'],
            terminal='reaped_exit_0_no_oom_no_restart',files=[r.semantics.artifact.model_dump(mode='json')],
            result_sha256=sha(r.model_dump(mode='json')))
        args=dict(file_custody=custody,current_export=p.initial.export,active_owner=p.initial.export.provenance.owner_id,
            active_store=p.initial.export.provenance.store_id,authority_generation=p.initial.export.selection.authority_generation,
            job=p.attempt_id,claim_sha256=trusted['claim_sha256'],collection_sha256=sha(custody))
        ns['validate_native_collection'](p,r,trusted,**args)
        for key,value in (('active_owner','UNIT-other'),('active_store','UNIT-other'),('authority_generation',2),
                ('job','UNIT-other'),('claim_sha256','0'*64),('collection_sha256','0'*64)):
            bad=dict(args);bad[key]=value
            with self.assertRaises(ValueError):ns['validate_native_collection'](p,r,trusted,**bad)
        bad=copy.deepcopy(args);bad['file_custody']['terminal']='parent_reaped_child_unknown'
        bad['collection_sha256']=sha(bad['file_custody'])
        with self.assertRaises(ValueError):ns['validate_native_collection'](p,r,trusted,**bad)
    def test_artifact_source_contains_actual_roundtrip_and_corruption_controls(self):
        tree=source(ARTIFACT);names={n.name for n in tree.body if isinstance(n,ast.FunctionDef)}
        self.assertTrue({'write','header','validate','corruption_controls'}<=names)
        text=(ROOT/ARTIFACT).read_text()
        for control in ('units','chain_labels','patient_labels','nonfinite','joint_alignment','extra_variable'):
            self.assertIn("'"+control+"'",text)
        self.assertIn('dimension_bound(cutoff,product.draws)',text)
        self.assertIn('header(path,product)',text);self.assertIn('xr.open_dataset',text)
        self.assertIn('np.array_equal',text);self.assertIn('S2_joint_latent_recurrence_alignment_corruption',text)
    def test_actual_writer_postwrite_header_precedes_first_reopen_and_values(self):
        # Execute the actual writer AST from its to_netcdf call through return.
        # The pre-write producer preparation is outside this ordering control;
        # every role/API/value below is a finite inert double, never an array.
        write=copy.deepcopy(next(n for n in source(ARTIFACT).body if isinstance(n,ast.FunctionDef) and n.name=='write'))
        start=next(i for i,n in enumerate(write.body) if isinstance(n,ast.Expr)
            and isinstance(n.value,ast.Call) and isinstance(n.value.func,ast.Attribute)
            and n.value.func.attr=='to_netcdf')
        write.body=write.body[start:]
        events=[];reject=[False];mismatch=[False]
        class Value:
            def __init__(self,label):self.label=label
            @property
            def values(self):events.append(self.label);return self.label.split(':')[1]
        originals={'posterior':{'alpha':Value('original:inert')},'sample_stats':{'energy':Value('original:inert')}}
        class Tree:
            def to_netcdf(self,*args,**kwargs):events.append('write')
        def digest(*args):events.append('bounded_file_check')
        def header(*args):
            events.append('header')
            if reject[0]:raise ValueError('inert rejected raw header')
        @contextmanager
        def opened(*args,**kwargs):
            events.append('data_open')
            yield {name:Value('saved:changed' if mismatch[0] else 'saved:inert') for name in originals[kwargs['group']]}
        def equal(a,b):events.append('producer_equality');return a==b
        def validated(*args,**kwargs):events.append('semantic_validation');return 'inert-semantics'
        ns=dict(tree=Tree(),path='inert-path',bound={'file_cap':1},encoding={},
            posterior=originals['posterior'],stats=originals['sample_stats'],schema=originals,
            file_digest=digest,header=header,xr=SimpleNamespace(open_dataset=opened),
            np=SimpleNamespace(array_equal=equal),validate=validated)
        exec(compile(ast.Module(body=[write],type_ignores=[]),'inert_actual_writer_postwrite_tail','exec'),ns)
        reject[0]=True
        with self.assertRaisesRegex(ValueError,'rejected raw header'):
            ns['write'](None,'inert-directory','inert-product',check=lambda:None)
        self.assertEqual(events,['write','bounded_file_check','header'])
        events.clear();reject[0]=False
        self.assertEqual(ns['write'](None,'inert-directory','inert-product',check=lambda:None),'inert-semantics')
        self.assertEqual(events[:4],['write','bounded_file_check','header','data_open'])
        self.assertEqual(events.count('producer_equality'),2)
        self.assertEqual(events[-1],'semantic_validation')
        events.clear();mismatch[0]=True
        with self.assertRaisesRegex(ValueError,'roundtrip_value_changed'):
            ns['write'](None,'inert-directory','inert-product',check=lambda:None)
        self.assertIn('producer_equality',events)
        self.assertNotIn('semantic_validation',events)
    def test_actual_binary_header_refuses_axis_dtype_unit_VLEN_and_group_corruption(self):
        # Only the scientific import is replaced with a finite inert API double.
        # The actual header validator executes unchanged; no binary file opens.
        p=product();schema=variable_schema(14)
        helpers=functions(ARTIFACT,'attrs','dimensions',SCHEMA_REF=SCHEMA_REF,sha=sha,ownership=ownership)
        class Dimension:
            def __init__(self,size):self.size=size
            def __len__(self):return self.size
            def isunlimited(self):return False
        class Variable:
            def __init__(self,dims,dtype,attrs):self.dimensions=tuple(dims);self.dtype=dtype;self.attrs=attrs
            def ncattrs(self):return list(self.attrs)
            def getncattr(self,key):return self.attrs[key]
            def filters(self):return dict(zlib=False,shuffle=False,complevel=0)
        def make_root():
            groups={};sizes=helpers['dimensions'](p)
            for group,variables in schema.items():
                coords=set().union(*(set(v['dims']) for v in variables.values()))
                dims={n:Dimension(sizes[n]) for n in coords}
                if group=='posterior':dims.update({n+'_label_byte':Dimension(128) for n in ('patient','feature')})
                var={}
                for name,value in variables.items():
                    dtype='int8' if value['dtype']=='bool' else value['dtype']
                    attrs=dict(unit=value['unit'])
                    if value['dtype']=='bool':attrs['dtype']='bool'
                    var[name]=Variable(value['dims'],dtype,attrs)
                for name in coords:
                    var[name]=Variable((name,name+'_label_byte') if name in ('patient','feature') else (name,),
                        '|S1' if name in ('patient','feature') else 'int64',{})
                groups[group]=SimpleNamespace(groups={},variables=var,dimensions=dims,ncattrs=lambda:[])
            identity=helpers['attrs'](p)
            return SimpleNamespace(groups=groups,variables={},dimensions={},ncattrs=lambda:list(identity),getncattr=lambda k:identity[k])
        root=[make_root()]
        @contextmanager
        def dataset(*args,**kwargs):yield root[0]
        header=copy.deepcopy(next(n for n in source(ARTIFACT).body if isinstance(n,ast.FunctionDef) and n.name=='header'))
        self.assertEqual(header.body[1].module,'netCDF4')
        del header.body[1]
        ns=dict(Dataset=dataset,variable_schema=variable_schema,**helpers)
        exec(compile(ast.Module(body=[header],type_ignores=[]),'inert_actual_binary_header','exec'),ns)
        ns['header']('inert-path-never-opened',p)
        for mutate in (lambda r:r.groups['posterior'].variables['tau'].attrs.update(unit='wrong'),
                lambda r:setattr(r.groups['posterior'].variables['tau'],'dtype','float32'),
                lambda r:setattr(r.groups['posterior'].variables['tau'],'dimensions',('draw','chain','patient')),
                lambda r:setattr(r.groups['posterior'].dimensions['chain'],'size',5),
                lambda r:setattr(r.groups['posterior'].variables['patient'],'dtype',str),
                lambda r:r.groups['sample_stats'].variables.pop('energy'),
                lambda r:r.groups.update(foreign=SimpleNamespace())):
            root[0]=make_root();mutate(root[0])
            with self.assertRaises(ValueError):ns['header']('inert-path-never-opened',p)
    def test_foundation_static_eager_closure_excludes_science(self):
        forbidden={'numpy','scipy','pymc','pytensor','arviz','arviz_stats','xarray','netCDF4','pandas','statsmodels'}
        visited=set()
        def visit(path):
            if path in visited or not (ROOT/path).exists():return
            visited.add(path)
            for node in source(path).body:
                if isinstance(node,ast.Import):
                    for alias in node.names:self.assertNotIn(alias.name.split('.')[0],forbidden)
                elif isinstance(node,ast.ImportFrom):
                    module=node.module or ''
                    self.assertNotIn(module.split('.')[0],forbidden)
                    parent=Path(path).parent
                    destination=(parent/('../'*(node.level-1))/(module.replace('.','/')+'.py')) if node.level else Path(module.replace('.','/')+'.py')
                    if module:visit(str(destination).replace('\\','/'))
        visit('contracts/domain/support_s2_native.py')
        visit('services/foundation/support_s2_analysis.py')
        self.assertGreater(len(visited),5)


if __name__=='__main__':unittest.main()
