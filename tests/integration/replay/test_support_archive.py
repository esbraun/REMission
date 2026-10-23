"""Structural admission/auth attacks only; no accepted-output/browser claim."""
from datetime import timedelta
import json
from pathlib import Path
import tempfile
import unittest
import os
import sqlite3

from fastapi.testclient import TestClient
from contracts.domain.evidence_v2 import exact_ref,projection_hash
from contracts.runs.common import Artifact,canonical,sha256
from contracts.runs.coverage_v2 import StageLedgerV2
from contracts.runs.support_research import SupportArchiveAuthority,SupportCompletion,StageVerifier,read_artifact,version_ref
from services.foundation.app import Settings,create_app
from services.foundation.cli import DEMO_PASSWORDS,seed,reset_password
from services.foundation.support_archive import admit_support_archive,verify_support_archive,read_support_history
from services.foundation.protocol import validate_support_v21
from services.foundation.store import canonical as store_canonical
from live_helpers import fresh_store
from support_archive_fixtures import build,history,START,WALL

ORIGIN='http://127.0.0.1:8765'


class SupportFixture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture_temp=tempfile.TemporaryDirectory();cls.package=build(Path(cls.fixture_temp.name))
        cls.verified=verify_support_archive(*cls.package)

    @classmethod
    def tearDownClass(cls):cls.fixture_temp.cleanup()


