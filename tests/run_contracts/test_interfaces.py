"""Real byte/path/admission/SQLite boundaries using labeled contract fixtures."""
import copy
from datetime import timedelta
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from fixtures import ROOT, CUTOFF, artifact, full_key, load, observation, setup
from contracts.domain.boundaries import ObservedHistory
from contracts.runs.admission import admit_export, read_admitted, verify_export
from contracts.runs.common import Artifact, Authority, Bindings, ExportAuthority, canonical, read_artifact, sha256
from contracts.runs.export import products
from contracts.runs.observed import ObservedExport, ReplayBatch
from contracts.runs.private import CELLS, RunManifest, RunResult, StreamKey, TruthRequest, TruthResponse, validate_truth_response
from contracts.runs.private_admission import verify_result, verify_run, verify_truth
from services.foundation.cli import seed
from services.foundation.replay import replay_export
from services.foundation.store import Store, instant
from services.foundation.workflow import history
from services.learner.worker import read_run_export
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'integration/replay'))
from live_helpers import fresh_store


class Interfaces(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);self.data=setup(self.root)

    def tearDown(self):self.temp.cleanup()

    def export(self,raw=None,authority=None):
        return verify_export(raw or self.data['export_raw'],self.root,authority or self.data['export_authority'])

    def test_trusted_run_export_roundtrip_and_strict_equality_cutoff(self):
        d=self.data
        run=verify_run(d['run_raw'],self.root,d['authority'])
        result,admitted=verify_result(d['result_raw'],self.root,run,d['authority'],sha256(d['result_raw']))
        self.assertEqual(result.status,'partial');self.assertEqual(len(admitted),2)
        manifest,partitions=self.export()
        self.assertEqual(ObservedExport.model_validate_json(canonical(manifest.model_dump(mode='json'))),manifest)
        for _,observed,_,projected,_,_ in partitions:
            self.assertEqual(projected.records,[]) # exactly equal availability stays out of learner values
            self.assertEqual(len(observed.project(instant(CUTOFF)+timedelta(microseconds=1)).records),1)
        self.assertEqual({p[1].patient_id for p in admitted},{'SYN-02','SYN-B01'})

    def test_evaluation_roster_configuration_and_calibration_barriers_before_export(self):
        data=self.data['run'].model_dump(mode='json');unit=data['units'][0];unit['preset']='evaluation'
        configuration=dict(id='evaluation-plan',version='fixture-v1',repetitions=1,cohorts=[dict(id='historical',role='historical',patients_per_replicate=60)])
        ref=artifact(self.root,'evaluation-plan','configuration/evaluation-plan.json',configuration,'configuration')
        data['inputs'].append(ref);data['input_sha256']=sha256(canonical(data['inputs']))
        unit['evaluation_configuration']=dict(id=ref['id'],version='fixture-v1',sha256=ref['sha256'])
        raw=canonical(data);authority=self.data['authority'].model_dump(mode='json');authority['manifest_sha256']=sha256(raw)
        verify_run(raw,self.root,load(Authority,authority))
        configuration['cohorts'][0]['patients_per_replicate']=61
        ref=artifact(self.root,'evaluation-plan','configuration/evaluation-plan.json',configuration,'configuration')
        data['inputs'][-1]=ref;data['input_sha256']=sha256(canonical(data['inputs']));unit['evaluation_configuration']['sha256']=ref['sha256']
        raw=canonical(data);authority['manifest_sha256']=sha256(raw)
        with self.assertRaisesRegex(ValueError,'evaluation cohort/replicate roster'):
            verify_run(raw,self.root,load(Authority,authority))
        for cell in ('S23.MAR_20.n60','S10.external_contrast.n60'):
            if cell not in CELLS:continue
            destination=self.root/cell;destination.mkdir();d=setup(destination,cell=cell)
            with self.assertRaisesRegex(ValueError,'independently verified solved binding'):
                verify_result(d['result_raw'],destination,d['run'],d['authority'],sha256(d['result_raw']))

    def test_complete_roster_requires_all_sixty_patients(self):
        bad=self.data['result'].model_dump(mode='json');bad.update(status='complete',reason=None)
        raw=canonical(bad)
        with self.assertRaisesRegex(ValueError,'omitted planned patients'):
            verify_result(raw,self.root,self.data['run'],self.data['authority'],sha256(raw))
        full_root=self.root/'complete';full_root.mkdir();full=setup(full_root,complete=True)
        _,records=verify_result(full['result_raw'],full_root,full['run'],full['authority'],sha256(full['result_raw']))
        self.assertEqual(len(records),60)

    def test_versions_hashes_runtime_and_self_declared_producer_reject(self):
        for field in Bindings.model_fields:
            bad=self.data['export'].bindings.model_dump(mode='json');bad[field]['sha256']='0'*64
            with self.subTest(field=field),self.assertRaises(ValueError):load(Bindings,bad)
        for change in [dict(export_sha256='0'*64),dict(source_commit='0'*40),dict(producer=dict(id='forged',version='1.0.0',role='contract_fixture')),dict(allow_contract_fixture=False)]:
            policy=self.data['export_authority'].model_dump(mode='json');policy.update(change)
            with self.subTest(change=change),self.assertRaises(ValueError):self.export(authority=load(ExportAuthority,policy))
        raw=self.data['run_raw']+b' '
        with self.assertRaises(ValueError):verify_run(raw,self.root,self.data['authority'])
        path=self.root/self.data['run'].inputs[0].path;path.write_bytes(path.read_bytes()+b'forged')
        with self.assertRaises(ValueError):verify_run(self.data['run_raw'],self.root,self.data['authority'])

    def test_path_role_hash_size_symlink_and_privileged_export_reject(self):
        template=self.data['export'].partitions[0].history.model_dump(mode='json')
        for path in ['../truth.json','/truth.json','C:/truth.json','observed\\truth.json','observed/%2e%2e/truth','a//b','a/./b','a/CON.json','a/file.','a/\x01bad']:
            with self.subTest(path=path),self.assertRaises(ValueError):load(Artifact,{**template,'path':path})
        for changes in [dict(role='private_truth'),dict(bytes=template['bytes']+1),dict(sha256='f'*64)]:
            with self.subTest(changes=changes),self.assertRaises(ValueError):read_artifact(self.root,load(Artifact,{**template,**changes}),'observed')
        bad=self.data['export'].model_dump(mode='json');bad['latent_states']={'L':1.0}
        with self.assertRaises(ValueError):load(ObservedExport,bad)
        path=self.root/template['path'];original=path.read_bytes();path.unlink()
        outside=self.root.parent/(self.root.name+'-outside');outside.write_bytes(original)
        try:
            try:path.symlink_to(outside)
            except OSError as error:self.skipTest('host lacks symlink privilege; Linux qualified run must exercise it: '+str(error))
            with self.assertRaises(ValueError):read_artifact(self.root,load(Artifact,template),'observed')
        finally:outside.unlink()

    def test_replay_raw_privilege_and_patient_provenance_mismatch_reject(self):
        batch=json.loads((self.root/self.data['export'].partitions[0].replay.path).read_bytes())
        bad=copy.deepcopy(batch);raw=json.loads(bad['entries'][0]['raw_source']);raw['latent_states']={'L':7.0};raw=canonical(raw).decode()
        bad['entries'][0]['raw_source']=raw;bad['entries'][0]['record']['source']['raw_sha256']=sha256(raw.encode())
        with self.assertRaises(ValueError):load(ReplayBatch,bad)
        bad=copy.deepcopy(batch);bad['patient_id']='SYN-B01'
        with self.assertRaises(ValueError):load(ReplayBatch,bad)
        bad=copy.deepcopy(batch);bad['entries'][0]['raw_source']+=' '
        with self.assertRaises(ValueError):load(ReplayBatch,bad)
        bad=self.data['export'].model_dump(mode='json');bad['partitions'][0]['records'][0]['import_to_event_store']=False;bad['partitions'][0]['records'][0]['exclusion_reason']='administrative_event_not_live_authority'
        raw=canonical(bad);authority=self.data['export_authority'].model_dump(mode='json');authority['export_sha256']=sha256(raw)
        with self.assertRaises(ValueError):self.export(raw,load(ExportAuthority,authority))

    def test_mapping_cannot_cross_cell_preset_cohort_replicate_source_seed(self):
        for field,value in [('cell_id','S02.outcome_null.n60'),('preset','smoke'),('cohort_id','external'),('replicate',1),('unit_id','unknown')]:
            bad=self.data['export'].model_dump(mode='json');bad['partitions'][0][field]=value
            raw=canonical(bad);export=self.data['result'].model_dump(mode='json');ref=artifact(self.root,'export-one','exports/contract-run/export-one.json',raw,'observed_manifest');export['observed_exports']=[ref];result_raw=canonical(export)
            with self.subTest(field=field),self.assertRaises(ValueError):verify_result(result_raw,self.root,self.data['run'],self.data['authority'],sha256(result_raw))
        # A valid-looking changed metadata file must still match the separately bound record/seed.
        bad=self.data['export'].model_dump(mode='json');bad['partitions'][0]['records'][0]['seed_key_sha256']='0'*64
        raw=canonical(bad);result=self.data['result'].model_dump(mode='json');result['observed_exports']=[artifact(self.root,'export-one','exports/contract-run/export-one.json',raw,'observed_manifest')];raw=canonical(result)
        with self.assertRaises(ValueError):verify_result(raw,self.root,self.data['run'],self.data['authority'],sha256(raw))

    def test_exact_full_seed_key_and_namespace_admission(self):
        key=full_key();accepted=load(StreamKey,key)
        material=['remission-seed-v1',20261020,'remission-g1-v1','fixture','measurement','S01.reference.n60',0,'SYN-02',0,'contract_fixture_measurement','error']
        expected=hashlib.sha256(json.dumps(material,separators=(',',':'),ensure_ascii=True).encode('ascii')).digest()
        self.assertEqual(accepted.words,[int.from_bytes(expected[i:i+4],'little') for i in range(0,32,4)])
        self.assertEqual(accepted.key_sha256,expected.hex())
        for changes in [dict(root_seed=7),dict(namespace='unknown'),dict(phase='unknown'),dict(words=[0]*8),dict(key_sha256='0'*64),dict(replicate=True)]:
            with self.subTest(changes=changes),self.assertRaises(ValueError):load(StreamKey,{**key,**changes})
        different=full_key(namespace='truth');self.assertNotEqual(key['key_sha256'],different['key_sha256'])

    def test_exact_catalog_presets_smoke_and_workload_sizes(self):
        data=self.data['run'].model_dump(mode='json')
        for change in [dict(catalog_patients=100),dict(cell_id='S01.reference.n240'),dict(preset='smoke')]:
            bad=copy.deepcopy(data);bad['units'][0].update(change)
            with self.subTest(change=change),self.assertRaises(ValueError):load(RunManifest,bad)
        for key,value in [('calibration_patients',100),('truth_batch_size',100),('truth_batch_cap',10),('source_comparator_sizes',[200]),('conditional_particle_levels',[1024])]:
            bad=copy.deepcopy(data);bad['required_workloads'][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):load(RunManifest,bad)
        data.update(scope='catalog_smoke',phase='smoke',execution='engine_run');data['producer']['role']='generator';data['units']=[]
        for index,cell in enumerate(CELLS.values()):
            roster=[dict(id=f'fixture-{index}-{rep}-{p}',replicate=rep) for rep in range(5) for p in range(cell['patients'])]
            data['units'].append(dict(id=f'unit-{index}',cell_id=cell['id'],catalog_patients=cell['patients'],preset='catalog_cell',evaluation_configuration=None,repetitions=5,cohorts=[dict(id='historical',role='historical',patients=roster)]))
        self.assertEqual(len(load(RunManifest,data).units),82)
        data['units'].pop()
        with self.assertRaises(ValueError):load(RunManifest,data)

    def test_immutable_published_observed_exports_and_safe_consumer_imports(self):
        destination=self.root/'admitted';destination.mkdir()
        published=admit_export(self.data['export_raw'],self.root,destination,self.data['export_authority'])
        _,projections=read_run_export(published,self.data['export_authority']);self.assertEqual(len(projections),2)
        self.assertTrue(all(not p.records for p in projections))
        with self.assertRaises(FileExistsError):admit_export(self.data['export_raw'],self.root,destination,self.data['export_authority'])
        script="import sys;import contracts.runs.admission;assert not any(n.startswith(('contracts.dgp','contracts.runs.private','contracts.domain.evaluation')) for n in sys.modules)"
        subprocess.check_call([sys.executable,'-c',script],cwd=ROOT)
        (published/'manifest.json').chmod(0o644);(published/'manifest.json').write_bytes(b'{}')
        with self.assertRaises(ValueError):read_admitted(published,self.data['export_authority'])

    def test_real_sqlite_multi_patient_atomic_replay_resume_and_snapshot_cutoff(self):
        store=fresh_store(self.root/'actual.sqlite');seed(store)
        def fault(_):raise RuntimeError('controlled pre-commit failure')
        with self.assertRaises(RuntimeError):replay_export(store,self.data['export_raw'],self.root,self.data['export_authority'],fault=fault)
        with store.transaction() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM events').fetchone()[0],0)
            self.assertEqual(db.execute('SELECT cursor FROM replay_runs').fetchone()[0],0)
        replay_export(store,self.data['export_raw'],self.root,self.data['export_authority'],batch_size=1)
        replay_export(Store(store.path,store.installed),self.data['export_raw'],self.root,self.data['export_authority'],batch_size=2)
        with store.transaction() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM events').fetchone()[0],2)
            self.assertEqual(db.execute('SELECT cursor FROM replay_runs').fetchone()[0],2)
            for patient in ['SYN-02','SYN-B01']:
                self.assertEqual(history(db,patient).project(instant(CUTOFF)).records,[])
                self.assertEqual(len(history(db,patient).project(instant(CUTOFF)+timedelta(microseconds=1)).records),1)

    def test_schema_and_dictionary_are_generated_from_current_types(self):
        schema=products()['schemas/observed-export.schema.json']
        self.assertFalse(schema['additionalProperties'])
        self.assertEqual(schema['$id'],'urn:remission:runs:1.0.0:observed-export')
        self.assertTrue({'SimulatorTruth','TruthResult','RunManifest','StreamKey'}.isdisjoint(schema['$defs']))
        load(ObservedExport,self.data['export'].model_dump(mode='json'))
        invalid=self.data['export'].model_dump(mode='json');invalid['counterfactuals']=[]
        with self.assertRaises(ValueError):load(ObservedExport,invalid)


if __name__=='__main__':unittest.main()
