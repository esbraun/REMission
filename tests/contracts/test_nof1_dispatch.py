"""Scalar dispatch and source isolation controls; no worker/science execution."""
import ast
import importlib.util
import json
import posixpath
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

    def test_new_service_and_learner_source_imports_are_explicitly_copied(self):
        # Static COPY closure only; base/runtime APIs and actual images are not
        # qualified here. Reuse directories already copied by these images.
        for recipe,entries in (
                ('service.Dockerfile',('contracts/domain/nof1_app.py','contracts/domain/nof1_config.py','services/foundation/nof1_analysis.py')),
                ('learner.Dockerfile',('services/learner/nof1_worker.py','services/learner/nof1_artifacts.py',
                    'contracts/domain/nof1_app.py','contracts/domain/nof1_config.py'))):
            copied=set()
            for line in Path('tooling/foundation',recipe).read_text().splitlines():
                words=line.split()
                if not words or words[0]!='COPY' or words[1].startswith('--'):continue
                destination=words[-1]
                if not destination.startswith('/app/'):continue
                for name in words[1:-1]:
                    source=Path(name)
                    if source.is_dir():
                        copied.update(posixpath.join(destination[5:],str(p.relative_to(source)).replace('\\','/'))
                            for p in source.rglob('*.py'))
                    elif source.suffix=='.py':
                        copied.add(posixpath.join(destination[5:],source.name) if destination.endswith('/') else destination[5:])
            pending=list(entries);seen=set()
            while pending:
                name=pending.pop()
                if name in seen:continue
                seen.add(name)
                with self.subTest(recipe=recipe,module=name):self.assertIn(name,copied)
                tree=ast.parse(Path(name).read_text(encoding='utf-8'))
                package=Path(name).parent.parts
                for node in ast.walk(tree):
                    if not isinstance(node,ast.ImportFrom) or not node.module:continue
                    parts=((*package[:len(package)-node.level+1],*node.module.split('.'))
                        if node.level else tuple(node.module.split('.')))
                    candidate=Path(*parts).with_suffix('.py')
                    if parts[0] not in ('contracts','methods') or not candidate.is_file():continue
                    pending.append(candidate.as_posix())


if __name__=='__main__':unittest.main()
