"""Deterministic temporary-filesystem checks; no image or native child runs."""
from contextlib import redirect_stderr
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('image03_probe',ROOT/'tooling/foundation/nof1_image01_probe.py')
probe=importlib.util.module_from_spec(spec);spec.loader.exec_module(probe)

class ProjectClosureControls(unittest.TestCase):
    def setUp(self):
        folder=ROOT/'artifacts/shared-image03-probe-tests';folder.mkdir(parents=True,exist_ok=True)
        self.temporary=tempfile.TemporaryDirectory(dir=folder);self.addCleanup(self.temporary.cleanup)
        self.root=Path(self.temporary.name);self.expected={}

    def known(self,name,raw):
        path=self.root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
        self.expected[str(path)]=hashlib.sha256(raw).hexdigest();return path

    def failure(self):
        stream=io.StringIO()
        with redirect_stderr(stream),self.assertRaisesRegex(ValueError,'complete parent-plus-overlay'):
            probe.check_project_source(self.root,self.expected)
        return stream.getvalue(),json.loads(stream.getvalue())

    def test_exact_public_manifest_and_known_files_pass_without_output(self):
        raw=subprocess.check_output(['git','show','8879d91eb59c3bc30761d831ac040a534dae1d00'],cwd=ROOT,timeout=15)
        self.assertEqual(len(raw),77023)
        self.assertEqual(hashlib.sha256(raw).hexdigest(),'fc607c0fb4b61283e48e6279bf75f1c81e1a8d0ec24a8894d3e092b4c1822836')
        self.known('role-copy-manifest.json',raw);self.known('source.py',b'known')
        stream=io.StringIO()
        with redirect_stderr(stream):actual=probe.check_project_source(self.root,self.expected)
        self.assertEqual(actual,self.expected);self.assertEqual(stream.getvalue(),'')

    def test_missing_extra_changed_known_bytes_fail_without_unknown_read_or_hash(self):
        missing=self.known('missing.py',b'missing');missing.unlink()
        changed=self.known('changed.py',b'original');changed.write_bytes(b'changed')
        extra=self.root/'unexpected.py';secret=b'UNKNOWN_CONTENT_MUST_NOT_APPEAR';extra.write_bytes(secret)
        original=Path.read_bytes
        def public_only(path):
            if path==extra:raise AssertionError('unknown file content read')
            return original(path)
        with patch.object(Path,'read_bytes',public_only):raw,value=self.failure()
        self.assertEqual(value['counts'],dict(missing=1,extra=1,hash_mismatch=1))
        self.assertEqual(value['missing'][0]['path'],'missing.py')
        self.assertEqual(value['extra'],[dict(path='unexpected.py',path_truncated=False,type='regular',bytes=len(secret))])
        mismatch=value['hash_mismatch'][0]
        self.assertEqual(mismatch['expected_sha256'],hashlib.sha256(b'original').hexdigest())
        self.assertEqual(mismatch['actual_sha256'],hashlib.sha256(b'changed').hexdigest())
        self.assertNotIn(secret.decode(),raw);self.assertNotIn(hashlib.sha256(secret).hexdigest(),raw)
        self.assertFalse(value['truncated'])

    def test_original_omitted_manifest_is_an_extra_until_explicitly_declared(self):
        path=self.known('role-copy-manifest.json',b'public fixture');digest=self.expected.pop(str(path))
        _,value=self.failure();self.assertEqual(value['counts']['extra'],1)
        self.expected[str(path)]=digest
        self.assertEqual(probe.check_project_source(self.root,self.expected),self.expected)

    def test_failure_projection_is_deterministic_capped_and_never_success(self):
        for index in range(200):self.expected[str(self.root/(str(index).zfill(3)+'x'*300))]='a'*64
        first,value=self.failure();second,_=self.failure()
        self.assertEqual(first,second);self.assertLessEqual(len(first.encode()),16384)
        self.assertEqual(value['counts']['missing'],200);self.assertTrue(value['truncated'])
        self.assertLessEqual(sum(len(value[key]) for key in ('missing','extra','hash_mismatch')),64)
        self.assertEqual(len(value['missing'])+value['omitted']['missing'],200)
        self.assertTrue(all(row['path_truncated'] for row in value['missing']))

    def test_known_read_error_remains_distinct_and_emits_no_mismatch_projection(self):
        self.known('known.py',b'known');stream=io.StringIO()
        with patch.object(Path,'read_bytes',side_effect=OSError('source read failed')),redirect_stderr(stream):
            with self.assertRaisesRegex(OSError,'source read failed'):probe.check_project_source(self.root,self.expected)
        self.assertEqual(stream.getvalue(),'')

    def test_symlink_rejection_remains_distinct_where_supported(self):
        target=self.known('known.py',b'known');link=self.root/'linked.py'
        try:link.symlink_to(target)
        except OSError as error:self.skipTest('local symlink permission unavailable: '+str(error))
        stream=io.StringIO()
        with redirect_stderr(stream),self.assertRaisesRegex(ValueError,'project source symlink denied'):
            probe.check_project_source(self.root,self.expected)
        self.assertEqual(stream.getvalue(),'')

    def test_existing_pycache_exclusion_is_unchanged(self):
        self.known('known.py',b'known');cache=self.root/'__pycache__';cache.mkdir();(cache/'x.pyc').write_bytes(b'cache')
        self.assertEqual(probe.check_project_source(self.root,self.expected),self.expected)
