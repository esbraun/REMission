"""Scalar dispatch and source isolation controls; no worker/science execution."""
import ast
import importlib.util
import json
from pathlib import Path
import sys
import unittest

from contracts.domain.analysis import canonical
from contracts.domain.borrowing import parse_input,parse_result
from contracts.domain.protocol_request import make_boundary_input
from tests.contracts.test_nof1_app import product


class Nof1Dispatch(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0,str(Path('tooling/foundation').resolve()))
        import analysis_dispatcher
        cls.dispatcher=analysis_dispatcher

    def test_only_distinct_admitted_N_input_selects_N_file_worker(self):
        p=product();value=p.model_dump(mode='json')
        self.assertEqual(parse_input(canonical(value)),p)
        self.dispatcher.require_dispatchable(value)
        self.assertEqual(self.dispatcher.worker_module(value),'services.learner.nof1_worker')
        value['purpose']='N0'
        with self.assertRaises(ValueError):self.dispatcher.require_dispatchable(value)
        closed=make_boundary_input(p.histories,p.purpose,'boundary',p.run.model_dump(),p.request.context.seed.model_dump())
        with self.assertRaisesRegex(ValueError,'not executable'):self.dispatcher.require_dispatchable(closed.model_dump(mode='json'))

    def test_existing_worker_modules_keep_explicit_routes(self):
        self.assertEqual(self.dispatcher.worker_module({'kind':'poc_support_s1_input'}),'services.learner.support_s1_worker')
        self.assertEqual(self.dispatcher.worker_module({'kind':'poc_visit_cohort_input'}),'services.learner.analysis_worker')
        self.assertEqual(self.dispatcher.worker_module({'kind':'poc_visit_input'}),'services.learner.analysis_worker')

    def test_foundation_and_N_entry_point_have_no_top_level_science_import(self):
        denied={'numpy','pymc','pytensor','arviz','arviz_stats','scipy','statsmodels','xarray','methods'}
        paths=[*Path('services/foundation').glob('*.py'),Path('contracts/domain/nof1_app.py'),
            Path('services/learner/nof1_worker.py'),Path('services/learner/nof1_artifacts.py')]
        for path in paths:
            tree=ast.parse(path.read_text(encoding='utf-8'),filename=str(path))
            imports=[n for n in tree.body if isinstance(n,(ast.Import,ast.ImportFrom))]
            modules=[name.name.split('.')[0] for n in imports if isinstance(n,ast.Import) for name in n.names]
            modules += [n.module.split('.')[0] for n in imports if isinstance(n,ast.ImportFrom) and n.module]
            with self.subTest(path=str(path)):self.assertFalse(denied.intersection(modules))
        self.assertFalse(denied.intersection(sys.modules))


if __name__=='__main__':unittest.main()
