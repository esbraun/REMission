"""Fixed packaging payload in temporary filesystems/doubles; no native child."""
from contextlib import redirect_stdout
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import stat
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('image04',ROOT/'tooling/foundation/nof1_image01.py')
op=importlib.util.module_from_spec(spec);spec.loader.exec_module(op)

class PackagingControls(unittest.TestCase):
    def setUp(self):
        folder=ROOT/'artifacts/shared-image04-packaging-tests';folder.mkdir(parents=True,exist_ok=True)
        self.temporary=tempfile.TemporaryDirectory(dir=folder);self.addCleanup(self.temporary.cleanup)
        self.root=Path(self.temporary.name);self.target=self.root/'app/web/dist/assets/index-_kvz3Qwx.js'
        self.target.parent.mkdir(parents=True)

    def run_payload(self):
        output=io.StringIO()
        # Only the literal Path constructor is redirected; the frozen code is
        # executed unchanged, in process, with no unknown content access.
        def literal(value):
            self.assertEqual(value,'/app/web/dist/assets/index-_kvz3Qwx.js')
            return self.target
        with patch('pathlib.Path',side_effect=literal),redirect_stdout(output):
            exec(compile(op.UNLINK_CODE,'<fixed-packaging>','exec'),{})
        self.assertLess(len(output.getvalue().encode()),512)
        return json.loads(output.getvalue())

    def test_literal_unlink_preserves_known_siblings_without_reading_target(self):
        self.target.write_bytes(b'unknown bytes never read')
        sibling=self.target.parent/'index-ddHm7Bwl.js';sibling.write_bytes(b'known')
        with patch.object(Path,'read_bytes',side_effect=AssertionError('content read forbidden')):
            self.assertEqual(self.run_payload()['packaging_unlink'],'removed')
        self.assertFalse(self.target.exists());self.assertEqual(sibling.read_bytes(),b'known')

    def test_absent_target_and_missing_parent_are_bounded_already_absent(self):
        self.assertEqual(self.run_payload()['packaging_unlink'],'already_absent')
        self.target.parent.rmdir()
        self.assertEqual(self.run_payload()['packaging_unlink'],'already_absent')

    def test_nonregular_target_and_ancestor_are_rejected(self):
        self.target.mkdir()
        with self.assertRaisesRegex(ValueError,'target'):self.run_payload()
        self.target.rmdir();self.target.parent.rmdir();self.target.parent.write_bytes(b'file')
        with self.assertRaisesRegex(ValueError,'ancestor'):self.run_payload()

    def test_symlink_modes_including_dangling_are_never_absent(self):
        original=Path.lstat
        for linked in (self.target,self.target.parent):
            def lstat(path,**kwargs):
                if path==linked:return SimpleNamespace(st_mode=stat.S_IFLNK|0o777)
                return original(path,**kwargs)
            with self.subTest(path=linked),patch.object(Path,'lstat',lstat):
                with self.assertRaisesRegex(ValueError,'ordinary'):self.run_payload()

    def test_real_dangling_symlink_rejected_where_supported(self):
        try:self.target.symlink_to(self.root/'missing')
        except OSError as error:self.skipTest('local symlink permission unavailable: '+str(error))
        with self.assertRaisesRegex(ValueError,'target'):self.run_payload()

    def test_permission_and_unlink_errors_propagate_without_absence_claim(self):
        self.target.write_bytes(b'unknown')
        for method in ('lstat','unlink'):
            with self.subTest(method=method),patch.object(Path,method,side_effect=PermissionError('denied')):
                with self.assertRaisesRegex(PermissionError,'denied'):self.run_payload()
        self.assertTrue(self.target.exists())

    def test_recipe_has_only_two_literal_runs_with_immediate_user_restore(self):
        bindings=json.loads(op.git(ROOT,'show',op.BINDINGS_BLOB))
        recipe=op.recipe(bindings['roles']).splitlines();runs=[]
        for index,line in enumerate(recipe):
            if line.startswith('RUN '):
                self.assertEqual(recipe[index-1],'USER 0:0')
                self.assertEqual(recipe[index+1],'USER 10001:10001')
                self.assertEqual(json.loads(line[4:]),['python','-I','-B','-c',op.UNLINK_CODE]);runs.append(index)
        self.assertEqual(len(runs),2)
        learner=recipe[recipe.index('FROM ${LEARNER_PARENT} AS learner'):recipe.index('FROM ${CONTROLS_PARENT} AS controls')]
        self.assertFalse(any(line.startswith(('RUN ','USER ')) for line in learner))

    def test_probes_use_exact_public_source_bytes_and_known_aliases_for_each_role(self):
        bindings=json.loads(op.git(ROOT,'show',op.BINDINGS_BLOB))
        expected={'/app/boundary_probe.py':('ba4c5e278db8d160dec3e88372bfb7ef9bb151c1',1658,'4fb5855d25caa03826e91c21492b389edde3c6a8d3acfa97ccf15b2561a72671'),
            '/app/observed_v2_probe.py':('a5d40caa380f19b98a688c301440a53953ce1352',7364,'dc773be79dd015a1c47426868e6e866755c7c60af88c1e5b39f04a8c24f75f41')}
        for role,item in bindings['roles'].items():
            for destination,(blob,size,digest) in expected.items():
                row=next(row for row in item['overlay'] if row['destination']==destination)
                raw=op.git(ROOT,'show',blob)
                self.assertEqual((row['git_blob'],len(raw),hashlib.sha256(raw).hexdigest()),(blob,size,digest))
                self.assertEqual(item['expected_project_source'][destination],digest)
