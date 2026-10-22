"""Actual frozen003 worker checkpoint and additive004 stopped upgrade proofs."""
import base64,hashlib,json,os,sqlite3,subprocess,sys,tempfile,unittest
from contextlib import closing
from pathlib import Path
from datetime import datetime,timezone
from services.foundation.cutover import bundle_for
from services.foundation.store import Store
from services.foundation.upgrade003 import upgrade_checkpoint003,legacy_snapshot
from services.foundation.admission import AdmissionError
from live_helpers import live_fixture
from live_process_helpers import CONTEXT

NOW=datetime(2026,10,21,12,tzinfo=timezone.utc)


class StoppedUpgradeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory=tempfile.TemporaryDirectory();cls.frozen=Path(cls.directory.name)/'frozen';cls.frozen.mkdir()
        manifest=json.loads(Path(__file__).with_name('checkpoint003-source.json').read_bytes())
        assert manifest['source_head']=='1096d6da86048e7a53f98ed70abdd85f6f497aed'
        for item in manifest['files']:
            raw=base64.b64decode(item['base64']);assert hashlib.sha256(raw).hexdigest()==item['sha256']
            assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==item['git_blob']
            target=cls.frozen/item['path'];target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)

    @classmethod
    def tearDownClass(cls):cls.directory.cleanup()

    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        result=subprocess.run([sys.executable,str(Path(__file__).with_name('build_checkpoint003.py')),str(self.frozen),str(self.root)],cwd=self.frozen,capture_output=True)
        self.assertEqual(result.returncode,0,(result.stdout+result.stderr).decode())
        self.previous=(self.root/'old-bundle.json').read_bytes();old=json.loads(self.previous)
        self.results=json.loads((self.root/'old-results.json').read_bytes())
        _,_,installed,_=live_fixture(self.root)
        self.assertEqual(installed.authority.grants[0].package_sha256,old['authority']['grants'][0]['package_sha256'])
        self.new=bundle_for(installed.authority,installed.review_rules,generation=old['control']['authority_generation']+1)
        self.source=self.root/'old.sqlite';self.target=self.root/'upgraded.sqlite'

    def tearDown(self):self.temp.cleanup()

    def snapshot(self,path):
        with closing(sqlite3.connect(path)) as db:return legacy_snapshot(db)

    def test_actual003_upgrade_preserves_old_bytes_ids_and_invalidates_review_once(self):
        before=self.snapshot(self.source)
        with closing(sqlite3.connect(self.source)) as db:version=db.execute("SELECT version FROM patients WHERE id='SYN-02'").fetchone()[0]
        store=upgrade_checkpoint003(self.target,self.source,self.previous,self.new,clock=lambda:NOW)
        self.assertEqual(before,self.snapshot(self.source))
        with store.transaction() as db:
            for table,rows in before.items():self.assertEqual([tuple(r) for r in db.execute('SELECT * FROM '+table+' ORDER BY rowid')][:len(rows)],rows,table)
            self.assertEqual({r[0] for r in db.execute('SELECT version FROM schema_migrations')},{1,2,3,4})
            self.assertEqual(db.execute("SELECT version FROM patients WHERE id='SYN-02'").fetchone()[0],version+1)
            episode=json.loads(db.execute('SELECT payload FROM live_hold_episodes').fetchone()[0])
            self.assertIsNone(episode['current_review_id']);self.assertEqual(episode['task_ids'],self.results['entry']['task_ids'])
            self.assertEqual(db.execute('SELECT task_id FROM live_hold_task_bindings').fetchone()[0],self.results['entry']['task_ids'][0])
            self.assertEqual(db.execute('PRAGMA foreign_key_check').fetchall(),[])
        from fastapi.testclient import TestClient
        from services.foundation.app import Settings,create_app
        from services.foundation.cli import DEMO_PASSWORDS
        with TestClient(create_app(Settings(store.path,self.new,clock=lambda:NOW)),base_url='http://127.0.0.1:8765') as client:
            csrf=client.get('/api/session').json()['csrf'];login=client.post('/api/login',json=dict(username='alice',password=DEMO_PASSWORDS['alice']),headers={'Origin':'http://127.0.0.1:8765','X-CSRF-Token':csrf});self.assertEqual(login.status_code,200,login.text)
            workspace=client.get('/api/patients/SYN-02');self.assertEqual(workspace.status_code,200,workspace.text);self.assertEqual(workspace.json()['stage'],'ASSIGN-09')

    def test_actual_process_death_before004_commit_rolls_back_and_after_commit_recovers(self):
        before=self.snapshot(self.source)
        def child(point,target):
            def fault(name):
                if name==point:os._exit(83)
            upgrade_checkpoint003(target,self.source,self.previous,self.new,clock=lambda:NOW,fault=fault)
        process=CONTEXT.Process(target=child,args=('before_004_upgrade_commit',self.target));process.start();process.join(15);self.assertEqual(process.exitcode,83)
        with closing(sqlite3.connect(self.target)) as db:
            self.assertEqual({r[0] for r in db.execute('SELECT version FROM schema_migrations')},{1,2,3})
            self.assertIsNone(db.execute("SELECT 1 FROM sqlite_master WHERE name='live_hold_task_bindings'").fetchone())
        with self.assertRaises(AdmissionError):Store(self.target,self.new)
        committed=self.root/'committed.sqlite';process=CONTEXT.Process(target=child,args=('after_004_upgrade_commit',committed));process.start();process.join(15);self.assertEqual(process.exitcode,83)
        recovered=Store(committed,self.new,clock=lambda:NOW)
        with recovered.transaction() as db:self.assertEqual(db.execute('SELECT count(*) FROM live_hold_task_bindings').fetchone()[0],1)
        self.assertEqual(before,self.snapshot(self.source))


if __name__=='__main__':unittest.main()