@unittest.skipUnless(os.name=='posix','Real Store admission requires the supported POSIX flock runtime; no host emulation')
class SupportArchiveTests(SupportFixture):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.store=fresh_store(Path(self.temp.name)/'fixture.sqlite')
        self.at=WALL+timedelta(seconds=1);self.store.clock=lambda:self.at;seed(self.store)
        self.settings=Settings(self.store.path,self.store.installed,clock=lambda:self.at,observed_archives={'structural':self.package},live_export_root=Path(self.temp.name)/'unused-exports')
        self.app=create_app(self.settings);self.client=TestClient(self.app,base_url=ORIGIN)
        self.login(self.client)

    def tearDown(self):self.client.close();self.temp.cleanup()

    def login(self,client,user='alice'):
        pre=client.get('/api/session').json()
        result=client.post('/api/login',json=dict(username=user,password=DEMO_PASSWORDS[user]),headers={'Origin':ORIGIN,'X-CSRF-Token':pre['csrf']})
        self.assertEqual(result.status_code,200,result.text)

    def headers(self,client=None):
        return {'Origin':ORIGIN,'X-CSRF-Token':(client or self.client).get('/api/session').json()['csrf'],'Idempotency-Key':'structural-key'}

    def admit(self):
        result=self.client.post('/api/observed-archives/structural',json=dict(mode='archive_only'),headers=self.headers())
        self.assertEqual(result.status_code,200,result.text);return result.json()

    def path(self,patient='STRUCT-00',mode='S1',day=14):
        return f'/api/patients/{patient}/observed-archives/structural-run:structural-cohort?mode={mode}&cutoff_day={day}'

    def test_atomic_intake_exact_reimport_panel_workspace_and_72_structural_replays(self):
        receipt=self.admit();self.assertEqual(receipt,self.admit());self.assertFalse(receipt['live_authority_granted'])
        self.assertEqual(receipt['qualification_scope'],'structural_fixture')
        panel=self.client.get('/api/patients').json();self.assertEqual(sum(bool(r['historical_support']) for r in panel['patients']),12)
        workspace=self.client.get('/api/patients/STRUCT-00').json();self.assertEqual(workspace['kind'],'restricted_support_historical')
        self.assertNotIn('snapshot',workspace)
        with self.store.transaction() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM observed_archives').fetchone()[0],1)
            self.assertEqual(db.execute('SELECT count(*) FROM observed_archive_artifacts').fetchone()[0],193)
            self.assertEqual(db.execute("SELECT count(*) FROM live_patient_journals WHERE patient_id LIKE 'STRUCT-%'").fetchone()[0],0)
            for t in self.package[2].descriptor.trajectories:
                for day in (14,42,84):
                    result=read_support_history(db,'alice',t.member_id,receipt['archive_id'],t.mode,day,self.package[2])
                    original=json.loads(read_artifact(self.package[1],t.projections[str(day)]))
                    self.assertEqual(result['projection'],original)
                    self.assertEqual(result['partition_id'],t.partition_id)
        s0=self.client.get(self.path(mode='S0'));s1=self.client.get(self.path(mode='S1'))
        self.assertEqual(s0.status_code,200,s0.text);self.assertEqual(s1.status_code,200,s1.text)
        self.assertNotEqual(s0.json()['partition_id'],s1.json()['partition_id'])
        self.assertEqual(self.client.get(self.path().split('?')[0]).status_code,409)

    def test_transaction_rolls_back_every_new_member_marker_and_archive(self):
        def fail(stage):
            if stage=='before_support_archive_commit':raise RuntimeError('structural rollback fault')
        with self.assertRaisesRegex(RuntimeError,'rollback fault'):
            admit_support_archive(self.store,*self.package,owner_id='alice',received_at=self.at,fault=fail)
        with self.store.transaction() as db:
            for table in ('patients','state_changes'):
                column='id' if table=='patients' else 'patient_id'
                self.assertEqual(db.execute(f"SELECT count(*) FROM {table} WHERE {column} LIKE 'STRUCT-%'").fetchone()[0],0)
            self.assertEqual(db.execute('SELECT count(*) FROM observed_archives').fetchone()[0],0)

    def test_foreign_last_member_and_interactive_identity_collision_rollback(self):
        # The first eleven creations must roll back when the last member collides.
        with self.store.transaction(write=True) as db:
            row=db.execute("SELECT * FROM patients WHERE id='SYN-B01'").fetchone()
            db.execute('INSERT INTO patients VALUES(?,?,?,?,?,?,?,?,?,?)',('STRUCT-11','bob',*tuple(row)[2:]))
        response=self.client.post('/api/observed-archives/structural',json=dict(mode='archive_only'),headers=self.headers())
        self.assertEqual(response.status_code,409,response.text)
        with self.store.transaction() as db:
            self.assertEqual(db.execute("SELECT count(*) FROM patients WHERE id LIKE 'STRUCT-%'").fetchone()[0],1)
            db.execute("SELECT 1")
        with self.store.transaction(write=True) as db:db.execute("UPDATE patients SET owner_id='alice' WHERE id='STRUCT-11'")
        self.assertEqual(self.client.post('/api/observed-archives/structural',json=dict(mode='archive_only'),headers=self.headers()).status_code,409)

    def test_all_member_ownership_checked_for_reads_reimport_and_other_account(self):
        self.admit();bob=TestClient(self.app,base_url=ORIGIN);self.login(bob,'bob')
        self.assertEqual(bob.get(self.path()).status_code,404)
        self.assertEqual(bob.post('/api/observed-archives/structural',json=dict(mode='archive_only'),headers=self.headers(bob)).status_code,409)
        with self.store.transaction(write=True) as db:db.execute("UPDATE patients SET owner_id='bob' WHERE id='STRUCT-11'")
        self.assertEqual(self.client.get(self.path()).status_code,409)
        self.assertEqual(self.client.get('/api/patients/STRUCT-00').status_code,409)
        self.assertEqual(self.client.post('/api/observed-archives/structural',json=dict(mode='archive_only'),headers=self.headers()).status_code,409)
        bob.close()

    def test_auth_csrf_expiry_and_password_revocation_apply_to_intake_and_reads(self):
        self.assertEqual(self.client.post('/api/observed-archives/structural',json=dict(mode='archive_only')).status_code,403)
        self.admit();anonymous=TestClient(self.app,base_url=ORIGIN)
        self.assertEqual(anonymous.get(self.path()).status_code,401);anonymous.close()
        self.at+=timedelta(seconds=1801)
        self.assertEqual(self.client.get(self.path()).status_code,401)
        self.login(self.client);reset_password(self.store,'alice','new structural password')
        self.assertEqual(self.client.get(self.path()).status_code,401)

    def test_all_patient_mutations_denied_and_existing_current_path_unchanged(self):
        self.admit()
        requests={
            'advance':dict(expected_version=1,mode='day'),
            'state':dict(expected_version=1,stage='ASSIGN-02',reason='structural attempt'),
            'analyses':dict(expected_version=1),
            'events':__import__('test_foundation').observed(patient='STRUCT-00'),
            'reports':dict(event_at=START.isoformat(),sleep_quality=6.,function=5.,diary_sleep_minutes=360.,note='fixture'),
            'approve':dict(decision_id='none',expected_patient_version=1,expected_state_version=1,expected_consent_version=1,expected_eligibility_version=1,
                mode='current',option='MED_A',rationale='fixture',follow_up_at=self.at.isoformat(),purpose='ordinary_treatment'),
            'live-safety-exports':dict(schema_version='1.0.0',contract='LIVE-HOLD-01',synthetic=True,cutoff=self.at.isoformat()),
            'nof1':dict(mode='current',action='withdraw',decision_id='none',expected_version=1,expected_state_version=1,expected_consent_version=1,expected_eligibility_version=1,rationale='fixture'),
            'randomize':{},
        }
        for endpoint,payload in requests.items():
            response=self.client.post('/api/patients/STRUCT-00/'+endpoint,json=payload,headers=self.headers())
            self.assertEqual(response.status_code,409,(endpoint,response.text));self.assertEqual(response.json()['code'],'historical_support_read_only')
        response=self.client.put('/api/patients/STRUCT-00/draft',json=dict(decision_id='none',expected_version=1,mode='current',option=None,rationale='',follow_up_at=''),headers=self.headers())
        self.assertEqual(response.status_code,409,response.text)
        self.assertEqual(self.client.get('/api/patients/STRUCT-00/live-safety-exports/unknown/manifest.json').status_code,409)
        ref=dict(record_id='fixture',payload_sha256='0'*64)
        forged=dict(schema_version='1.0.0',contract='LIVE-HOLD-01',synthetic=True,archive_id='structural-run:structural-cohort',
            partition_id='STRUCT-00-S1',bundle_ref=ref,trigger_refs=[ref])
        response=self.client.post('/api/patients/SYN-02/live-holds',json=forged,headers=self.headers())
        self.assertEqual(response.status_code,409,response.text);self.assertEqual(response.json()['code'],'historical_support_read_only')
        self.assertEqual(self.client.post('/api/observed-archives/structural',json=dict(mode='clinical_observation_import'),headers=self.headers()).status_code,409)
        current=self.client.get('/api/patients/SYN-02');self.assertEqual(current.status_code,200);self.assertIn('snapshot',current.json())
        response=self.client.post('/api/patients/SYN-02/state',json=dict(expected_version=current.json()['snapshot']['patient_version'],stage='ASSIGN-02',reason='Existing ordinary physician review'),headers=self.headers())
        self.assertEqual(response.status_code,200,response.text)

    def test_stored_artifact_manifest_and_entry_tampering_fail_closed(self):
        self.admit();t=self.package[2].descriptor.trajectories[0]
        # First prove normal storage rejects mutation. The remaining injections
        # explicitly simulate corrupt backing storage in this private fixture.
        with self.assertRaisesRegex(sqlite3.IntegrityError,'immutable_record'):
            with self.store.transaction(write=True) as db:db.execute('UPDATE observed_archive_artifacts SET payload=? WHERE path=?',(b'[]',t.history.path))
        with self.store.transaction(write=True) as db:
            db.execute('DROP TRIGGER immutable_observed_archive_artifacts_UPDATE')
            db.execute('UPDATE observed_archive_artifacts SET payload=? WHERE path=?',(b'[]',t.history.path))
        self.assertEqual(self.client.get(self.path(mode='S0')).status_code,409)
        with self.store.transaction(write=True) as db:
            db.execute('UPDATE observed_archive_artifacts SET payload=? WHERE path=?',(read_artifact(self.package[1],t.history),t.history.path))
            db.execute('DROP TRIGGER immutable_observed_archive_entries_UPDATE')
            db.execute('UPDATE observed_archive_entries SET raw_source=? WHERE archive_id=? AND partition_id=? AND record_id=?',(b'{}','structural-run:structural-cohort',t.partition_id,'consent'))
        self.assertEqual(self.client.get(self.path(mode='S0')).status_code,409)

    def test_stored_receipt_provenance_is_rechecked_against_trusted_configuration(self):
        receipt=self.admit()
        with self.store.transaction(write=True) as db:
            db.execute('DROP TRIGGER immutable_observed_archives_UPDATE')
            changed=dict(receipt,source_commit='f'*40)
            db.execute('UPDATE observed_archives SET receipt=? WHERE id=?',(store_canonical(changed),receipt['archive_id']))
        self.assertEqual(self.client.get(self.path()).status_code,409)
        self.assertEqual(self.client.post('/api/observed-archives/structural',json=dict(mode='archive_only'),headers=self.headers()).status_code,409)

    def test_descriptor_source_runtime_qualification_member_pair_and_hash_substitutions(self):
        raw,root,authority=self.package
        for field,value in (('source_commit','f'*40),('runtime',authority.descriptor.runtime.model_copy(update=dict(image_sha256='f'*64))),
                            ('members',['forged',*authority.descriptor.members[1:]])):
            changed=authority.model_copy(update=dict(descriptor=authority.descriptor.model_copy(update={field:value})))
            with self.assertRaises(ValueError):verify_support_archive(raw,root,changed)
        substituted=json.loads(raw);substituted['trajectories'][0]['paired_member_id']='forged'
        altered=canonical(substituted)
        with self.assertRaises(ValueError):verify_support_archive(altered,root,authority)
        self.admit()
        changed=authority.model_copy(update=dict(outcome_qualification=authority.producer_qualification.model_copy(update=dict(sha256='f'*64))))
        with self.assertRaises(ValueError):admit_support_archive(self.store,raw,root,changed,owner_id='alice',received_at=self.at)

