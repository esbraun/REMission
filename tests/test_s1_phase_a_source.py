"""Protect exactly authorized authority/carrier/job-field changes and old guards."""
import ast
from copy import deepcopy
import json,re,tempfile
from pathlib import Path
import unittest
import test_s1_genuine_source as prior
host=prior.host;driver=prior.driver;ROOT=prior.ROOT;BASELINE=None

def child():
    return dict(kind='S1_GENUINE_SUBMIT_EXPORT_V1',executable=True,namespace=driver.NAMESPACE,volume=driver.VOLUME,
        key=driver.KEY,cutoff_day=84,members=12,no_claim_or_fit=True,store_instance='store-unit',authority_generation=1,
        owner_id='owner-unit',archive_id='archive-unit',archive_export_id='export-unit',admission_sha256='a'*64,
        source_commit='b'*40,authority_mode='EXTERNAL_ROOT_EXACT_ONCE_AFTER_SOURCE_OP',request_seconds=180,private_export_cap=16777216)
def function(tree,name):return next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name)

class PhaseASourceTests(unittest.TestCase):
    def test_external_authority_only_no_fabricated_current_proofs(self):
        driver.admit(child());host.admit(prior.spec())
        for changes in ({'authority_mode':'AUTOMATIC'},{'root_go':'e'*64},{'source_review':'e'*40},{'operation_review':None}):
            with self.subTest(changes=changes),self.assertRaises(ValueError):driver.admit(dict(child(),**changes))
            with self.subTest(host_changes=changes),self.assertRaises(ValueError):host.admit(dict(prior.spec(),**changes))
    def test_existing_child_selection_boundaries_still_refuse(self):
        for changes in ({'members':11},{'members':True},{'cutoff_day':42},{'key':'fresh-retry-key'},
            {'owner_id':None},{'archive_id':None},{'authority_generation':True},{'no_claim_or_fit':False}):
            with self.subTest(changes=changes),self.assertRaises(ValueError):driver.admit(dict(child(),**changes))
    def test_normal_auth_CSRF_intent_singlePOST_export_run_exact_inverse(self):
        current=ast.parse((ROOT/'tooling/foundation/s1_genuine_submit.py').read_bytes());baseline=ast.parse(BASELINE)
        # No run/auth/HTTP/timer/private-persistence body changed at all.
        for name in ('run','invoke','private_once','emit','run_binding','protected_binding','read_only_connection','selected_owner'):
            self.assertEqual(ast.dump(function(current,name)),ast.dump(function(baseline,name)),name)
        text=ast.unparse(function(current,'run'))
        self.assertLess(text.index("login['principal']['id'] == spec['owner_id']"),text.index('submit_export('))
        self.assertIn("'X-CSRF-Token': csrf",text);self.assertIn('export_queued_request(',text)
        self.assertNotIn('claim(',text);self.assertNotIn('fit(',text)
    def test_submit_export_inverse_only_job_format_and_output_field(self):
        current=ast.parse((ROOT/'tooling/foundation/s1_genuine_submit.py').read_bytes());baseline=ast.parse(BASELINE)
        text=ast.unparse(function(current,'submit_export'))
        restored=text.replace("re.fullmatch('analysis-[a-f0-9]{32}', proof['attempt_id']) is not None","bool(proof['attempt_id'])")
        restored=restored.replace("job_id=proof['attempt_id'], ",'')
        self.assertEqual(ast.dump(ast.parse(restored)),ast.dump(ast.Module(body=[function(baseline,'submit_export')],type_ignores=[])))
    def test_genuine_job_identifier_from_original_proof_only(self):
        result,_=prior.SubmitTests().flow()
        self.assertEqual(result['job_id'],prior.proof()['attempt_id'])
        self.assertEqual(set(result),{'status','members','cutoff_day','job_id','response_confirmed','original_receipt_resolved','claim','fit'})
        different='analysis-'+'b'*32
        with self.assertRaises(ValueError):prior.SubmitTests().flow(resolve=lambda *_:dict(prior.proof(),attempt_id=different,active_attempts=[dict(attempt_id=different,status='queued')]))
    def test_bad_job_identifier_never_saved_as_success(self):
        for value in (None,True,12,'job-unit','analysis-'+'A'*32,'analysis-'+'a'*31,'analysis-'+'a'*33):
            proof=prior.proof();proof['attempt_id']=value;proof['active_attempts']=[dict(attempt_id=value,status='queued')]
            with self.subTest(value=value),self.assertRaises(ValueError):prior.SubmitTests().flow(resolve=lambda *_:proof)
    def test_no_input_hash_original_key_or_private_values_in_public_result(self):
        proof=prior.proof();proof.update(input={'private_value':'SECRET_SENTINEL'},input_sha256='SECRET_SENTINEL',history_sha256='SECRET_SENTINEL')
        result,_=prior.SubmitTests().flow(resolve=lambda *_:proof)
        self.assertNotIn('SECRET_SENTINEL',json.dumps(result));self.assertNotIn(driver.KEY,json.dumps(result))
        self.assertFalse({'receipt_key','input_sha256','history_sha256','owner_id','selection'}&set(result))
    def test_closed_public_job_field_rejects_missing_extra_or_bad_type(self):
        self.assertEqual(host.public_rows(prior.encoded([prior.final()]))[-1]['job_id'],prior.JOB)
        for value in (None,False,'analysis-'+'a'*33,'analysis-'+'A'*32):
            with self.subTest(value=value),self.assertRaises(ValueError):host.public_rows(prior.encoded([dict(prior.final(),job_id=value)]))
        value=prior.final();value.pop('job_id')
        with self.assertRaises(ValueError):host.public_rows(prior.encoded([value]))
        with self.assertRaises(ValueError):host.public_rows(prior.encoded([dict(prior.final(),receipt_key=driver.KEY)]))
    def test_exact_three_mounts_no_archive_artifact_root(self):
        args,mounts=host.argv(prior.spec(),Path('C:/public-unit/packet'))
        self.assertEqual([v[2] for v in mounts],['/data','/operation','/private/auth.json'])
        self.assertTrue(mounts[1][3] and mounts[2][3]);self.assertFalse(mounts[0][3])
        for field in ('public_archive_path','public_authority_path'):
            with self.assertRaises(ValueError):host.admit(dict(prior.spec(),**{field:'C:/public-unit/old-103MB-root'}))
    def test_fixed_five_leaf_submit_carrier_prevents_import_or_root_fallback(self):
        names=('s1_genuine_submit.py','submit-spec.json','archive-config.json','support-manifest.json','support-authority.json')
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            for name in names:(root/name).write_bytes(b'public-unit')
            host.checked_submit_carrier(root)
            (root/'sqlite3.py').write_text('raise AssertionError("SECRET_SENTINEL")')
            with self.assertRaises(ValueError):host.checked_submit_carrier(root)
    def test_actual_sameStore_artifact_path_has_no_filesystem_fallback(self):
        tree=ast.parse((ROOT/'services/foundation/support_archive.py').read_bytes())
        text=ast.unparse(function(tree,'read_support_history'))
        self.assertIn('FROM observed_archive_artifacts WHERE archive_id=? AND path=?',text)
        self.assertNotIn('read_bytes',text);self.assertNotIn('Path(',text)
        support=ast.parse((ROOT/'services/foundation/support_analysis.py').read_bytes())
        self.assertIn('for raw, _root, a in',ast.unparse(function(support,'authority_for')))
        self.assertIn('read_support_history(db, owner, patient',ast.unparse(function(support,'prepare')))
    def test_original_service_current_Hstar_versions_config_queue_and_export_gates_unchanged(self):
        support=(ROOT/'services/foundation/support_analysis.py').read_text()
        self.assertIn('for patient in sorted(index.members)',support)
        self.assertIn('same_version_history_changed',support)
        self.assertIn('one_exact_reviewed_queued_S1_attempt_required',support)
        self.assertIn('exact_S1_submission_receipt_required',support)
        analysis=(ROOT/'services/foundation/analysis.py').read_text()
        self.assertIn('with store.transaction() as db:',analysis)

if __name__=='__main__':unittest.main()
