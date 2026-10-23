"""Real strict scalar contracts and actual producer AST; no numeric runtime."""
import ast
import copy
from pathlib import Path
import unittest

from pydantic import ValidationError
from contracts.domain.analysis import sha
from contracts.domain.support_s2 import CELLS,S2Request,S2Result
from test_s2_numerics_source import wire

ROOT=Path(__file__).resolve().parents[1]


def function():
    tree=ast.parse((ROOT/'methods/support/s2_prediction.py').read_text(encoding='utf-8'))
    return next(node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name=='predict')


def construct(request,legacy=False):
    assignment=copy.deepcopy(next(node for node in function().body if isinstance(node,ast.Assign)
        and isinstance(node.targets[0],ast.Name) and node.targets[0].id=='result'))
    if legacy:
        cells=assignment.value.keywords[next(i for i,item in enumerate(assignment.value.keywords) if item.arg=='cells')]
        if isinstance(cells.value,ast.Call):
            assert isinstance(cells.value.func,ast.Name) and cells.value.func.id=='tuple'
            generator=cells.value.args[0];assert isinstance(generator,ast.GeneratorExp)
            cells.value=ast.ListComp(elt=generator.elt,generators=generator.generators)
    namespace=dict(request=request,sha=sha,CELLS=CELLS)
    module=ast.fix_missing_locations(ast.Module(body=[assignment],type_ignores=[]))
    exec(compile(module,'isolated_actual_constructor','exec'),namespace)
    return namespace['result']


def scalar_finish(result,summaries):
    body=function().body
    start=next(i for i,node in enumerate(body) if isinstance(node,ast.Assign)
        and isinstance(node.targets[0],ast.Subscript) and isinstance(node.targets[0].value,ast.Name)
        and node.targets[0].value.id=='result' and isinstance(node.targets[0].slice,ast.Constant)
        and node.targets[0].slice.value=='primary')
    original=function()
    original.name='finish_actual_scalar_metadata'
    original.args=ast.arguments(posonlyargs=[],args=[ast.arg(arg=name) for name in
        ('result','summaries','indicators','timing')],kwonlyargs=[],kw_defaults=[],defaults=[])
    original.body=body[start:]
    namespace=dict(S2Result=S2Result)
    module=ast.fix_missing_locations(ast.Module(body=[original],type_ignores=[]))
    exec(compile(module,'isolated_actual_final_metadata','exec'),namespace)
    return namespace[original.name](result,summaries,{'inert':'no arrays'},dict(inert=True))


class ProducerRepresentation(unittest.TestCase):
    def test_actual_constructor_old_list_specific_rejection_and_repaired_tuple_positive(self):
        request=S2Request.model_validate(wire())
        old=construct(request,legacy=True)
        with self.assertRaises(ValidationError) as failure:S2Result.model_validate(old)
        errors=failure.exception.errors(include_input=False,include_url=False)
        self.assertEqual([(item['loc'],item['type']) for item in errors],[(('cells',),'tuple_type')])
        actual=construct(request);self.assertIs(type(actual['cells']),tuple)
        self.assertEqual(len({id(cell) for cell in actual['cells']}),9)
        value=S2Result.model_validate(actual)
        self.assertEqual(tuple((cell.delta0,cell.delta1) for cell in value.cells),CELLS)
        self.assertTrue(all(cell.precision is None for cell in value.cells))
        self.assertEqual(value.probability,.5);self.assertEqual(value.status,'numerical_unready')
        self.assertEqual(value.request_sha256,sha(request.model_dump(mode='json')))
        self.assertEqual((value.target_id,value.context_id,value.context_version),
                         (request.target_id,request.context_id,request.context_version))
        self.assertIs(value.serving_authority,False);self.assertIs(value.empirical_domain_only,True)

    def test_actual_arm_unavailable_branch_returns_before_any_array_operation(self):
        data=wire();data['members'][7]['observed']=(0,4);data['members'][7]['missing']=(0,2)
        request=S2Request.model_validate(data);arrays=object();ids=[m.patient_id for m in request.members];calls=[]
        def inert_index(actual_arrays,actual_ids,actual_request):
            self.assertIs(actual_arrays,arrays);self.assertIs(actual_ids,ids);self.assertIs(actual_request,request)
            calls.append('checked_arrays');return 7
        def forbidden(*args,**kwargs):raise AssertionError('numeric operation reached in early scalar branch')
        namespace=dict(S2Request=S2Request,S2Result=S2Result,sha=sha,CELLS=CELLS,checked_arrays=inert_index,
            action_moments=forbidden,expected_quality=forbidden,rounded_quality=forbidden,indicator_diagnostics=forbidden)
        exec(compile(ast.Module(body=[function()],type_ignores=[]),'isolated_actual_predict_early_branch','exec'),namespace)
        value,indicators,timing=namespace['predict'](request,arrays,ids)
        self.assertEqual(calls,['checked_arrays']);self.assertEqual(value.status,'arm_unavailable')
        self.assertEqual(value.reason,'no complete two-action opportunity in an arm')
        self.assertEqual(value.probability,.5);self.assertIsNone(value.primary)
        self.assertTrue(all(cell.precision is None for cell in value.cells));self.assertEqual(indicators,{})
        self.assertEqual(timing,dict(expected_quality_seconds=0.,diagnostics_seconds=0.,distinct_diagnostic_arrays=0))
        self.assertEqual(value.target_id,'UNIT-07');self.assertIs(value.serving_authority,False)

    def test_actual_populated_scalar_updates_preserve_order_and_ready_metadata(self):
        request=S2Request.model_validate(wire());result=construct(request)
        precision=dict(probability=.7,half_probability=.7,constant_chain=False,rhat=1.001,
                       ess_bulk=500.,ess_tail=500.,mcse=.01,status='candidate_ready')
        summaries={key:dict(precision) for key in ['primary',*[str(i) for i in range(9)]]}
        value,indicators,timing=scalar_finish(result,summaries)
        self.assertEqual(value.status,'candidate_ready');self.assertEqual(value.probability,.7)
        self.assertEqual(value.primary.model_dump(),precision)
        self.assertEqual(tuple((cell.delta0,cell.delta1) for cell in value.cells),CELLS)
        self.assertTrue(all(cell.precision.model_dump()==precision for cell in value.cells))
        self.assertEqual(value.request_sha256,sha(request.model_dump(mode='json')))
        self.assertEqual((value.target_id,value.context_id,value.context_version),('UNIT-07','UNIT-context',1))
        self.assertIs(value.serving_authority,False);self.assertEqual(indicators,{'inert':'no arrays'})
        self.assertEqual(timing,dict(inert=True))

    def test_actual_constant_chain_scalar_updates_remain_unready_point_five(self):
        request=S2Request.model_validate(wire());result=construct(request)
        precision=dict(probability=1.,half_probability=1.,constant_chain=True,rhat=None,
                       ess_bulk=None,ess_tail=None,mcse=None,status='probability_unready_constant_chain')
        summaries={key:dict(precision) for key in ['primary',*[str(i) for i in range(9)]]}
        value,_,_=scalar_finish(result,summaries)
        self.assertEqual(value.status,'probability_unready');self.assertEqual(value.probability,.5)
        self.assertTrue(value.primary.constant_chain)
        self.assertTrue(all(cell.precision.status=='probability_unready_constant_chain' for cell in value.cells))
        self.assertIs(value.serving_authority,False)