class SupportProofTests(SupportFixture):
    def test_supplemental_public_inventory_exact_set_ids_and_immutable_original_index(self):
        raw,root,authority=self.package
        self.assertEqual((root/'manifest.json').read_bytes(),raw)
        proof=authority.supplemental_public_artifacts[0];target=root/proof.artifact.path;original=target.read_bytes()
        try:
            target.write_bytes(b'{}')
            with self.assertRaisesRegex(ValueError,'hash_or_size'):verify_support_archive(raw,root,authority)
        finally:target.write_bytes(original)
        omitted=authority.model_copy(update=dict(supplemental_public_artifacts=authority.supplemental_public_artifacts[1:]))
        with self.assertRaisesRegex(ValueError,'exact_qualified'):verify_support_archive(raw,root,omitted)
        extra=root/'unqualified.json'
        try:
            extra.write_bytes(b'{}')
            with self.assertRaisesRegex(ValueError,'exact_qualified'):verify_support_archive(raw,root,authority)
        finally:extra.unlink()
        value=authority.model_dump(mode='json')
        value['supplemental_public_artifacts'].append(value['supplemental_public_artifacts'][0])
        with self.assertRaisesRegex(ValueError,'duplicate'):SupportArchiveAuthority.model_validate_json(canonical(value))
        value=authority.model_dump(mode='json');value['supplemental_public_artifacts'][0]['partition_id']='foreign'
        with self.assertRaisesRegex(ValueError,'not_qualified'):SupportArchiveAuthority.model_validate_json(canonical(value))

    def test_host_configuration_discriminates_restricted_and_preserves_full_v2(self):
        from services.foundation.configuration import read_archives
        from observed_v2_fixtures import build as full_v2_fixture
        from contracts.runs.observed_v2 import ExportAuthorityV2
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);full=full_v2_fixture(root/'full-v2',hold=True)
            (root/'restricted-manifest.json').write_bytes(self.package[0]);(root/'restricted-authority.json').write_text(self.package[2].model_dump_json())
            (root/'full-manifest.json').write_bytes(full['raw']);(root/'full-authority.json').write_bytes(canonical(full['authority']))
            entries=[dict(export_id=prefix,manifest=str(root/(prefix+'-manifest.json')),artifact_root=str(self.package[1] if prefix=='restricted' else root/'full-v2'),authority=str(root/(prefix+'-authority.json'))) for prefix in ('restricted','full')]
            path=root/'config.json';path.write_bytes(canonical(entries));result=read_archives(path)
            self.assertEqual(result['restricted'][2],self.package[2]);self.assertIs(type(result['full'][2]),ExportAuthorityV2)

    def test_paths_links_and_changed_bytes_rejected(self):
        good=self.package[2].descriptor.trajectories[0].history
        for path in ('../escape.json','a/../b.json','C:/file.json','a\\b.json','a%2fb.json','CON.json'):
            with self.assertRaises(ValueError):Artifact.model_validate_json(canonical(good.model_dump(mode='json')|dict(path=path)))
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);source=root/'source.json';source.write_bytes(b'{}');link=root/'link.json'
            # Hard links are ordinary files with shared identity: deny them too.
            os.link(source,link)
            artifact=Artifact.model_validate_json(canonical(good.model_dump(mode='json')|dict(path='link.json',bytes=2,sha256=sha256(b'{}'))))
            with self.assertRaises(ValueError):read_artifact(root,artifact)
            if os.name=='posix':
                alias=root/'alias.json';alias.symlink_to(source)
                with self.assertRaisesRegex(ValueError,'symlink'):read_artifact(root,artifact.model_copy(update=dict(path='alias.json')))
        with self.assertRaises(ValueError):read_artifact(self.package[1],good.model_copy(update=dict(sha256='0'*64)))

    def test_independently_configured_descriptor_source_runtime_members_and_pairs(self):
        raw,root,authority=self.package
        for field,value in (('source_commit','f'*40),('runtime',authority.descriptor.runtime.model_copy(update=dict(image_sha256='f'*64))),
                            ('members',['forged',*authority.descriptor.members[1:]])):
            changed=authority.model_copy(update=dict(descriptor=authority.descriptor.model_copy(update={field:value})))
            with self.assertRaises(ValueError):verify_support_archive(raw,root,changed)
        for edit in ('source_commit','pairs','partition','hash'):
            index=json.loads(raw)
            if edit=='source_commit':index['source_commit']='f'*40
            elif edit=='pairs':index['trajectories'][0]['paired_member_id']='forged'
            elif edit=='partition':index['trajectories'][0]['partition_id']=index['trajectories'][1]['partition_id']
            else:index['trajectories'][0]['history']['sha256']='0'*64
            altered=canonical(index)
            with self.assertRaises(ValueError):verify_support_archive(altered,root,authority.model_copy(update=dict(manifest_sha256=sha256(altered))))

    def proof(self,full=None,ledgers=None,completions=None):
        trajectory=self.package[2].descriptor.trajectories[1];index=self.package[2].descriptor
        full=full or self.verified.histories[trajectory.partition_id]
        ledgers=ledgers if ledgers is not None else [StageLedgerV2.model_validate_json(canonical(r)) for r in json.loads(read_artifact(self.package[1],trajectory.stage_ledgers))]
        completions=completions if completions is not None else [SupportCompletion.model_validate_json(canonical(r)) for r in json.loads(read_artifact(self.package[1],trajectory.completions))]
        return StageVerifier(full,ledgers,completions,self.package[1],run_id=index.run_id,partition_id=trajectory.partition_id,
            source_commit=index.source_commit,runtime=index.runtime,frozen_plan_sha256=index.frozen_plan_sha256)

    def test_positive_empty_closures_omissions_partial_future_and_corrected_refs(self):
        positive=self.proof();full=positive.history;closure=next(r for r in full.records if r.kind=='support_stage_closure')
        self.assertEqual(len(positive(closure,START+timedelta(days=14))),1)
        empty_t=self.package[2].descriptor.trajectories[0];empty=self.verified.histories[empty_t.partition_id]
        empty_closure=next(r for r in empty.records if r.kind=='support_stage_closure');self.assertEqual(empty_closure.row_count,0)
        # Removing an empty completion is still missing proof, never zero.
        empty_proof=StageVerifier(empty,[],[],self.package[1],run_id='structural-run',partition_id=empty_t.partition_id,
            source_commit=self.package[2].descriptor.source_commit,runtime=self.package[2].descriptor.runtime,frozen_plan_sha256=self.package[2].descriptor.frozen_plan_sha256)
        with self.assertRaisesRegex(ValueError,'missing_or_substituted'):empty_proof(empty_closure,START+timedelta(days=14))
        with self.assertRaises(ValueError):self.proof(completions=[])(closure,START+timedelta(days=14))
        ledger=positive.ledgers[closure.stage_ledger.id];receipt=positive.completions[closure.completion_receipt.id]
        omitted=ledger.model_copy(update=dict(event_refs=[]))
        rebound=receipt.model_copy(update=dict(stage_ledgers=[version_ref(omitted) if r.id==ledger.id else r for r in receipt.stage_ledgers]))
        changed=closure.model_copy(update=dict(stage_ledger=version_ref(omitted),completion_receipt=version_ref(rebound),stage_event_refs=[],row_count=0))
        edited=history(full.patient_id,[changed if r.record_id==closure.record_id else r for r in full.records])
        with self.assertRaisesRegex(ValueError,'not_exhaustive'):
            self.proof(edited,[omitted if r.id==ledger.id else r for r in positive.ledgers.values()],[rebound])(changed,START+timedelta(days=14))
        event=next(r for r in full.records if r.record_id==closure.stage_event_refs[0].record_id)
        for change in (dict(available_at=START+timedelta(days=14),recorded_at=START+timedelta(days=14)),dict(patient_id='foreign')):
            with self.assertRaises(ValueError):
                edited=history(full.patient_id,[r.model_copy(update=change) if r.record_id==event.record_id else r for r in full.records])
                self.proof(edited)(closure,START+timedelta(days=14))
        correction=event.model_copy(update=dict(record_id='corrected',revision=2,supersedes=event.record_id,recorded_at=event.recorded_at+timedelta(seconds=1),available_at=event.available_at+timedelta(seconds=1)))
        with self.assertRaises(ValueError):self.proof(history(full.patient_id,[*full.records,correction]))(closure,START+timedelta(days=14))
        partial=receipt.model_copy(update=dict(status='partial',reason='structural interruption'))
        changed=closure.model_copy(update=dict(completion_receipt=version_ref(partial)))
        edited=history(full.patient_id,[changed if r.record_id==closure.record_id else r for r in full.records])
        with self.assertRaises(ValueError):self.proof(edited,completions=[partial])(changed,START+timedelta(days=14))

    def test_stage_source_runtime_and_cross_window_substitutions(self):
        proof=self.proof();full=proof.history;closure=next(r for r in full.records if r.kind=='support_stage_closure')
        receipt=proof.completions[closure.completion_receipt.id]
        for change in (dict(source_commit='f'*40),dict(runtime=receipt.runtime.model_copy(update=dict(image_sha256='f'*64))),dict(patient_id='foreign'),dict(partition_id='foreign')):
            altered=receipt.model_copy(update=change)
            changed=closure.model_copy(update=dict(completion_receipt=version_ref(altered)))
            edited=history(full.patient_id,[changed if r.record_id==closure.record_id else r for r in full.records])
            with self.assertRaisesRegex(ValueError,'foreign_or_changed_completion'):
                self.proof(edited,completions=[altered])(changed,START+timedelta(days=14))
        changed=closure.model_copy(update=dict(window_id='foreign'))
        edited=history(full.patient_id,[changed if r.record_id==closure.record_id else r for r in full.records])
        with self.assertRaisesRegex(ValueError,'window_mismatch'):self.proof(edited)(changed,START+timedelta(days=14))

    def test_known_probability_consent_and_hold_checks_are_not_inferred_from_projection_hash(self):
        full=self.proof().history;decision=next(r for r in full.records if r.kind=='support_decision')
        assign=next(r for r in full.records if r.record_id==decision.assignment_id)
        changed=assign.model_copy(update=dict(probability=.25))
        edited=history(full.patient_id,[changed if r.record_id==assign.record_id else r for r in full.records])
        with self.assertRaisesRegex(ValueError,'probability'):validate_support_v21(edited,decision,START+timedelta(days=14))
        consent=next(r for r in full.records if r.kind=='consent')
        for change in (dict(expires_at=START),dict(withdrawn_at=START),dict(oversight_status='expired')):
            changed=consent.model_copy(update=change)
            edited=history(full.patient_id,[changed if r.record_id==consent.record_id else r for r in full.records])
            rebound=decision.model_copy(update=dict(context_projection_sha256=projection_hash(edited,START)))
            with self.assertRaisesRegex(ValueError,'consent_oversight'):validate_support_v21(edited,rebound,START+timedelta(days=14))
        snapshot=next(r for r in full.records if r.record_id==decision.decision_snapshot.record_id)
        held=snapshot.model_copy(update=dict(workflow=snapshot.workflow.model_copy(update=dict(clinical='clinical_hold',hold_reasons=['fixture hold']))))
        edited=history(full.patient_id,[held if r.record_id==snapshot.record_id else r for r in full.records])
        rebound=decision.model_copy(update=dict(decision_snapshot=exact_ref(held)))
        with self.assertRaisesRegex(ValueError,'held_support'):validate_support_v21(edited,rebound,START+timedelta(days=14))


if __name__=='__main__':unittest.main()
