"""Test-only genuine generation and isolated Store; no research qualification.

Runtime/source/image identities are observed by the invoking test command, not
invented by a fixture. Test authorities exist only in this temporary test tree.
"""
import copy
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import platform
import shutil
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'integration/replay'))
from live_helpers import fresh_store
from contracts.domain.analysis import project_history
from contracts.domain.cohort import make_cohort_input
from contracts.domain.common import Source
from contracts.runs.admission import admit_export, verify_export
from contracts.runs.common import Authority, Bindings, ExportAuthority, RESTRICTED, Runtime, canonical, sha256
from contracts.runs.observed import ObservedExport
from contracts.runs.private import RunManifest
from contracts.runs.private_admission import verify_run
from services.foundation.cli import seed
from services.foundation.cohort_registration import register, registration, _key
from services.foundation.research_enrollment import enroll_replay_register
from services.foundation.store import instant, timestamp
from services.foundation.replay import replay
from services.generator import research

ROOT=Path(__file__).resolve().parents[2]


def runtime():
    import numpy
    def ref(identifier,path):return dict(id=identifier,version='20261021',sha256=sha256((ROOT/path).read_bytes().replace(b'\r\n',b'\n')))
    return dict(image_sha256=os.environ['RESEARCH_TEST_IMAGE'].removeprefix('sha256:'),
        numerical_lock=ref('numerical-lock','tooling/library/requirements.lock'),
        service_lock=ref('service-lock','tooling/foundation/requirements.lock'),python_version=platform.python_version(),
        numpy_version=numpy.__version__,prng=RESTRICTED['runtime_profile']['prng'],
        seed_derivation=RESTRICTED['runtime_profile']['seed_derivation'],precision='float64')


def authority(raw):
    value=json.loads(raw)
    return ExportAuthority.model_validate_json(canonical(dict(run_id=value['run_id'],producer=value['producer'],
        manifest_sha256=value['run_manifest']['sha256'],source_commit=value['source_commit'],runtime=value['runtime'],
        allow_contract_fixture=False,export_id=value['id'],export_sha256=sha256(raw))))


class ResearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.archive=tempfile.TemporaryDirectory();cls.root=Path(cls.archive.name)
        cls.plan=dict(version='poc-restricted-research-plan-v1',namespace='PRIVATE-test-research-generation-namespace',
            run_id='test-research-run',unit_id='test-research-unit',cohort_id='test-research-cohort',
            created_at=datetime.now(timezone.utc).isoformat(),
            patients=['RESEARCH-'+str(i).zfill(2) for i in range(12)])
        cls.pins=runtime();cls.commit=os.environ['RESEARCH_TEST_SOURCE']
        cls.product=research.prepare(cls.plan,cls.root/'private',cls.root/'staging',runtime=cls.pins,source_commit=cls.commit)
        cls.raw={d:(cls.root/'staging'/f'day-{d}'/'candidate.json').read_bytes() for d in (14,42)}
        cls.auth={d:authority(cls.raw[d]) for d in (14,42)}

    @classmethod
    def tearDownClass(cls):cls.archive.cleanup()

    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.local=Path(self.temp.name)

    def verify(self,data=None,day=14,root=None):
        raw=self.raw[day] if data is None else canonical(data)
        return verify_export(raw,root or self.root/'staging'/f'day-{day}',authority(raw))

    def changed_record(self,change,day=14):
        root=self.local/'changed';shutil.copytree(self.root/'staging'/f'day-{day}',root)
        data=json.loads(self.raw[day]);p=data['partitions'][0]
        history=json.loads((root/p['history']['path']).read_bytes());change(history['records'])
        encoded=canonical(history);(root/p['history']['path']).write_bytes(encoded)
        p['history'].update(sha256=sha256(encoded),bytes=len(encoded))
        p['records']=[dict(record_id=r['record_id'],payload_sha256=sha256(canonical(r)),source=r['source'],seed_key_sha256=None,
            import_to_event_store=r['kind'] in research.INGESTIBLE,exclusion_reason=None if r['kind'] in research.INGESTIBLE else 'administrative_event_not_live_authority') for r in history['records']]
        return data,root

    def store(self):
        store=fresh_store(self.local/'service.sqlite');seed(store);return store

    def enroll(self,store,day=14,**kwargs):
        return enroll_replay_register(store,'alice',self.raw[day],self.root/'staging'/f'day-{day}',self.auth[day],
            cohort_id=self.plan['cohort_id'],**kwargs)

    def test_exact_descriptors_and_dependency_hashes(self):
        for name,value in RESTRICTED['binding_descriptors'].items():
            self.assertEqual(sha256(canonical(value)),RESTRICTED['bindings'][name]['sha256'])
        self.assertEqual(sha256(canonical(RESTRICTED['evaluation_configuration']['payload'])),RESTRICTED['evaluation_configuration']['reference']['sha256'])
        self.assertEqual(self.pins['numerical_lock']['sha256'],RESTRICTED['runtime_profile']['numerical_lock_sha256'])
        self.assertEqual(self.pins['service_lock']['sha256'],RESTRICTED['runtime_profile']['service_lock_sha256'])

    def test_genuine_12_continuity_strict_cutoffs_and_identical_bytes(self):
        _,short=self.verify();_,long=self.verify(day=42)
        self.assertEqual(len(short),12);self.assertEqual(len(long),12)
        self.assertNotEqual(sha256(self.raw[14]),sha256(self.raw[42]))
        for a,b in zip(short,long):
            before={r.record_id:r for r in a[1].records};after={r.record_id:r for r in b[1].records}
            self.assertTrue(before.keys()<=after.keys());self.assertTrue(all(r==after[i] for i,r in before.items()))
            self.assertTrue(all(max(r.event_at,r.recorded_at,r.available_at)<a[3].cutoff for r in a[1].records))
            reduced=project_history(b[3]);plans=[r for r in reduced.records if r.kind=='assignment']
            self.assertEqual([p.event_at for p in plans],[research.START+timedelta(days=d) for d in (0,14,28)])
            self.assertEqual(len({p.option for p in plans}),1);self.assertTrue(plans[0].experimental)
            self.assertEqual([p.experimental for p in plans[1:]],[False,False])
        again=self.local/'again'
        research.prepare(self.plan,again/'private',again/'staging',runtime=self.pins,source_commit=self.commit)
        for day in (14,42):self.assertEqual(self.raw[day],(again/'staging'/f'day-{day}'/'candidate.json').read_bytes())
        # Same private recipe is safely repeatable without replacing any bytes.
        self.assertEqual(research.prepare(self.plan,self.root/'private',self.root/'staging',runtime=self.pins,source_commit=self.commit),self.product)

    def test_private_run_configuration_verified_and_public_admission(self):
        raw=(self.root/'private/run-manifest.json').read_bytes()
        public=json.loads(self.raw[14]);trusted=self.auth[14].model_dump(exclude={'export_id','export_sha256'})
        run=verify_run(raw,self.root/'private',Authority.model_validate_json(canonical(trusted)))
        self.assertEqual(run.units[0].catalog_patients,12)
        self.assertEqual(run.sources,[*RESTRICTED['source'],RESTRICTED['historical_assignment_source']])
        destination=self.local/'admitted';destination.mkdir()
        admitted=admit_export(self.raw[14],self.root/'staging/day-14',destination,self.auth[14])
        self.assertTrue((admitted/'manifest.json').exists())
        self.assertEqual({p.name for p in admitted.iterdir()},{'observed','replay','manifest.json'})
        verify_export((admitted/'manifest.json').read_bytes(),admitted,self.auth[14])
        with self.assertRaises(FileExistsError):admit_export(self.raw[14],self.root/'staging/day-14',destination,self.auth[14])
        self.assertIsNone(public.get('private_mapping'))

    def test_no_private_mapping_truth_or_raw_in_learner(self):
        _,parts=self.verify(day=42)
        all_public=b''.join(p.read_bytes() for p in (self.root/'staging').rglob('*.json'))
        self.assertNotIn(self.plan['namespace'].encode(),all_public)
        self.assertNotIn(b'derivation_input',all_public);self.assertNotIn(b'adapter_seed',all_public)
        self.assertNotIn(b'private_truth',all_public);self.assertNotIn(b'canonical_words',all_public)
        for p in parts:
            reduced=canonical(project_history(p[3]).model_dump(mode='json'))
            for denied in (b'raw_source',b'"source"',b'"seed"',b'"parameters"',b'"truth"',b'"namespace"'):
                self.assertNotIn(denied,reduced)

    def test_every_binding_mutation_and_canonical_mixture_rejected(self):
        canonical_bindings=json.loads((ROOT/'contracts/runs/bindings-v1.json').read_bytes())
        for name in RESTRICTED['bindings']:
            for mutation in ('hash','canonical'):
                with self.subTest(name=name,mutation=mutation):
                    data=json.loads(self.raw[14]);data['bindings'][name]=copy.deepcopy(canonical_bindings[name] if mutation=='canonical' else data['bindings'][name])
                    if mutation=='hash':data['bindings'][name]['sha256']='0'*64
                    with self.assertRaises(ValueError):self.verify(data)

    def test_unknown_mixed_runtime_source_binding_and_evaluation_rejected(self):
        for field,value in [('prng','unknown'),('prng','PCG64DXSM'),('seed_derivation','remission-seed-v1')]:
            data=json.loads(self.raw[14]);data['runtime'][field]=value
            with self.subTest(field=field,value=value),self.assertRaises(ValueError):self.verify(data)
        for field in ('numerical_lock','service_lock'):
            data=json.loads(self.raw[14]);data['runtime'][field]['sha256']='0'*64
            with self.assertRaises(ValueError):self.verify(data)
        for field,value in [('evaluation_configuration',None),('execution','contract_fixture'),('source_commit','bad')]:
            data=json.loads(self.raw[14]);data[field]=value
            with self.assertRaises(ValueError):self.verify(data)
        data=json.loads(self.raw[14]);data['runtime'].update(prng='PCG64DXSM',seed_derivation='remission-seed-v1')
        with self.assertRaises(ValueError):self.verify(data)
        data=json.loads(self.raw[14]);data['bindings']=json.loads((ROOT/'contracts/runs/bindings-v1.json').read_bytes())
        with self.assertRaises(ValueError):self.verify(data)
        for field,value in [('id','unknown'),('version','1.2.0'),('adapter','patient_report')]:
            data=json.loads(self.raw[14]);data['partitions'][0]['records'][0]['source'][field]=value
            with self.assertRaises(ValueError):self.verify(data)

    def test_wrong_unit_replicate_count_configuration_and_source_run_rejected(self):
        raw=json.loads((self.root/'private/run-manifest.json').read_bytes())
        mutations=[lambda d:d.update(phase='fixture'),lambda d:d.update(scope='cell_batch'),
            lambda d:d['sources'][0].update(version='1.2.0'),lambda d:d['units'][0].update(cell_id='S01.reference.n60'),
            lambda d:d['units'][0].update(catalog_patients=60),lambda d:d['units'][0].update(repetitions=2),
            lambda d:d['units'][0]['evaluation_configuration'].update(sha256='0'*64),
            lambda d:d['units'][0]['cohorts'][0].update(role='historical'),
            lambda d:d['units'][0]['cohorts'][0]['patients'].pop(),
            lambda d:d['units'][0]['cohorts'][0]['patients'][0].update(replicate=1)]
        for mutate in mutations:
            data=copy.deepcopy(raw);mutate(data)
            with self.assertRaises(ValueError):RunManifest.model_validate_json(canonical(data))
        for field,value in [('cohort_id','wrong'),('unit_id','wrong'),('replicate',1),('cell_id','S01.reference.n60')]:
            data=json.loads(self.raw[14]);data['partitions'][0][field]=value
            with self.assertRaises(ValueError):self.verify(data)
        data=json.loads(self.raw[14]);data['partitions'].pop()
        with self.assertRaises(ValueError):self.verify(data)

    def test_assignment_metadata_and_future_private_injection_rejected(self):
        def mutate(records,kind,changes):
            record=next(r for r in records if r['kind']==kind);record.update(changes)
        cases=[('assignment',dict(probability=.4)),('assignment',dict(clinician_override='behavioral_continue',override_reason='not authorized')),
            ('assignment',dict(experimental=False,component=None,probability=None,seed=None)),
            ('assignment',dict(event_at=(research.START+timedelta(days=1)).isoformat(),recorded_at=(research.START+timedelta(days=1)).isoformat(),available_at=(research.START+timedelta(days=1)).isoformat())),
            ('assignment',dict(truth=12)),('assignment',dict(parameters={})),
            ('daily_report',dict(available_at=(research.START+timedelta(days=14)).isoformat()))]
        for index,(kind,changes) in enumerate(cases):
            self.local=self.local/str(index);self.local.mkdir()
            data,root=self.changed_record(lambda records:mutate(records,kind,changes))
            with self.subTest(kind=kind,changes=changes),self.assertRaises(ValueError):self.verify(data,root=root)

    def test_seed_collision_rejected_before_engine_and_domains_independent(self):
        values=research.mappings(research.ResearchPlan.model_validate_json(canonical(self.plan)))
        self.assertEqual(len({m['adapter_seed'] for m in values}),24)
        self.assertEqual({m['index'] for m in values},set(range(12)))
        with patch('services.generator.research.sha256',return_value='0'*64),patch('services.generator.research.generate') as generator:
            with self.assertRaisesRegex(ValueError,'collision'):research.prepare(self.plan,self.local/'private',self.local/'observed',runtime=self.pins,source_commit=self.commit)
            generator.assert_not_called()
        # Independent Bernoulli draws may be entirely one arm; no rebalancing.
        with patch('services.generator.research.uniform',return_value=.9):
            research.prepare(self.plan,self.local/'unbalanced-private',self.local/'unbalanced-observed',runtime=self.pins,source_commit=self.commit)
        _,parts=self.verify(json.loads((self.local/'unbalanced-observed/day-14/candidate.json').read_bytes()),root=self.local/'unbalanced-observed/day-14')
        self.assertEqual({r.option for p in parts for r in p[1].records if r.kind=='assignment'},{'behavioral_continue'})

    def test_store_two_cutoffs_retry_current_versions_and_day14_immutable(self):
        store=self.store();first=self.enroll(store)
        with store.transaction() as db:
            historical=registration(db,'alice',self.plan['run_id'],self.plan['cohort_id'],json.loads(self.raw[14])['cutoff'])
            versions={p:db.execute('SELECT version FROM patients WHERE id=?',(p,)).fetchone()[0] for p in self.plan['patients']}
            self.assertEqual(db.execute("SELECT count(*) FROM events WHERE kind IN ('assignment','approval')").fetchone()[0],0)
            self.assertEqual(db.execute('SELECT count(*) FROM bundles').fetchone()[0],0)
            self.assertEqual(db.execute('SELECT count(*) FROM events WHERE kind=?',('consent',)).fetchone()[0],0)
        self.assertEqual(first,self.enroll(store))
        with store.transaction() as db:self.assertEqual(versions,{p:db.execute('SELECT version FROM patients WHERE id=?',(p,)).fetchone()[0] for p in versions})
        second=self.enroll(store,42);self.assertFalse(second['executable'])
        with store.transaction() as db:
            self.assertEqual(historical,registration(db,'alice',self.plan['run_id'],self.plan['cohort_id'],json.loads(self.raw[14])['cutoff']))
            current=registration(db,'alice',self.plan['run_id'],self.plan['cohort_id'],json.loads(self.raw[42])['cutoff'])
            from contracts.domain.borrowing import SourceBundle
            sources=SourceBundle.model_validate_json((ROOT/'services/foundation/studies/source-7c97862d.json').read_bytes())
            for c in (historical,current):
                v0=make_cohort_input(c,'test-v0');v1=make_cohort_input(c,'test-v1',sources)
                self.assertEqual(v0.cohort_sha256,v1.cohort_sha256)
                self.assertNotEqual(v0.numerical_seeds.nuts,v1.numerical_seeds.nuts)
                self.assertIsNone(v0.sources);self.assertEqual(v1.sources,sources)
        self.assertEqual(first,self.enroll(store,14))
        with self.assertRaisesRegex(ValueError,'version'):
            register(store,'alice',self.raw[42],self.root/'staging/day-42',self.auth[42],cohort_id=self.plan['cohort_id'],patient_versions=versions)

    def test_owner_fixture_duplicate_and_conflicting_enrollment_fail_before_registration(self):
        store=self.store()
        for owner,cohort in [('missing',self.plan['cohort_id']),('alice','wrong-cohort')]:
            with self.assertRaises(ValueError):enroll_replay_register(store,owner,self.raw[14],self.root/'staging/day-14',self.auth[14],cohort_id=cohort)
        fixture=self.auth[14].model_dump(mode='json');fixture['allow_contract_fixture']=True
        with self.assertRaises(ValueError):enroll_replay_register(store,'alice',self.raw[14],self.root/'staging/day-14',ExportAuthority.model_validate_json(canonical(fixture)),cohort_id=self.plan['cohort_id'])
        from services.foundation.workflow import state_for
        patient=self.plan['patients'][0]
        with store.transaction(write=True) as db:
            db.execute('INSERT INTO patients VALUES(?,?,?,?,?,?,?,?,?,?)',(patient,'bob','Conflicting owned patient',1,1,1,1,
                canonical(state_for('ASSIGN-01')).decode(),None,timestamp(research.START)))
        with self.assertRaisesRegex(ValueError,'conflict'):self.enroll(store)
        with store.transaction(write=True) as db:
            state=state_for('ASSIGN-01');state['simulation']={'panel':'interactive'}
            db.execute('UPDATE patients SET owner_id=?,state_json=? WHERE id=?',('alice',canonical(state).decode(),patient))
        with self.assertRaisesRegex(ValueError,'interactive'):self.enroll(store)
        with store.transaction() as db:
            self.assertEqual(db.execute("SELECT count(*) FROM state_changes WHERE id LIKE 'cohort-run-%'").fetchone()[0],0)
            self.assertEqual(db.execute("SELECT count(*) FROM patients WHERE id LIKE 'RESEARCH-%'").fetchone()[0],1)
        duplicate=copy.deepcopy(self.plan);duplicate['patients'][1]=duplicate['patients'][0]
        with self.assertRaises(ValueError):research.ResearchPlan.model_validate_json(canonical(duplicate))

    def test_partial_replay_and_cutoff_fault_retry_is_version_stable(self):
        store=self.store();counts={'batches':0}
        def partial(stage):
            if stage=='before_replay_commit':
                counts['batches']+=1
                if counts['batches']==2:raise ValueError('injected-replay-failure')
        with self.assertRaisesRegex(ValueError,'injected-replay'):self.enroll(store,batch_size=80,fault=partial)
        with store.transaction() as db:
            self.assertEqual(db.execute("SELECT count(*) FROM state_changes WHERE id LIKE 'cohort-run-%'").fetchone()[0],0)
            self.assertGreater(db.execute('SELECT cursor FROM replay_runs').fetchone()[0],0)
            self.assertTrue(all(instant(r['cutoff'])==research.START for r in db.execute("SELECT cutoff FROM patients WHERE id LIKE 'RESEARCH-%'")))
        def before_cutoff(stage):
            if stage=='before_cutoff_commit':raise ValueError('injected-cutoff-failure')
        with self.assertRaisesRegex(ValueError,'injected-cutoff'):self.enroll(store,fault=before_cutoff)
        with store.transaction() as db:
            self.assertEqual(db.execute("SELECT count(*) FROM state_changes WHERE id LIKE 'research-cutoff-%'").fetchone()[0],0)
            versions={r['id']:r['version'] for r in db.execute("SELECT id,version FROM patients WHERE id LIKE 'RESEARCH-%'")}
        def before_register(stage):
            if stage=='before_registration':raise ValueError('injected-register-failure')
        with self.assertRaisesRegex(ValueError,'injected-register'):self.enroll(store,fault=before_register)
        with store.transaction() as db:
            for p,v in versions.items():self.assertEqual(db.execute('SELECT version FROM patients WHERE id=?',(p,)).fetchone()[0],v+1)
        self.enroll(store)
        with store.transaction() as db:
            for p,v in versions.items():self.assertEqual(db.execute('SELECT version FROM patients WHERE id=?',(p,)).fetchone()[0],v+1)
            self.assertEqual(db.execute("SELECT count(*) FROM ingestion_receipts WHERE status='rejected'").fetchone()[0],1)
            self.assertEqual(db.execute("SELECT count(*) FROM ingestion_receipts WHERE transport_key LIKE '%:validated-retry'").fetchone()[0],1)
            self.assertEqual(db.execute('SELECT count(DISTINCT id) FROM events').fetchone()[0],db.execute('SELECT count(*) FROM events').fetchone()[0])

    def test_changed_retry_payload_and_conflicting_retry_receipt_rejected(self):
        store=self.store()
        def fail(stage):
            if stage=='before_replay_commit':raise ValueError('retained-failed-receipt')
        with self.assertRaisesRegex(ValueError,'retained-failed'):self.enroll(store,fault=fail)
        with store.transaction() as db:
            receipt=dict(db.execute("SELECT * FROM ingestion_receipts WHERE status='rejected'").fetchone())
            versions={r['id']:r['version'] for r in db.execute("SELECT id,version FROM patients WHERE id LIKE 'RESEARCH-%'")}
        _,parts=self.verify()
        entries=[e.model_dump(mode='json') for p in parts for e in p[2].entries]
        # Still valid typed raw envelope, but different bytes in the same frozen
        # replay run. Immutable source identity rejects it before a batch starts.
        changed=copy.deepcopy(entries);changed[0]['raw_source']+=' '
        changed[0]['record']['source']['raw_sha256']=sha256(changed[0]['raw_source'].encode())
        with self.assertRaisesRegex(ValueError,'immutable_replay_run'):
            replay(store,receipt['run_id'],changed,json.loads(self.raw[14])['cutoff'],preserve_cutoff=True)
        with store.transaction(write=True) as db:
            db.execute('INSERT INTO ingestion_receipts VALUES(?,?,?,?,?)',(receipt['run_id'],receipt['transport_key']+':validated-retry','0'*64,'accepted','injected conflicting immutable key'))
        with self.assertRaisesRegex(ValueError,'replay_receipt_payload_conflict'):self.enroll(store)
        with store.transaction() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM events').fetchone()[0],0)
            for p,v in versions.items():self.assertEqual(db.execute('SELECT version FROM patients WHERE id=?',(p,)).fetchone()[0],v)

    def test_projection_rejects_unknown_mixed_canonical_and_noninitial_research_design(self):
        from contracts.domain.boundaries import ObservedHistory
        _,parts=self.verify(day=42);base=parts[0][1].model_dump(mode='json')
        mutations=[lambda a:a['source'].update(id='unknown'),lambda a:a['source'].update(version='1.2.0'),
            lambda a:a['source'].update(adapter='patient_report'),
            lambda a:a['source'].update(id='foundation-synthetic',adapter='research_configuration'),
            lambda a:a.update(experimental=True,component='escalation',probability=.5,seed=dict(namespace='assignment',protocol='poc-restricted-research-retain-v1',scenario='poc-restricted-reference-n12-v1',replicate=0,patient=a['patient_id'],time_index=0,process='historical-initial-assignment'))]
        for index,mutate in enumerate(mutations):
            data=copy.deepcopy(base);plans=[r for r in data['records'] if r['kind']=='assignment'];mutate(plans[-1] if index==4 else plans[0])
            typed=ObservedHistory.model_validate_json(canonical(data))
            with self.subTest(index=index),self.assertRaises(ValueError):project_history(typed.project(research.START+timedelta(days=42)))

    def test_v2_runtime_and_schema_bindings_remain_canonical(self):
        from pydantic import TypeAdapter
        from contracts.runs.observed_v2 import ObservedExportV2, ExportAuthorityV2
        from contracts.runs.private_v2 import RunManifestV2, AuthorityV2
        for model in (ObservedExportV2,ExportAuthorityV2,RunManifestV2,AuthorityV2):
            annotation=model.model_fields['runtime'].annotation
            self.assertIs(annotation,Runtime)
            with self.subTest(model=model.__name__),self.assertRaises(ValueError):TypeAdapter(annotation).validate_json(canonical(self.pins))
            schema=TypeAdapter(model).json_schema()
            self.assertEqual(schema['$defs']['Runtime']['properties']['prng']['const'],'PCG64DXSM')
        from contracts.runs.export_v2 import products
        for path,value in products().items():
            expected=json.loads((ROOT/'contracts/runs'/path).read_bytes())
            self.assertEqual(value,expected)

    def test_registration_late_member_failure_rolls_back_all_links(self):
        store=self.store()
        with store.transaction(write=True) as db:
            db.execute("CREATE TRIGGER registration_failure BEFORE INSERT ON state_changes WHEN NEW.patient_id='RESEARCH-11' AND NEW.id LIKE 'cohort-run-%' BEGIN SELECT RAISE(ABORT,'late-member-failure'); END")
        with self.assertRaisesRegex(sqlite3.IntegrityError,'late-member'):self.enroll(store)
        with store.transaction(write=True) as db:
            self.assertEqual(db.execute("SELECT count(*) FROM state_changes WHERE id LIKE 'cohort-run-%'").fetchone()[0],0)
            db.execute('DROP TRIGGER registration_failure')
        self.assertFalse(self.enroll(store)['executable'])


if __name__=='__main__':unittest.main()
