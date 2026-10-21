"""Actual service products, immutable admission, strict prefix and worker paths."""
from dataclasses import replace
from datetime import datetime,timedelta,timezone
import copy,json,os,shutil,subprocess,sys
from pathlib import Path
import unittest
from fastapi.testclient import TestClient
from contracts.runs.common import canonical,sha256
from contracts.service.live_safety import TrustedLiveSafetyAuthority
from contracts.service.live_safety_admission import FACTS,fold,verify_live_safety
from services.foundation.app import create_app
from services.learner.export_observed import admit,admit_live_safety
from services.learner.worker import dispatch_product,read_live_safety_export
import test_live_hold as workflow

NOW=workflow.NOW


class LiveSafetyProductTests(unittest.TestCase):
    setUp=workflow.LiveWorkflowTests.setUp
    tearDown=workflow.LiveWorkflowTests.tearDown
    login=workflow.LiveWorkflowTests.login
    headers=workflow.LiveWorkflowTests.headers
    enter=workflow.LiveWorkflowTests.enter
    review_input=workflow.LiveWorkflowTests.review_input

    def export(self,key='product',cutoff=NOW+timedelta(microseconds=1),fault=None):
        settings=replace(self.settings,clock=lambda:NOW+timedelta(hours=1),fault=fault)
        with TestClient(create_app(settings),base_url=workflow.ORIGIN,raise_server_exceptions=False) as client:
            self.login(client)
            result=client.post('/api/patients/SYN-02/live-safety-exports',json=dict(schema_version='1.0.0',contract='LIVE-HOLD-01',synthetic=True,cutoff=cutoff.isoformat()),headers=self.headers(key,client))
        with self.store.transaction() as db:
            row=db.execute('SELECT * FROM live_export_receipts WHERE key=?',(key,)).fetchone()
        if row is None:return result,None,None
        authority=TrustedLiveSafetyAuthority.model_validate_json(row['authority'])
        return result,self.root/'exports'/authority.export_id,authority

    def mutable_copy(self,root,name):
        destination=self.root/name
        shutil.copytree(root,destination)
        for path in destination.iterdir():path.chmod(0o600)
        return destination

    def rewritten(self,root,authority,name,*,fact_edit=None,manifest_edit=None,observed_edit=None,resign=False):
        destination=self.mutable_copy(root,name)
        manifest=json.loads((destination/'manifest.json').read_bytes())
        if fact_edit:
            facts=json.loads((destination/'live-hold-facts.json').read_bytes());fact_edit(facts)
            raw=canonical(facts);(destination/'live-hold-facts.json').write_bytes(raw)
            manifest['facts'].update(sha256=sha256(raw),bytes=len(raw),count=len(facts))
        if observed_edit:
            value=json.loads((destination/'observed-projection.json').read_bytes());observed_edit(value)
            raw=canonical(value);(destination/'observed-projection.json').write_bytes(raw)
            manifest['observed_projection'].update(sha256=sha256(raw),bytes=len(raw))
        if manifest_edit:manifest_edit(manifest)
        raw=canonical(manifest);(destination/'manifest.json').write_bytes(raw)
        if resign:
            # Explicit adversarial contract fixture: exercise structure beyond the
            # real immutable out-of-band manifest hash, never promote this trust.
            authority=authority.model_copy(update={'manifest_sha256':sha256(raw)})
        return destination,authority

    def test_before_baseline_is_unknown_and_receipt_equality_is_strict(self):
        self.enter()
        cases=[('2026-10-21T09:00:00+00:00','unknown',0),('2026-10-21T09:00:00.000001+00:00','not_held',1),
            ('2026-10-21T12:00:00+00:00','not_held',1),('2026-10-21T12:00:00.000001+00:00','held',2)]
        for index,(cutoff,status,count) in enumerate(cases):
            with self.subTest(cutoff=cutoff):
                response,root,authority=self.export('boundary-'+str(index),datetime.fromisoformat(cutoff))
                self.assertEqual(response.status_code,200,response.text)
                context=read_live_safety_export(root,authority)
                self.assertEqual((context.independent_hold_status,len(context.visible_operations)),(status,count))

    def test_whole_manifest_hash_and_exact_three_file_roster_fail_closed(self):
        self.enter();response,root,authority=self.export();self.assertEqual(response.status_code,200,response.text)
        for name,mutate in [('tail',lambda fs:fs.pop()),('middle',lambda fs:fs.pop(0)),('reorder',lambda fs:fs.reverse()),
            ('duplicate',lambda fs:fs.append(copy.deepcopy(fs[-1])))]:
            with self.subTest(name=name):
                destination,trust=self.rewritten(root,authority,name,fact_edit=mutate)
                with self.assertRaisesRegex(ValueError,'untrusted live manifest'):read_live_safety_export(destination,trust)
        extra=self.mutable_copy(root,'extra');(extra/'authority.json').write_text('{}')
        with self.assertRaisesRegex(ValueError,'exactly three'):read_live_safety_export(extra,authority)
        link=self.mutable_copy(root,'symlink');(link/'live-hold-facts.json').unlink();(link/'live-hold-facts.json').symlink_to(root/'live-hold-facts.json')
        with self.assertRaisesRegex(ValueError,'unsafe live artifact'):read_live_safety_export(link,authority)

    def test_strict_structure_rejects_gap_duplicate_future_foreign_and_wrong_fold(self):
        self.enter();_,root,authority=self.export()
        cases=[('gap',lambda fs:fs[-1].update(patient_sequence=4),None),
            ('duplicate-op',lambda fs:fs[-1].update(operation_id=fs[0]['operation_id']),None),
            ('future-receipt',lambda fs:fs[-1].update(recorded_at='2026-10-21T12:00:00.000001Z',available_at='2026-10-21T12:00:00.000001Z'),None),
            ('foreign-patient',lambda fs:fs[-1].update(patient_id='SYN-01'),None),
            ('wrong-fold',None,lambda m:m.update(independent_hold_status='not_held'))]
        for name,facts,manifest in cases:
            with self.subTest(name=name):
                destination,trust=self.rewritten(root,authority,name,fact_edit=facts,manifest_edit=manifest,resign=True)
                with self.assertRaises(ValueError):read_live_safety_export(destination,trust)

    def test_nested_and_authority_bindings_and_observed_only_paths_reject_live_product(self):
        self.enter();_,root,authority=self.export()
        for field,value in [('source_commit','b'*40),('snapshot_id','foreign-snapshot'),('authority_generation',8),('service_instance_id','foreign-instance')]:
            with self.subTest(field=field):
                with self.assertRaisesRegex(ValueError,'authority binding mismatch'):
                    read_live_safety_export(root,authority.model_copy(update={field:value}))
        destination,trust=self.rewritten(root,authority,'nested',observed_edit=lambda value:value.update(patient_id='SYN-01'),resign=True)
        trust=trust.model_copy(update={'observed_sha256':sha256((destination/'observed-projection.json').read_bytes())})
        with self.assertRaisesRegex(ValueError,'nested patient/cutoff'):read_live_safety_export(destination,trust)
        destination,trust=self.rewritten(root,authority,'schema',manifest_edit=lambda m:m['service_contract'].update(sha256='f'*64),resign=True)
        with self.assertRaisesRegex(ValueError,'schema/spec'):read_live_safety_export(destination,trust)
        with self.assertRaises(ValueError):admit(root/'manifest.json',self.root/'forbidden-observed.json')
        with self.assertRaises(ValueError):admit(root/'live-hold-facts.json',self.root/'forbidden-facts.json')
        self.assertFalse((self.root/'forbidden-observed.json').exists());self.assertFalse((self.root/'forbidden-facts.json').exists())
        with self.assertRaises(ValueError):read_live_safety_export(root,authority.model_copy(update={'allow_contract_fixture':False}))

    def test_fold_rejects_authority_jump_while_active_and_weakened_reasons(self):
        self.enter();_,root,_=self.export()
        facts=json.loads((root/'live-hold-facts.json').read_bytes())
        weakened=copy.deepcopy(facts[-1]);weakened['patient_sequence']=3;weakened['previous_fact_sha256']='a'*64;weakened['operation_id']='new-op'
        weakened['operation']['action']='strengthen';weakened['operation']['reason_codes']=[]
        with self.assertRaises(ValueError):fold(FACTS.validate_json(canonical(facts+[weakened])))
        weakened['operation']['reason_codes']=['experimental_stability_review']
        with self.assertRaisesRegex(ValueError,'removed active reason'):fold(FACTS.validate_json(canonical(facts+[weakened])))
        jumped=copy.deepcopy(weakened);jumped['operation']['reason_codes']=['clinician_concern'];jumped['authority_generation']=2
        with self.assertRaisesRegex(ValueError,'authority'):
            fold(FACTS.validate_json(canonical(facts+[jumped])))

    def test_export_commit_faults_and_response_loss_recover_original_three_files(self):
        self.enter()
        def before(name):
            if name=='before_live_export_commit':raise RuntimeError('controlled precommit export failure')
        response,root,_=self.export('before',fault=before)
        self.assertEqual(response.status_code,500);self.assertIsNone(root)
        self.assertFalse(self.settings.live_export_root.exists())
        def after(name):
            if name=='after_live_export_commit':raise RuntimeError('controlled postcommit export response loss')
        response,root,authority=self.export('after',fault=after)
        self.assertEqual(response.status_code,500);self.assertFalse(root.exists())
        response,recovered,repeated=self.export('after')
        self.assertEqual(response.status_code,200,response.text);self.assertEqual(root,recovered);self.assertEqual(authority,repeated)
        self.assertEqual({p.name for p in recovered.iterdir()},{'manifest.json','observed-projection.json','live-hold-facts.json'})
        original={p.name:p.read_bytes() for p in recovered.iterdir()}
        self.export('after');self.assertEqual(original,{p.name:p.read_bytes() for p in recovered.iterdir()})

    def test_actual_consumer_admit_worker_cli_and_dispatcher(self):
        self.enter();_,root,authority=self.export()
        admitted=self.root/'admitted'
        context=admit_live_safety((root/'manifest.json').read_bytes(),root,admitted,authority)
        self.assertEqual(context.independent_hold_status,'held')
        self.assertEqual({p.name:p.read_bytes() for p in root.iterdir()},{p.name:p.read_bytes() for p in admitted.iterdir()})
        authority_path=self.root/'trusted-authority.json';authority_path.write_text(authority.model_dump_json())
        result=subprocess.run([sys.executable,'-m','services.learner.worker','--product','live-safety','--root',str(admitted),'--authority',str(authority_path)],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr);self.assertEqual(json.loads(result.stdout)['independent_hold_status'],'held')
        self.assertEqual(dispatch_product(required_product=('LIVE-SAFETY-EXPORT','1.0.0'),worker_capabilities=[('LIVE-SAFETY-EXPORT','1.0.0')],root=admitted,authority=authority).independent_hold_status,'held')
        for capabilities,source,trust in [([],root,authority),([('LIVE-SAFETY-EXPORT','1.0.0')],None,authority),([('LIVE-SAFETY-EXPORT','1.0.0')],root,None)]:
            with self.assertRaises(ValueError):dispatch_product(required_product=('LIVE-SAFETY-EXPORT','1.0.0'),worker_capabilities=capabilities,root=source,authority=trust)


if __name__=='__main__':unittest.main()
