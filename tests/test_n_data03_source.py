"""Meaningful fixed-driver invariants, with process/app/Store imports blocked."""
import ast
import copy
import contextlib
import hashlib
from datetime import datetime,timedelta,timezone
import json
import io
from pathlib import Path
import subprocess
import tempfile
import time
from types import SimpleNamespace
from unittest import mock
import unittest

import n_data03_driver as d
import n_data03 as op
import analysis_lifecycle as frozen_life

def startup_inverse_source(source):
    source=source.replace("'remission-n-data03-261024-r4'","'remission-n-data03-261024-r3'")
    if 'def publish_startup(' not in source:return source
    source=source[:source.index('def publish_startup(')]+source[source.index('def ordinary('):]
    replacements=[
      ("'remission-n-data03-261024-r3'","'remission-n-data03-261023-r2'"),
      ("nonce=secrets.token_hex(24);child=None;reaped=False;code=None;acceptance_failed=False",
       "nonce=secrets.token_hex(24);child=None;reaped=False;code=None"),
      ("        except BaseException:\n            acceptance_failed=True  # A late ACK may already have reached the worker body.\n            if child is not None:",
       "        except BaseException:\n            if child is not None:"),
      ("status='worker_terminal' if not acceptance_failed and reaped and code in (0,1,2) else 'STOP UNCONFIRMED',\n            launcher_acceptance_failed=acceptance_failed,outer_deadline=outer,",
       "status='worker_terminal' if reaped and code in (0,1,2) else 'STOP UNCONFIRMED',outer_deadline=outer,"),
      ("    require(not acceptance_failed and reaped and code==0)","    require(reaped and code==0)"),
      ("                if ready.exists():\n                    require(json.loads(ready.read_bytes())==expected)\n                    require(time.monotonic()<min(until,start+7140));break",
       "                if ready.exists():require(json.loads(ready.read_bytes())==expected);break"),
      ("            require(child.poll() is None)\n            publish_startup(output,'worker-ack.json',expected,min(until,start+7140))\n            require(time.monotonic()<min(until,start+7140) and child.poll() is None)",
       "            require(child.poll() is None);save(output/'worker-ack.json',expected)"),
      ("    until=min(args.outer,args.start+7140,time.monotonic()+5)\n    publish_startup(packet/'attempt','worker-ready.json',identity,until)",
       "    save(packet/'attempt/worker-ready.json',identity);until=min(args.outer,time.monotonic()+5)"),
      ("        if ack.exists():\n            require(json.loads(ack.read_bytes())==identity)\n            require(time.monotonic()<until);break",
       "        if ack.exists():require(json.loads(ack.read_bytes())==identity);break"),
      ("    require(time.monotonic()<until)\n    return worker(packet,spec,args.start,args.lease_unix,args.outer)",
       "    return worker(packet,spec,args.start,args.lease_unix,args.outer)")]
    for before,after in replacements:
        assert source.count(before)==1,before
        source=source.replace(before,after)
    return source

# Exact public R1 typed/config and requested-argv records, not private data.
CAPTURED_CREATED_RAW=r'''{"Id":"ecc1193c6f952e955c8cc5edc76edc022b59223db4cedaa6646b7f5aacfef18e","Image":"sha256:a8e8aa54c20ac6011d0fb108d6c626ff693a518e50acb87fb62679e61e0279a4","User":"0:0","Path":"python","Args":["-B","-c","import os,json,stat\nfrom pathlib import Path\np=Path('/data');assert os.geteuid()==os.getegid()==0\nassert p.is_dir() and not p.is_symlink() and not any(p.iterdir())\nos.chown(p,0,0);assert p.stat().st_uid==p.stat().st_gid==0\nos.chmod(p,0o700);assert not any(p.iterdir())\nos.chown(p,10001,10001);s=p.stat()\nassert (s.st_uid,s.st_gid,stat.S_IMODE(s.st_mode))==(10001,10001,0o700)\nprint(json.dumps(dict(status='fresh_empty_private_volume_owned',uid=10001,gid=10001,mode=448)))\n"],"Labels":{"remission.task":"remission-n-data03-261023-r1"},"State":{"Dead":false,"Error":"","ExitCode":0,"FinishedAt":"0001-01-01T00:00:00Z","OOMKilled":false,"Paused":false,"Pid":0,"Restarting":false,"Running":false,"StartedAt":"0001-01-01T00:00:00Z","Status":"created"},"RestartCount":0,"Memory":1073741824,"MemorySwap":1073741824,"NanoCpus":2000000000,"PidsLimit":64,"ReadonlyRootfs":true,"Privileged":false,"CapAdd":["CAP_CHOWN"],"CapDrop":["ALL"],"AutoRemove":false,"SecurityOpt":["no-new-privileges"],"Tmpfs":{"/tmp":"rw,noexec,nosuid,nodev,size=128m"},"NetworkMode":"none","PortBindings":{},"PublishAllPorts":false,"RestartPolicy":{"MaximumRetryCount":0,"Name":"no"},"Mounts":[{"Destination":"/data","Driver":"local","Mode":"z","Name":"remission-n-data03-261023-r1-positive","Propagation":"","RW":true,"Source":"/var/lib/docker/volumes/remission-n-data03-261023-r1-positive/_data","Type":"volume"}],"Networks":{"none":{"Aliases":null,"DNSNames":null,"DriverOpts":null,"EndpointID":"","Gateway":"","GlobalIPv6Address":"","GlobalIPv6PrefixLen":0,"GwPriority":0,"IPAMConfig":null,"IPAddress":"","IPPrefixLen":0,"IPv6Gateway":"","Links":null,"MacAddress":"","NetworkID":""}}}
'''.encode('utf-8')
CAPTURED_CREATE_RAW=r'''{
  "argv": [
    "docker",
    "create",
    "--name",
    "remission-n-data03-261023-r1-ownership",
    "--network",
    "none",
    "--cpus",
    "2",
    "--memory",
    "1g",
    "--memory-swap",
    "1g",
    "--pids-limit",
    "64",
    "--read-only",
    "--cap-drop",
    "ALL",
    "--security-opt",
    "no-new-privileges",
    "--tmpfs",
    "/tmp:rw,noexec,nosuid,nodev,size=128m",
    "--restart",
    "no",
    "--label",
    "remission.task=remission-n-data03-261023-r1",
    "--user",
    "0:0",
    "--cap-add",
    "CHOWN",
    "--mount",
    "type=volume,source=remission-n-data03-261023-r1-positive,target=/data",
    "--workdir",
    "/app",
    "--entrypoint",
    "python",
    "sha256:a8e8aa54c20ac6011d0fb108d6c626ff693a518e50acb87fb62679e61e0279a4",
    "-B",
    "-c",
    "import os,json,stat\nfrom pathlib import Path\np=Path('/data');assert os.geteuid()==os.getegid()==0\nassert p.is_dir() and not p.is_symlink() and not any(p.iterdir())\nos.chown(p,0,0);assert p.stat().st_uid==p.stat().st_gid==0\nos.chmod(p,0o700);assert not any(p.iterdir())\nos.chown(p,10001,10001);s=p.stat()\nassert (s.st_uid,s.st_gid,stat.S_IMODE(s.st_mode))==(10001,10001,0o700)\nprint(json.dumps(dict(status='fresh_empty_private_volume_owned',uid=10001,gid=10001,mode=448)))\n"
  ],
  "started_monotonic": 838136.1720379,
  "work_deadline_monotonic": 838146.1720379,
  "work_seconds": 10,
  "cleanup_grace_seconds": 2,
  "exit": 0,
  "timed_out": false,
  "deadline_rejected": false,
  "cli_pid": 15712,
  "cli_terminal": "OWNED_POPEN_CHILD_EXIT_OBSERVED",
  "cli_descendants_terminal": "UNKNOWN",
  "stdout_file": "010-ownership-create.stdout",
  "stderr_file": "010-ownership-create.stderr",
  "cleanup_events": [],
  "stdout": "ecc1193c6f952e955c8cc5edc76edc022b59223db4cedaa6646b7f5aacfef18e\n",
  "stdout_snapshot_truncated": false,
  "stderr": "",
  "stderr_snapshot_truncated": false,
  "elapsed_seconds": 0.27443970006424934
}
'''.replace('\n','\r\n').encode('utf-8')

def generation():
    return dict(status='generated',seed=d.SEED,count=12,panel_id='panel-'+'a'*32,
        patient_ids=['POC-'+format(i,'032x') for i in (9,4,8,3,11,2,12,7,1,10,5,6)])


class Data03Source(unittest.TestCase):
    def test_public_input_paths_reject_lexical_escape_before_read(self):
        with tempfile.TemporaryDirectory(dir='artifacts') as folder:
            root=Path(folder)
            self.assertEqual(op.ordinary(root/'public.json'),(root/'public.json').absolute())
            for path in (root/'..'/'outside.json',root/'sub'/'..'/'public.json',root/'bad,name'):
                with self.assertRaises(ValueError):op.ordinary(path)

    def test_generation_ordinal_precedes_sorted_list_and_is_fixed(self):
        value=generation();selection=d.validate_generation(value)
        self.assertEqual(selection['target_id'],value['patient_ids'][6])
        self.assertNotEqual(selection['target_id'],selection['cohort'][6])
        for update in ({'seed':1},{'count':11},{'patient_ids':value['patient_ids'][:-1]},
                       {'patient_ids':[value['patient_ids'][0]]*12},{'latent':'PRIVACY_SENTINEL'}):
            with self.assertRaises(d.Data03Error):d.validate_generation(dict(value,**update))

    def test_generation_persistence_failure_stops_before_workspace(self):
        class Response:
            content=d.encoded(generation());status_code=200
            def json(self):return generation()
        # Test the same exclusive output seam with an existing response file;
        # no fallback/replacement can overwrite a pre-existing private export.
        with tempfile.TemporaryDirectory(dir='artifacts') as folder:
            exports=d.Exports(Path(folder)/'exports');exports.once('generation-response.json',b'prior',raw=True)
            with self.assertRaises(d.Data03Error):exports.once('generation-response.json',Response.content,raw=True)
            self.assertEqual((exports.root/'generation-response.json').read_bytes(),b'prior')
        source=ast.parse(Path(d.__file__).read_text())
        run=next(n for n in source.body if isinstance(n,ast.FunctionDef) and n.name=='run_driver')
        freeze=next(n for n in ast.walk(run) if isinstance(n,ast.FunctionDef) and n.name=='freeze_generation')
        self.assertEqual([n.func.attr for n in ast.walk(freeze) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='once'],['once','once'])

    def test_output_quota_counts_every_export_and_newline(self):
        with tempfile.TemporaryDirectory(dir='artifacts') as folder:
            exports=d.Exports(Path(folder)/'exports')
            with mock.patch.object(d,'FILE_CAP',20),mock.patch.object(d,'EXPORT_CAP',30):
                exports.once('declaration.json',{'a':1})
                exports.once('credentials.json',b'x'*20,raw=True)
                self.assertEqual(sum(exports.sizes.values()),28)
                with self.assertRaises(d.Data03Error):exports.once('selection.json',b'123',raw=True)
                with self.assertRaises(d.Data03Error):exports.once('unexpected.json',b'',raw=True)
                with self.assertRaises(d.Data03Error):exports.once('observed-day36.json',b'x'*21,raw=True)

    def test_timer_spans_response_receipt_and_uses_remaining_common_lease(self):
        arms=[];clock=[100.0];events=[]
        timer=d.RequestLimit(140.0,wall=lambda:clock[0],arm=lambda kind,value:arms.append(value))
        with timer.hold():events.extend(('response','status','receipt_frozen'))
        self.assertEqual(events,['response','status','receipt_frozen']);self.assertEqual(arms,[40.0,0])
        clock[0]=141
        with self.assertRaises(d.Data03Error):
            with timer.hold():self.fail('expired lease entered')
        writes=[]
        def exit_process(code):events.append(('whole_process_exit',code));raise SystemExit(code)
        timer=d.RequestLimit(500,arm=lambda *_:None,write=lambda fd,data:writes.append(data),exit_process=exit_process)
        with self.assertRaises(SystemExit):timer.expired()
        self.assertEqual(events[-1],('whole_process_exit',124))
        self.assertEqual(json.loads(writes[0]),{'kind':'n_data03_error','code':'request_deadline'})

    def test_180_timer_is_only_http_scope_not_init_export_or_general_persistence(self):
        tree=ast.parse(Path(d.__file__).read_text())
        run=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='run_driver')
        barrier=next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='barrier')
        def holds(node):return [n for n in ast.walk(node) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='hold']
        self.assertEqual(holds(run),[]);self.assertEqual(holds(barrier),[])
        call=next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='call')
        self.assertEqual(len(holds(call)),1)
        self.assertIn('consume(response)',ast.unparse(call))

    def test_zero_analysis_checks_orphans_nonqueued_and_unknown_pending_reasons(self):
        d.no_analysis_jobs(0,[])
        d.no_analysis_jobs(0,[('unavailable',d.ORDINARY_UNAVAILABLE_REASON)])
        for attempts,rows in ((1,[]),(0,[('completed','N analysis queued')]),
                (0,[('unavailable','N analysis queued')]),(0,[('failed','Joint cohort analysis queued')]),
                (0,[('unavailable','unknown')]),(0,[('queued',d.ORDINARY_UNAVAILABLE_REASON)])):
            with self.assertRaises(d.Data03Error):d.no_analysis_jobs(attempts,rows)

    def test_unknown_mutation_is_never_resent(self):
        class Limit:
            def hold(self):
                from contextlib import nullcontext
                return nullcontext()
        client=mock.Mock();client.request.side_effect=TimeoutError('PRIVATE_SENTINEL')
        p=d.Physician(None,None,None,None,None,None,Limit(),None)
        with self.assertRaisesRegex(d.Data03Error,'unknown_mutation'):
            p.call(client,'POST','/fixed',mutation=True)
        self.assertEqual(client.request.call_count,1)

    def test_denial_requires_unchanged_versions_events_assignments(self):
        p=d.Physician(None,None,None,None,None,None,None,None)
        p.state_counts=mock.Mock(side_effect=[('same',),('same',)])
        request=mock.Mock();p.denied(request);request.assert_called_once_with()
        p.state_counts=mock.Mock(side_effect=[('before',),('changed',)])
        with self.assertRaises(d.Data03Error):p.denied(request)

    def test_fixed_advance_sequence_all_members_and_both_barriers(self):
        p=d.Physician(None,None,None,None,None,None,None,mock.Mock())
        p.workspace=mock.Mock(return_value={'snapshot':{'patient_version':7},'simulation':{'day':36}})
        captured=[]
        def command(*args,**kwargs):captured.append(args[3]()['mode'])
        p.command=command
        for index,patient in enumerate(generation()['patient_ids'],1):p.advance(patient,index,36)
        self.assertEqual(captured,(['visit']*2+['day']*8)*12)
        p.workspace.return_value['simulation']['day']=72;captured.clear()
        for index,patient in enumerate(generation()['patient_ids'],1):p.advance(patient,index,72)
        self.assertEqual(captured,(['visit']*3+['day']*2)*12);self.assertEqual(p.advances,180)

    def test_reauthentication_precedes_payload_and_expiry_after_payload_is_not_resent(self):
        events=[];p=d.Physician(None,None,None,None,None,mock.Mock(),None,None)
        p.live=lambda *_:events.append('reauth_before_payload')
        p.live_once=lambda *_:dict(csrf='private-csrf')
        p.call=lambda *_args,**_kwargs:events.append('one_dispatch')
        p.command(None,'owner','/fixed',lambda:(events.append('fresh_snapshot_payload') or {}),'stage',1,'step')
        self.assertEqual(events,['reauth_before_payload','fresh_snapshot_payload','one_dispatch'])
        def expired(*_):raise d.Data03Error()
        p.live_once=expired;p.call=mock.Mock()
        with self.assertRaises(d.Data03Error):p.command(None,'owner','/fixed',lambda:{},'stage',1,'step')
        p.call.assert_not_called()

    def test_exact_owned_handle_cleanup_not_reported_pid(self):
        process=mock.Mock();process.poll.return_value=None;process.wait.return_value=-9
        self.assertEqual(d.terminate_child(process),(-9,True));process.kill.assert_called_once_with()
        process.wait.side_effect=subprocess.TimeoutExpired('fixed',2)
        self.assertEqual(d.terminate_child(process),(None,False))
        self.assertEqual(process.wait.call_args,mock.call(timeout=2))

    def test_public_parser_denies_private_unknown_nonfinite_and_duplicate(self):
        good=dict(kind='n_data03_phase',stage='cohort_frozen',ordinal=0,day=0,seconds=1.0)
        self.assertEqual(d.parse_rows(d.encoded(good)),[good])
        for raw in (d.encoded(dict(good,auth_generation='PRIVATE_SENTINEL')),
                    b'{"kind":"n_data03_error","kind":"n_data03_error","code":"driver_failed"}\n',
                    b'{"kind":"n_data03_phase","stage":"initialized","ordinal":0,"day":0,"seconds":NaN}\n',
                    d.encoded(dict(good,stage='PRIVATE_SENTINEL')),b'PRIVATE_SENTINEL\n'):
            with self.assertRaises((d.Data03Error,ValueError)):d.parse_rows(raw)

    def test_public_cap_includes_encoded_separators_and_custody_reserve(self):
        sink=[];public=d.Public(sink.append,clock=lambda:0)
        row=dict(kind='n_data03_error',code='driver_failed');size=len(d.encoded(row))
        with mock.patch.object(d,'DRIVER_CAP',size):
            public.send(row)
            with self.assertRaises(d.Data03Error):public.send(row)
        self.assertEqual(sum(map(len,sink)),size)
        self.assertEqual(d.DRIVER_CAP+4096,d.STDOUT_CAP)

    def test_wrong_member_owner_version_panel_and_cutoff_reject_before_export(self):
        selection=d.validate_generation(generation());rows=[];snapshots={};origin=datetime(2026,1,1,12,tzinfo=timezone.utc)
        law={'id':'LAW'};protocol={'id':'N'}
        for index,patient in enumerate(selection['generation_order']):
            state={'simulation':dict(day=36,origin=origin.isoformat(),family='nof1_med',law_version='LAW',law=law,protocol=protocol,
                panel_id=selection['panel_id'],seed=d.SEED,index=index,nof1=dict(start_day=0,uninterrupted=True,status='active'))}
            row=dict(id=patient,owner_id='owner',version=7,state_version=6,consent_version=2,eligibility_version=6,
                current_decision='decision-'+patient,cutoff=(origin+timedelta(days=36)).isoformat(),state_json=json.dumps(state))
            rows.append(row);snapshots[patient]=dict(record_id=row['current_decision'],patient_version=7,state_version=6,
                consent_version=2,eligibility_version=6,cutoff=row['cutoff'])
        self.assertEqual(d.admit_rows(rows,selection,snapshots,'owner',36,law,protocol),origin+timedelta(days=36))
        for field,value in (('owner_id','other'),('version',8),('cutoff',origin.isoformat())):
            bad=copy.deepcopy(rows);bad[0][field]=value
            with self.assertRaises(d.Data03Error):d.admit_rows(bad,selection,snapshots,'owner',36,law,protocol)
        for key,value in (('panel_id','other'),('seed',123),('index',7),('day',72)):
            bad=copy.deepcopy(rows);state=json.loads(bad[0]['state_json']);state['simulation'][key]=value;bad[0]['state_json']=json.dumps(state)
            with self.assertRaises(d.Data03Error):d.admit_rows(bad,selection,snapshots,'owner',36,law,protocol)
        with self.assertRaises(d.Data03Error):d.admit_rows(rows[:-1],selection,snapshots,'owner',36,law,protocol)

    def test_real_scalar_readiness_keeps_twelve_and_sparse_peer(self):
        from tests.contracts.test_nof1_app import scalar_fixture
        from contracts.domain.nof1_app import readiness
        ids=generation()['patient_ids'];histories=[scalar_fixture(p,arms=('MED_A',)*4 if i==0 else ('MED_A','MED_B','MED_A','MED_B')) for i,p in enumerate(ids)]
        self.assertEqual(len(histories),12);self.assertEqual(readiness(histories,ids[6])['status'],'eligible')
        self.assertEqual(readiness(histories,ids[0])['status'],'inconclusive')
        with self.assertRaises(ValueError):readiness(histories[:-1]+[scalar_fixture(ids[-1],review=27)],ids[6])

    def test_no_production_edit_or_forbidden_admission_call(self):
        tree=ast.parse(Path(d.__file__).read_text())
        names=[n.func.id if isinstance(n.func,ast.Name) else n.func.attr if isinstance(n.func,ast.Attribute) else '' for n in ast.walk(tree) if isinstance(n,ast.Call)]
        for forbidden in ('prepare','make_input','NInput','NRequest','NSubmission','submit','claim','fit'):
            self.assertNotIn(forbidden,names)
        source=Path(d.__file__).read_text()
        self.assertIn('PRAGMA query_only=ON',source)
        self.assertIn("if day==72:",source)
        self.assertIn("canonical(historical)==canonical(receipt36['histories'])",source)


class Data03OperatorSource(unittest.TestCase):
    def test_bounded_capture_accepts_boundary_rejects_one_sentinel(self):
        with tempfile.TemporaryDirectory(dir='artifacts') as folder:
            path=Path(folder)/'public.stdout';path.write_bytes(b'x'*8)
            self.assertEqual(op.bounded_stdout(path,8),b'x'*8)
            path.write_bytes(b'x'*9)
            with self.assertRaises(ValueError):op.bounded_stdout(path,8)
        source=ast.parse(Path(op.__file__).read_text())
        capture=next(n for n in source.body if isinstance(n,ast.FunctionDef) and n.name=='bounded_stdout')
        reads=[n for n in ast.walk(capture) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=='read']
        self.assertEqual(len(reads),1);self.assertEqual(ast.unparse(reads[0].args[0]),'cap + 1')

    def test_single_selected_network_exact_and_empty_no_fallback(self):
        value=dict(Id=op.NETWORK,Name=op.NETWORK_NAME,Driver='bridge',Internal=True,
            Labels={'remission.task':'remission-cloud-fixture-6e48c02af5b9'},
            IPAM=[{'Subnet':'10.253.240.0/28','Gateway':'10.253.240.1'}],Containers={})
        op.audit_network(value,empty=True)
        for update in ({'Id':'b'*64},{'Internal':False},{'Containers':{'unexpected':{}}},
                {'IPAM':[{'Subnet':'10.0.0.0/28','Gateway':'10.0.0.1'}]},{'Extra':'PRIVATE_SENTINEL'}):
            with self.assertRaises(ValueError):op.audit_network(dict(value,**update),empty=True)

    def test_two_live_roles_and_pure_setup_role_mount_resource_arguments(self):
        spec=dict(namespace='remission-n-data03-261023-r1',volume='fresh-positive',carrier='C:/fixed/public/carrier')
        for role,image,user in (('app',op.APP,'10001:10001'),('generator',op.GEN,'20000:20000'),('ownership',op.OWNER,'0:0')):
            argv=op.create_argv(spec,role,1000)
            self.assertIn(image,argv);self.assertEqual(argv[argv.index('--user')+1],user)
            self.assertEqual(argv[argv.index('--pids-limit')+1],'64')
            self.assertEqual(argv[argv.index('--cpus')+1],'2')
            self.assertEqual(argv[argv.index('--memory')+1],argv[argv.index('--memory-swap')+1])
            self.assertEqual(argv[argv.index('--tmpfs')+1],'/tmp:rw,noexec,nosuid,nodev,size=128m')
            self.assertNotIn('--publish',argv);self.assertNotIn('--rm',argv)
            if role=='generator':self.assertNotIn('--mount',argv)
            if role=='ownership':self.assertEqual(argv[argv.index('--cap-add')+1],'CHOWN')
            else:self.assertNotIn('--cap-add',argv)

    def test_generator_mismatched_pid_nan_nested_no_attach_diagnostics_serialize(self):
        for invalid in ('pid','nan','nested','dead'):
            with self.subTest(invalid=invalid),tempfile.TemporaryDirectory(dir='artifacts') as folder:
                life=SimpleNamespace(__file__='C:/fixed/analysis_lifecycle.py',check_deadline=lambda _:None,
                    reap=lambda child:0 if child is not None else None)
                with mock.patch.object(op.secrets,'token_hex',return_value='a'*48):
                    gen=op.Generator('b'*64,Path(folder)/'generator',1000.0,life)
                watch=mock.Mock(pid=41);watch.poll.side_effect=[None,0] if invalid=='dead' else None
                if invalid!='dead':watch.poll.return_value=None
                def fake_popen(*_args,**_kwargs):
                    ready=dict(cid='b'*64,nonce='a'*48,deadline=1000.0,pid=41)
                    if invalid=='pid':ready['pid']=42
                    if invalid=='nan':ready['deadline']=float('nan')
                    if invalid=='nested':ready['pid']={'private':'PRIVATE_SENTINEL'}
                    (gen.folder/'watchdog-ready.json').write_text(json.dumps(ready))
                    return watch
                with mock.patch.object(op.subprocess,'Popen',side_effect=fake_popen) as popen:
                    with self.assertRaises(ValueError):gen.start()
                    self.assertEqual(popen.call_count,1)
                diagnostic=json.loads((gen.folder/'prearm.json').read_bytes())
                self.assertFalse(diagnostic['live_ack_before_start'])
                self.assertNotIn('PRIVATE_SENTINEL',json.dumps(diagnostic,allow_nan=False))
                gen.reap()
                self.assertTrue(json.loads((gen.folder/'process-reaping.json').read_bytes())['watchdog']['reaped'])

    def test_unknown_metadata_terminal_stops_worker_without_next_command(self):
        class StopUnknown(RuntimeError):pass
        life=SimpleNamespace(StopUnconfirmed=StopUnknown)
        calls=[]
        def command_attempt(*args):
            calls.append(args)
            return {'timed_out':True,'cli_terminal':'OWNED_POPEN_CHILD_EXIT_OBSERVED'}
        runner=SimpleNamespace(command_attempt=command_attempt)
        with tempfile.TemporaryDirectory(dir='artifacts') as folder:
            packet=Path(folder);(packet/'attempt').mkdir()
            spec=dict(images={'app':op.APP,'generator':op.GEN,'ownership':op.OWNER})
            with mock.patch.object(op,'module',side_effect=[life,runner]):
                code=op.worker(packet,spec,time.monotonic(),time.time()+7140,time.monotonic()+7200)
            result=json.loads((packet/'attempt/operation-terminal.json').read_bytes())
            self.assertEqual(code,2);self.assertEqual(len(calls),1)
            self.assertEqual(result['status'],'STOP UNCONFIRMED')
            self.assertIn('selected_command_or_create_outcome',result['unresolved'])

    def test_unknown_create_never_becomes_plain_failure(self):
        tree=ast.parse(Path(op.__file__).read_text())
        worker=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='worker')
        # The exact branch recognizes both container and volume creates, before
        # returning an untrusted CID; runtime doubles above prove STOP retention.
        text=ast.unparse(worker)
        self.assertIn("['create']",text);self.assertIn("['volume', 'create']",text)
        self.assertIn("raise life.StopUnconfirmed('selected create outcome UNKNOWN')",text)
        self.assertIn("raise life.StopUnconfirmed('literal selected create CID UNKNOWN')",text)

    def test_malformed_created_cid_halts_without_discovery_or_foreign_cleanup(self):
        class StopUnknown(RuntimeError):pass
        def require_cid(value):
            if len(value)!=64 or any(c not in '0123456789abcdef' for c in value):raise ValueError('bad fixture CID')
            return value
        life=SimpleNamespace(StopUnconfirmed=StopUnknown,require_cid=require_cid)
        calls=[];namespace='remission-n-data03-261023-r1'
        def command_attempt(argv,*_args):
            calls.append(argv)
            if argv[1:3]==['image','inspect']:
                image=argv[-1];value=dict(Id=image,Os='linux',Architecture='amd64',User='20000:20000' if image==op.GEN else '10001:10001')
                stdout=json.dumps(value)
            elif argv[1:3]==['network','inspect']:
                stdout=json.dumps(dict(Id=op.NETWORK,Name=op.NETWORK_NAME,Driver='bridge',Internal=True,
                    Labels={'remission.task':'remission-cloud-fixture-6e48c02af5b9'},IPAM=[dict(Subnet='10.253.240.0/28',Gateway='10.253.240.1')],Containers={}))
            elif argv[1:3]==['volume','create']:stdout=namespace+'-positive'
            elif argv[1]=='create':stdout='ambiguous fixture output'
            else:stdout=''
            return dict(timed_out=False,deadline_rejected=False,cli_terminal='OWNED_POPEN_CHILD_EXIT_OBSERVED',
                exit=0,error=None,stdout_snapshot_truncated=False,stderr_snapshot_truncated=False,stdout=stdout)
        with tempfile.TemporaryDirectory(dir='artifacts') as folder:
            packet=Path(folder);(packet/'attempt').mkdir()
            spec=dict(namespace=namespace,volume=namespace+'-positive',carrier='C:/fixed/public/carrier',images={'app':op.APP,'generator':op.GEN,'ownership':op.OWNER})
            with mock.patch.object(op,'module',side_effect=[life,SimpleNamespace(command_attempt=command_attempt)]):
                code=op.worker(packet,spec,time.monotonic(),time.time()+7140,time.monotonic()+7200)
            result=json.loads((packet/'attempt/operation-terminal.json').read_bytes())
            self.assertEqual(code,2);self.assertEqual(result['status'],'STOP UNCONFIRMED')
            self.assertEqual(result['owned_cids'],{});self.assertEqual(calls[-1][1],'create')
            self.assertFalse(any('stop' in argv or 'kill' in argv for argv in calls))

    def test_source_has_no_network_create_removal_or_global_discovery(self):
        tree=ast.parse(Path(op.__file__).read_text())
        lists=[n for n in ast.walk(tree) if isinstance(n,ast.List)]
        for node in lists:
            literals=[x.value for x in node.elts if isinstance(x,ast.Constant) and type(x.value) is str]
            self.assertNotEqual(literals[:3],['docker','network','create'])
            self.assertFalse(set(literals)&{'prune','disconnect','restart','rm','rmi'})
        self.assertEqual(op.BOUNDS,dict(outer=7200,work=7140,setup=180,ownership=30,readiness=30,request=180,metadata=5,create=10,cli_reap=2))


class Data03CapabilitySource(unittest.TestCase):
    @staticmethod
    def inverse(tree):
        tree=copy.deepcopy(tree)
        audit=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='audit_created')
        loop=next(n for n in audit.body if isinstance(n,ast.For) and isinstance(n.iter,ast.Call) and isinstance(n.iter.func,ast.Attribute) and n.iter.func.attr=='items')
        assert len(loop.body)==1 and isinstance(loop.body[0],ast.If)
        loop.body=loop.body[0].orelse
        count=0
        for node in ast.walk(tree):
            if isinstance(node,ast.Constant) and node.value=='remission-n-data03-261023-r2':node.value='remission-n-data03-261023-r1';count+=1
        assert count==1
        return tree

    @staticmethod
    def fixture(role='ownership'):
        value=json.loads(CAPTURED_CREATED_RAW);cid=value['Id']
        spec=dict(namespace='remission-n-data03-261023-r1',volume='remission-n-data03-261023-r1-positive',carrier='C:/fixed/public/carrier',
                  images={'app':op.APP,'generator':op.GEN,'ownership':op.OWNER})
        argv=op.create_argv(spec,role,1234.)
        if role!='ownership':
            value.update(Image=op.APP if role=='app' else op.GEN,User='10001:10001' if role=='app' else '20000:20000',
                Memory=2147483648,MemorySwap=2147483648,CapAdd=None,NetworkMode=op.NETWORK_NAME,
                Args=argv[argv.index('--entrypoint')+3:])
            value['Mounts']=[] if role=='generator' else [value['Mounts'][0],dict(Type='bind',Source=spec['carrier'],Destination='/carrier',RW=False)]
            value['Networks']={op.NETWORK_NAME:dict(NetworkID=op.NETWORK,Aliases=['generator'] if role=='generator' else [])}
        return value,cid,spec,argv

    def test_real_captured_fixture_old_rejection_both_exact_spellings_and_requested_argv(self):
        self.assertEqual(hashlib.sha256(CAPTURED_CREATED_RAW).hexdigest(),'10632f912753f83b452c11c2cc436e14736a5e266b3a4449915307b5a6b6bbac')
        self.assertEqual(hashlib.sha256(CAPTURED_CREATE_RAW).hexdigest(),'e89e328eb46eebdb81add64cf2dbfc873ff00a58649ed0b7a2b80d139f7bf92b')
        value,cid,spec,argv=self.fixture()
        self.assertEqual(argv,json.loads(CAPTURED_CREATE_RAW)['argv'])
        tree=self.inverse(ast.parse(startup_inverse_source(Path(op.__file__).read_text())))
        audit=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='audit_created')
        namespace=dict(op.__dict__);exec(compile(ast.Module(body=[audit],type_ignores=[]),'original_R1_audit_only','exec'),namespace)
        with self.assertRaises(ValueError):namespace['audit_created'](value,cid,spec,'ownership',argv,frozen_life)
        for caps in (['CHOWN'],['CAP_CHOWN']):
            with self.subTest(caps=caps):op.audit_created(dict(value,CapAdd=caps),cid,spec,'ownership',argv,frozen_life)

    def test_singleton_exact_types_only_and_live_roles_still_none(self):
        value,cid,spec,argv=self.fixture()
        class StringSubclass(str):pass
        class ListSubclass(list):pass
        invalid=(None,[],['CHOWN','CHOWN'],['CHOWN','CAP_CHOWN'],['CAP_CHOWN','DAC_OVERRIDE'],['FOWNER'],
            ['cap_chown'],['CAP_CAP_CHOWN'],'CHOWN',('CHOWN',),[1],[True],[None],[StringSubclass('CHOWN')],ListSubclass(['CHOWN']))
        for caps in invalid:
            with self.subTest(caps=caps),self.assertRaises(ValueError):op.audit_created(dict(value,CapAdd=caps),cid,spec,'ownership',argv,frozen_life)
        missing=dict(value);missing.pop('CapAdd')
        with self.assertRaises(ValueError):op.audit_created(missing,cid,spec,'ownership',argv,frozen_life)
        for role in ('app','generator'):
            value,cid,spec,argv=self.fixture(role);op.audit_created(value,cid,spec,role,argv,frozen_life)
            for caps in ([],['CHOWN'],['CAP_CHOWN'],['DAC_OVERRIDE']):
                with self.subTest(role=role,caps=caps),self.assertRaises(ValueError):op.audit_created(dict(value,CapAdd=caps),cid,spec,role,argv,frozen_life)
            if role=='app':
                changed=copy.deepcopy(value);changed['Mounts'][1]['Source']='C:/other/public/carrier'
                with self.assertRaises(ValueError):op.audit_created(changed,cid,spec,role,argv,frozen_life)

    def test_each_remaining_protected_mutation_stops_before_supervision_and_only_owned_cid_cleanup(self):
        original,cid,spec,argv=self.fixture()
        mutations={
            'Id':lambda v:v.update(Id='f'*64),'Image':lambda v:v.update(Image=op.APP),'User':lambda v:v.update(User='10001:10001'),
            'Labels':lambda v:v.update(Labels={}), 'Memory':lambda v:v.update(Memory=2147483648),
            'MemorySwap':lambda v:v.update(MemorySwap=0),'NanoCpus':lambda v:v.update(NanoCpus=1000000000),
            'PidsLimit':lambda v:v.update(PidsLimit=64.),'ReadonlyRootfs':lambda v:v.update(ReadonlyRootfs=False),
            'Privileged':lambda v:v.update(Privileged=True),'CapDrop':lambda v:v.update(CapDrop=[]),
            'CapAdd':lambda v:v.update(CapAdd=None),'AutoRemove':lambda v:v.update(AutoRemove=True),
            'SecurityOpt':lambda v:v.update(SecurityOpt=[]),'Tmpfs':lambda v:v.update(Tmpfs={}),
            'NetworkMode':lambda v:v.update(NetworkMode=op.NETWORK_NAME),'PublishAllPorts':lambda v:v.update(PublishAllPorts=True),
            'RestartPolicy':lambda v:v.update(RestartPolicy={'Name':'always','MaximumRetryCount':0}),
            'Path':lambda v:v.update(Path='other'),'Args':lambda v:v.update(Args=[]),
            'PortBindings':lambda v:v.update(PortBindings={'1/tcp':[]}),
            'State.status':lambda v:v['State'].update(Status='exited'),'State.pid':lambda v:v['State'].update(Pid=1),
            'Mount.name':lambda v:v['Mounts'][0].update(Name='foreign'),
            'Mount.destination':lambda v:v['Mounts'][0].update(Destination='/other'),
            'Mount.RW':lambda v:v['Mounts'][0].update(RW=False),'Mount.type':lambda v:v['Mounts'][0].update(Type='bind')}
        for name,mutate in mutations.items():
            with self.subTest(field=name),tempfile.TemporaryDirectory(dir='artifacts') as folder:
                value=copy.deepcopy(original);mutate(value)
                with self.assertRaises(ValueError):op.audit_created(value,cid,spec,'ownership',argv,frozen_life)
                calls=[];stops=[];supervise=mock.Mock(side_effect=AssertionError('no start allowed'))
                final=dict(Id=cid,RestartCount=0,State=copy.deepcopy(original['State']))
                life=SimpleNamespace(StopUnconfirmed=frozen_life.StopUnconfirmed,checked_state=frozen_life.checked_state,
                    require_cid=frozen_life.require_cid,supervise=supervise,stop_owned=lambda owned:stops.append(owned) or [],
                    inspect=lambda owned:final,stopped=frozen_life.stopped)
                def command_attempt(command,*_args):
                    calls.append(command)
                    if command[1:3]==['image','inspect']:
                        image=command[-1];stdout=json.dumps(dict(Id=image,Os='linux',Architecture='amd64',User='20000:20000' if image==op.GEN else '10001:10001'))
                    elif command[1:3]==['network','inspect']:
                        stdout=json.dumps(dict(Id=op.NETWORK,Name=op.NETWORK_NAME,Driver='bridge',Internal=True,
                            Labels={'remission.task':'remission-cloud-fixture-6e48c02af5b9'},IPAM=[dict(Subnet='10.253.240.0/28',Gateway='10.253.240.1')],Containers={}))
                    elif command[1:3]==['volume','create']:stdout=spec['volume']
                    elif command[1]=='create':stdout=cid
                    elif command[1]=='inspect':stdout=json.dumps(value)
                    else:stdout=''
                    return dict(exit=0,timed_out=False,deadline_rejected=False,cli_terminal='OWNED_POPEN_CHILD_EXIT_OBSERVED',error=None,
                                stdout_snapshot_truncated=False,stderr_snapshot_truncated=False,stdout=stdout)
                packet=Path(folder);(packet/'attempt').mkdir()
                with mock.patch.object(op,'module',side_effect=[life,SimpleNamespace(command_attempt=command_attempt)]),mock.patch.object(op,'Generator') as generator:
                    code=op.worker(packet,spec,time.monotonic(),time.time()+7140,time.monotonic()+7200)
                self.assertEqual(code,1);supervise.assert_not_called();generator.assert_not_called()
                self.assertEqual(stops,[cid]);self.assertEqual(sum(command[1]=='create' for command in calls),1)
                result=json.loads((packet/'attempt/operation-terminal.json').read_bytes())
                self.assertEqual(result['owned_cids'],{'ownership':cid});self.assertEqual(result['unresolved'],[])

    def test_inverse_entire_operator_is_only_enum_and_new_namespace(self):
        tree=ast.parse(startup_inverse_source(Path(op.__file__).read_text()));inverse=self.inverse(tree)
        self.assertEqual(hashlib.sha256(ast.dump(inverse,include_attributes=False).encode()).hexdigest(),'c354ffada53e03660ec6a7e52b2e55c3d8808a96284da4b397bdaba47278a8ce')
        expected=dict(create_argv='18cfee67c62604d20df2409974c6d6a8dd1b48f542100ba04f0d69ed26a5acf7',
            worker='229540e0a773093f3384786c538027249f53184ce830980a86c229d9e2b6ec56',launch='358aca3d7def0674232d69d50f7bdb7d9168111a747d882dfacce887f6c6ac97')
        for name,digest in expected.items():
            node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name)
            self.assertEqual(hashlib.sha256(ast.dump(node,include_attributes=False).encode()).hexdigest(),digest)


class Data03StartupSource(unittest.TestCase):
    def rename_double(self,source,destination):
        # Inert namespace model, NOT an os.rename/native/concurrency probe.
        if destination.exists():raise FileExistsError('inert destination collision')
        destination.write_bytes(source.read_bytes());source.unlink()

    def test_both_receipts_hidden_during_partial_write_and_close_before_one_rename(self):
        for name in ('worker-ready.json','worker-ack.json'):
            with self.subTest(name=name),tempfile.TemporaryDirectory(dir='artifacts') as folder:
                root=Path(folder);final=root/name;observed=[];original_dump=op.json.dump
                def dump(value,stream,**kwargs):
                    observed.append((final.exists(),stream.closed));stream.write('{');stream.flush()
                    observed.append((final.exists(),stream.closed));stream.seek(0);stream.truncate()
                    return original_dump(value,stream,**kwargs)
                def rename(source,destination):
                    observed.append(('rename',json.loads(source.read_bytes())))
                    self.rename_double(source,destination)
                with mock.patch.object(op.json,'dump',side_effect=dump),mock.patch.object(op.os,'rename',side_effect=rename) as call:
                    op.publish_startup(root,name,{'public':1},time.monotonic()+5)
                self.assertEqual(observed,[(False,False),(False,False),('rename',{'public':1})])
                self.assertEqual(json.loads(final.read_bytes()),{'public':1});self.assertEqual(call.call_count,1)

    def test_preexisting_pending_final_and_racing_destination_never_overwritten(self):
        for name in ('worker-ready.json','worker-ack.json'):
            for case in ('pending','final','racing'):
                with self.subTest(name=name,case=case),tempfile.TemporaryDirectory(dir='artifacts') as folder:
                    root=Path(folder);final=root/name;pending=root/name.replace('.json','.pending.json')
                    if case!='racing':(pending if case=='pending' else final).write_bytes(b'prior public fixture')
                    def rename(source,destination):
                        destination.write_bytes(b'racing public fixture');self.rename_double(source,destination)
                    with mock.patch.object(op.os,'rename',side_effect=rename) as call:
                        with self.assertRaises((ValueError,FileExistsError)):op.publish_startup(root,name,{'public':1},time.monotonic()+5)
                    self.assertEqual(call.call_count,1 if case=='racing' else 0)
                    if case=='pending':self.assertEqual(pending.read_bytes(),b'prior public fixture')
                    else:self.assertEqual(final.read_bytes(),b'racing public fixture' if case=='racing' else b'prior public fixture')

    def test_write_serialization_close_rename_faults_preserve_scratch_and_no_final(self):
        for name in ('worker-ready.json','worker-ack.json'):
            for failure in ('write','serialization','close','rename'):
                with self.subTest(name=name,failure=failure),tempfile.TemporaryDirectory(dir='artifacts') as folder:
                    root=Path(folder);final=root/name;save=op.save
                    def failed_save(path,value):
                        if failure=='serialization':return save(path,{'public':float('nan')})
                        if failure=='write':
                            with path.open('x') as stream:stream.write('{');raise OSError('inert write failure')
                        save(path,value)
                        if failure=='close':raise OSError('inert close failure')
                    with mock.patch.object(op,'save',side_effect=failed_save),mock.patch.object(op.os,'rename',side_effect=OSError('inert rename failure')) as call:
                        with self.assertRaises((ValueError,OSError)):op.publish_startup(root,name,{'public':1},time.monotonic()+5)
                    self.assertFalse(final.exists());self.assertTrue((root/name.replace('.json','.pending.json')).exists())
                    self.assertEqual(call.call_count,1 if failure=='rename' else 0)

    def test_publication_cost_uses_existing_clock_and_late_complete_file_rejects(self):
        for name in ('worker-ready.json','worker-ack.json'):
            for late in ('write','rename'):
                with self.subTest(name=name,late=late),tempfile.TemporaryDirectory(dir='artifacts') as folder:
                    clock=[1.0];root=Path(folder);save=op.save
                    def saving(path,value):
                        save(path,value)
                        if late=='write':clock[0]=6.0
                    def rename(source,destination):self.rename_double(source,destination);clock[0]=6.0
                    with mock.patch.object(op,'save',side_effect=saving),mock.patch.object(op.time,'monotonic',side_effect=lambda:clock[0]),mock.patch.object(op.os,'rename',side_effect=rename) as call:
                        with self.assertRaises(ValueError):op.publish_startup(root,name,{'public':1},6.0)
                    self.assertEqual(call.call_count,0 if late=='write' else 1)
                    self.assertEqual((root/name).exists(),late=='rename') # retained late bytes are not authority

    def startup(self,case,worker=False):
        clock=[7239.0 if case.startswith('common_late_') else 100.5 if worker and case=='separate_windows' else 7240.0 if worker and case=='common_expired' else 100.0]
        nonce='a'*48;identity=dict(pid=41,ppid=42,nonce=nonce,start=100.0,outer=7300.0,lease_unix=8000.0)
        with tempfile.TemporaryDirectory(dir='artifacts') as folder:
            packet=Path(folder);events=[];code=[None];polls=[0]
            def rename(source,destination):
                self.rename_double(source,destination)
                if case in ('late_publication','late_publication_exited'):
                    clock[0]=105.0
                    if case=='late_publication_exited':code[0]=0
                if case=='common_late_work_rename':clock[0]=7240.0
                if case=='common_late_outer_rename':clock[0]=7300.0
            class Child:
                pid=41
                def __init__(self,*args,**kwargs):
                    events.append('owned_Popen_double');ready=packet/'attempt/worker-ready.json'
                    value=dict(identity,ppid=43) if case=='mismatch' else identity
                    if case=='nan_identity':value=dict(identity,start=float('nan'))
                    if case=='nested_identity':value=dict(identity,ppid={'invalid':'PRIVATE_SENTINEL'})
                    ready.write_bytes(b'{' if case=='malformed' else json.dumps(value).encode())
                    if case=='common_expired':clock[0]=7240.0
                def poll(self):
                    polls[0]+=1
                    if case=='child_exit' or (case=='child_exit_between' and polls[0]>=2):code[0]=1;return 1
                    return code[0]
                def kill(self):events.append('kill_exact_child');code[0]=1
                def wait(self,timeout):
                    events.append('wait_exact_child')
                    if case=='reap_unconfirmed':raise subprocess.TimeoutExpired('inert',timeout)
                    if code[0] is None:code[0]=0
                    return code[0]
            if worker:
                (packet/'attempt').mkdir();ack=packet/'attempt/worker-ack.json'
                value=dict(identity,ppid=43) if case=='mismatch' else dict(identity,start=float('nan')) if case=='nan_identity' else dict(identity,ppid={'invalid':'PRIVATE_SENTINEL'}) if case=='nested_identity' else identity
                ack.write_bytes(b'{' if case=='malformed' else json.dumps(value).encode())
            args=SimpleNamespace(worker=True,spec=Path('fixed-spec'),authorized_spec_sha256='fixed',authorization=Path('inert-authority'),
                start=100.0,outer=7300.0,lease_unix=8000.0,nonce=nonce)
            spec=dict(host_runtime=[],worktree='fixed-worktree',candidate_commit='fixed-candidate')
            real_loads=op.json.loads
            def loads(raw,*args,**kwargs):
                value=real_loads(raw,*args,**kwargs)
                if case=='late_read':clock[0]=105.0
                if case=='separate_windows':clock[0]=105.25
                if case=='common_late_work_read':clock[0]=7240.0
                if case=='common_late_outer_read':clock[0]=7300.0
                return value
            def metadata(argv,**kwargs):return b'fixed-candidate\n' if argv[1:]==['rev-parse','HEAD'] else b''
            with mock.patch.object(op,'validate_packet',return_value=(packet,spec)),\
                mock.patch.object(op,'os',SimpleNamespace(name='nt',getpid=lambda:41 if worker else 42,getppid=lambda:42,rename=rename)),\
                mock.patch.object(op,'time',SimpleNamespace(monotonic=lambda:clock[0],time=lambda:860.,sleep=lambda _:None)),\
                mock.patch.object(op,'sys',SimpleNamespace(executable='C:/Python313/python.exe')),\
                mock.patch.object(op,'secrets',SimpleNamespace(token_hex=lambda _:nonce)),\
                mock.patch.object(op.subprocess,'Popen',Child),mock.patch.object(op.subprocess,'check_output',side_effect=metadata),\
                mock.patch.object(op.argparse.ArgumentParser,'parse_args',return_value=args),\
                mock.patch.object(op.json,'loads',side_effect=loads),mock.patch.object(op,'worker',side_effect=lambda *a:events.append('body') or 0),\
                contextlib.redirect_stdout(io.StringIO()):
                if case in ('matching','separate_windows'):op.main() if worker else op.launch(Path('fixed-spec'),'fixed',Path('inert-authority'))
                else:
                    with self.assertRaises((ValueError,json.JSONDecodeError)):op.main() if worker else op.launch(Path('fixed-spec'),'fixed',Path('inert-authority'))
            if worker:self.assertEqual('body' in events,case in ('matching','separate_windows'))
            else:
                terminal=json.loads((packet/'attempt/launcher-terminal.json').read_bytes())
                self.assertEqual(terminal['reaped'],case!='reap_unconfirmed')
                self.assertEqual(terminal['launcher_acceptance_failed'],case!='matching')
                self.assertEqual(terminal['status'],'worker_terminal' if case=='matching' else 'STOP UNCONFIRMED')
                if case=='late_publication_exited':self.assertEqual(terminal['returncode'],0)
                if case in ('malformed','mismatch','nan_identity','nested_identity','late_read','child_exit','child_exit_between','common_expired'):self.assertFalse((packet/'attempt/worker-ack.json').exists())
            return dict(body_entered='body' in events,reader_clock=clock[0])

    def test_parent_matching_malformed_mismatch_child_exit_late_deadline_and_reap(self):
        for case in ('matching','malformed','mismatch','nan_identity','nested_identity','child_exit','child_exit_between','late_read','late_publication','late_publication_exited','common_expired','reap_unconfirmed'):
            with self.subTest(case=case):self.startup(case)

    def test_worker_matching_invalid_ACK_late_read_publication_no_body(self):
        for case in ('matching','malformed','mismatch','nan_identity','nested_identity','late_read','late_publication','common_expired'):
            with self.subTest(case=case):self.startup(case,worker=True)

    def test_separate_local_window_counterexample_is_retained_not_claimed_fixed(self):
        observed=self.startup('separate_windows',worker=True)
        self.assertEqual(observed,dict(body_entered=True,reader_clock=105.25))
        # Worker began at100.5 -> local105.5. Parent's assumed local105.0 is
        # absent from unchanged identity. This limitation is NOT repaired.
        self.assertTrue(105.0<observed['reader_clock']<105.5)

    def test_common_work_outer_expiry_after_blocking_publication_or_read_refuses(self):
        for worker in (False,True):
            for case in ('common_late_work_rename','common_late_outer_rename','common_late_work_read','common_late_outer_read'):
                with self.subTest(worker=worker,case=case):self.startup(case,worker=worker)

    def test_full_operator_inverse_confines_only_new_helper_seams_and_namespace(self):
        source=Path(op.__file__).read_text();before=startup_inverse_source(source)
        # R2 inverse/digests above independently constrain the entire restored operator.
        tree=ast.parse(source);base=ast.parse(before)
        functions=lambda t:{n.name:ast.dump(n,include_attributes=False) for n in t.body if isinstance(n,ast.FunctionDef)}
        current=functions(tree);prior=functions(base)
        self.assertEqual(set(current)-set(prior),{'publish_startup'})
        for name in prior:
            if name not in ('launch','main','validate_packet'):self.assertEqual(current[name],prior[name])
        helper=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='publish_startup')
        calls=[n for n in ast.walk(helper) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute)]
        self.assertEqual(sum(n.func.attr=='rename' for n in calls),1)
        self.assertFalse(any(n.func.attr in ('replace','unlink','remove','copy','copyfile') for n in calls))

def cutoff_fixture(day):
    selection=d.validate_generation(generation());rows=[];snapshots={}
    origin=datetime(2026,1,1,12,0,0,123456,tzinfo=timezone.utc)
    law={'id':'LAW'};protocol={'id':'N'}
    for index,patient in enumerate(selection['generation_order']):
        state={'simulation':dict(day=day,origin=origin.isoformat(),family='nof1_med',law_version='LAW',law=law,protocol=protocol,
            panel_id=selection['panel_id'],seed=d.SEED,index=index,nof1=dict(start_day=0,uninterrupted=True,status='active' if day==36 else 'completed'))}
        row=dict(id=patient,owner_id='owner',version=7,state_version=6,consent_version=2,eligibility_version=6,
            current_decision='decision-'+patient,cutoff=(origin+timedelta(days=day)).isoformat(),state_json=json.dumps(state))
        rows.append(row);snapshots[patient]=dict(record_id=row['current_decision'],patient_version=7,state_version=6,
            consent_version=2,eligibility_version=6,cutoff=row['cutoff'])
    return rows,selection,snapshots,origin,law,protocol


def cutoff_inverse(source):
    helper="def instant(value):\n    import re\n    require(not re.search(r'[.,]\\d{7}',value))\n    require(not re.search(r'[+-]\\d{2}(?::?\\d{2}){0,2}[.,]',value))\n    result=datetime.fromisoformat(value.replace('Z','+00:00'))\n    require(result.tzinfo is not None and result.utcoffset() is not None)\n    return result.astimezone(timezone.utc)\n\n\n"
    replacements=[(helper,''),
        ("        cutoff=instant(row['cutoff']);snapshot_cutoff=instant(s['cutoff']);origin=instant(sim['origin'])\n",''),
        ('and cutoff==snapshot_cutoff and sim.get',"and row['cutoff']==s['cutoff'] and sim.get"),
        ('        require(cutoff==origin+timedelta(days=day));',"        origin=datetime.fromisoformat(sim['origin']);cutoff=datetime.fromisoformat(row['cutoff'])\n        require(cutoff==origin+timedelta(days=day));")]
    for before,after in replacements:
        assert source.count(before)==1,before
        source=source.replace(before,after)
    return source


class Data03CutoffSource(unittest.TestCase):
    def admit(self,fixture,day):
        rows,selection,snapshots,_origin,law,protocol=fixture
        return d.admit_rows(rows,selection,snapshots,'owner',day,law,protocol)

    def test_actual_DecisionSnapshot_producer_serialization_old_rejects_new_accepts(self):
        from contracts.domain.entities import DecisionSnapshot
        import pydantic
        for day in (36,72):
            fixture=cutoff_fixture(day);rows,selection,snapshots,origin,law,protocol=fixture
            for row in rows:
                patient=row['id'];at=row['cutoff'];ref=dict(id='fixture',version='1',sha256='0'*64)
                value=dict(schema_version='1.0.0',synthetic=True,record_id=row['current_decision'],patient_id=patient,
                    event_at=at,recorded_at=at,available_at=at,source=dict(id='fixture',version='1',adapter='simulation',raw_sha256='0'*64),
                    lineage_id='fixture-'+patient,revision=1,supersedes=None,duplicate_of=None,record_status='active',
                    kind='decision_snapshot',cutoff=at,patient_version=7,state_version=6,consent_version=2,eligibility_version=6,
                    workflow=dict(clinical='treatment_active',learning='nof1_block',data_readiness='ready',hold_reasons=[],support_policy=ref,support_mode='frozen'),
                    view=dict(patient_id=patient,mode='current',snapshot_id=None),eligibility=[],outcome='Scalar serialization fixture',
                    horizon_days=42,estimand=ref,model=ref,posterior=None,evidence=[],policy=ref)
                raw=json.dumps(value,sort_keys=True,separators=(',',':'));before=copy.deepcopy(value)
                typed=DecisionSnapshot.model_validate_json(raw)
                snapshots[patient]=typed.model_dump(mode='json')
                self.assertEqual(value,before);self.assertEqual(raw,json.dumps(value,sort_keys=True,separators=(',',':')))
                self.assertEqual(snapshots[patient]['cutoff'],at.replace('+00:00','Z'))
                self.assertNotEqual(row['cutoff'],snapshots[patient]['cutoff'])
            old={};exec(compile(cutoff_inverse(Path(d.__file__).read_text()),'<old-driver>','exec'),old)
            frozen=copy.deepcopy(fixture)
            with self.assertRaises(old['Data03Error']):old['admit_rows'](rows,selection,snapshots,'owner',day,law,protocol)
            self.assertEqual(self.admit(fixture,day),origin+timedelta(days=day));self.assertEqual(fixture,frozen)
        print('REAL scalar DecisionSnapshot producer: Pydantic '+pydantic.__version__+'; DB +00:00 -> typed JSON Z; old rejects/new accepts days36,72/all12')

    def test_equivalent_spellings_all_members_exact_UTC_and_no_input_mutation(self):
        for day in (36,72):
            for spelling in ('identical','Z','offset','mixed'):
                fixture=cutoff_fixture(day);rows,_selection,snapshots,origin,_law,_protocol=fixture
                for index,row in enumerate(rows):
                    cutoff=origin+timedelta(days=day);state=json.loads(row['state_json'])
                    if spelling=='Z':snapshots[row['id']]['cutoff']=cutoff.isoformat().replace('+00:00','Z')
                    if spelling in ('offset','mixed'):
                        zone=timezone(timedelta(hours=5,minutes=30)) if index%2 else timezone(timedelta(hours=-7))
                        row['cutoff']=cutoff.astimezone(zone).isoformat()
                        state['simulation']['origin']=origin.astimezone(zone).isoformat()
                        snapshots[row['id']]['cutoff']=cutoff.isoformat().replace('+00:00','Z') if spelling=='mixed' else cutoff.astimezone(zone).isoformat()
                        row['state_json']=json.dumps(state)
                frozen=copy.deepcopy(fixture);actual=self.admit(fixture,day)
                self.assertEqual(actual,origin+timedelta(days=day));self.assertIs(actual.tzinfo,timezone.utc)
                self.assertEqual(actual.microsecond,123456);self.assertEqual(fixture,frozen)

    def test_each_member_invalid_timestamp_or_lineage_refuses_before_guard_export_persist(self):
        for day in (36,72):
            for index in range(12):
                cases=[]
                exact=cutoff_fixture(day)[3]+timedelta(days=day)
                for field in ('cutoff','snapshot','origin'):
                    for value in ((exact+timedelta(microseconds=1)).isoformat(),(exact+timedelta(hours=1)).isoformat(),
                                  '2026-02-06T12:00:00.123456','2026-99-06T12:00:00+00:00','2026-02-06T12:00:00+25:00','2026-02-06'):
                        cases.append((field,value))
                cases.extend((field,value) for field,value in (('owner_id','wrong'),('current_decision','wrong'),('version',8),
                    ('state_version',7),('consent_version',3),('eligibility_version',7)))
                cases.extend(('sim.'+field,value) for field,value in (('day',0),('family','wrong'),('law_version','wrong'),('law',{}),
                    ('protocol',{}),('panel_id','wrong'),('seed',0),('index',99),('research_run_id','wrong')))
                cases.extend(('loop.'+field,value) for field,value in (('start_day',1),('uninterrupted',False),('status','wrong')))
                for field,value in cases:
                    with self.subTest(day=day,member=index,field=field,value=value):
                        fixture=cutoff_fixture(day);rows,_selection,snapshots,_origin,_law,_protocol=fixture;row=rows[index]
                        if field=='snapshot':snapshots[row['id']]['cutoff']=value
                        elif field=='origin' or '.' in field:
                            state=json.loads(row['state_json']);sim=state['simulation']
                            if field.startswith('loop.'):sim['nof1'][field[5:]]=value
                            else:sim['origin' if field=='origin' else field[4:]]=value
                            row['state_json']=json.dumps(state)
                        else:row[field]=value
                        frozen=copy.deepcopy(fixture);downstream=mock.Mock()
                        with self.assertRaises((d.Data03Error,ValueError)):
                            self.admit(fixture,day);downstream.guard();downstream.export();downstream.persist()
                        self.assertEqual(downstream.mock_calls,[]);self.assertEqual(fixture,frozen)

    def test_common_origin_cutoff_and_membership_target_order_still_exact(self):
        for day in (36,72):
            for case in ('paired_shift','origin_only','missing_row','extra_row','missing_snapshot','extra_snapshot','target','order'):
                fixture=cutoff_fixture(day);rows,selection,snapshots,origin,_law,_protocol=fixture
                if case in ('paired_shift','origin_only'):
                    state=json.loads(rows[-1]['state_json']);state['simulation']['origin']=(origin+timedelta(microseconds=1)).isoformat();rows[-1]['state_json']=json.dumps(state)
                    if case=='paired_shift':rows[-1]['cutoff']=(origin+timedelta(days=day,microseconds=1)).isoformat();snapshots[rows[-1]['id']]['cutoff']=rows[-1]['cutoff']
                elif case=='missing_row':rows.pop()
                elif case=='extra_row':rows.append(copy.deepcopy(rows[-1]))
                elif case=='missing_snapshot':snapshots.pop(rows[-1]['id'])
                elif case=='extra_snapshot':snapshots['extra']=copy.deepcopy(snapshots[rows[-1]['id']])
                elif case=='target':selection['target_id']=selection['generation_order'][0]
                elif case=='order':selection['generation_order'][0],selection['generation_order'][1]=selection['generation_order'][1],selection['generation_order'][0]
                with self.assertRaises(d.Data03Error):self.admit(fixture,day)

    def test_submicrosecond_precision_rejects_without_truncation_on_each_input(self):
        for day in (36,72):
            for field in ('cutoff','snapshot','origin','both_cutoffs'):
                for suffix in ('0','1','9'):
                    fixture=cutoff_fixture(day);rows,_selection,snapshots,origin,_law,_protocol=fixture;row=rows[-1]
                    if field in ('cutoff','both_cutoffs'):row['cutoff']=row['cutoff'].replace('123456+','123456'+suffix+'+')
                    if field in ('snapshot','both_cutoffs'):snapshots[row['id']]['cutoff']=snapshots[row['id']]['cutoff'].replace('123456+','1234562+' if field=='both_cutoffs' else '123456'+suffix+'+')
                    if field=='origin':
                        state=json.loads(row['state_json']);state['simulation']['origin']=origin.isoformat().replace('123456+','123456'+suffix+'+');row['state_json']=json.dumps(state)
                    frozen=copy.deepcopy(fixture)
                    with self.assertRaises(d.Data03Error):self.admit(fixture,day)
                    self.assertEqual(fixture,frozen)
        for value in ('2026-01-01T00:00:00,1234567Z','2026-01-01T00:00:00+01:00:00.1234567'):
            with self.assertRaises(d.Data03Error):d.instant(value)

    def test_entire_driver_inverse_only_declared_scalar_timestamp_delta(self):
        source=Path(d.__file__).read_text();inverse=cutoff_inverse(source).encode()
        self.assertEqual(hashlib.sha1(b'blob '+str(len(inverse)).encode()+b'\0'+inverse).hexdigest(),'e1b7c486172c121160dff82b3ea7a96d5da38157')
        operator=Path(op.__file__).read_text()
        self.assertEqual(operator.count("'remission-n-data03-261024-r4'"),1)
        prior=operator.replace("'remission-n-data03-261024-r4'","'remission-n-data03-261024-r3'").encode()
        self.assertEqual(hashlib.sha1(b'blob '+str(len(prior)).encode()+b'\0'+prior).hexdigest(),'a7e51ea8633f24a1c4683e38146a7e314277c19c')

    def test_fractional_zero_offset_counterexample_old_collapses_new_rejects(self):
        guard="    require(not re.search(r'[+-]\\d{2}(?::?\\d{2}){0,2}[.,]',value))\n"
        source=Path(d.__file__).read_text();self.assertEqual(source.count(guard),1)
        node=next(n for n in ast.parse(source.replace(guard,'')).body if isinstance(n,ast.FunctionDef) and n.name=='instant')
        namespace=dict(datetime=datetime,timezone=timezone,require=d.require)
        exec(compile(ast.Module(body=[node],type_ignores=[]),'<superseded-scalar-parser>','exec'),namespace)
        left='2026-02-06T12:00:00+00:00:00.000001';right='2026-02-06T12:00:00Z'
        self.assertEqual(namespace['instant'](left),namespace['instant'](right))
        with self.assertRaises(d.Data03Error):d.instant(left)
        self.assertEqual(d.instant(right),datetime(2026,2,6,12,tzinfo=timezone.utc))

    def test_fractional_offset_syntax_each_member_DB_snapshot_origin_rejects(self):
        offsets=[sign+base+separator+('0'*(digits-1)+'1')
                 for sign in ('+','-') for base in ('00','00:00','00:00:00','0000','000000')
                 for separator in ('.',',') for digits in range(1,7)]
        offsets.extend(('+00:00:00.000000','-00:00:00,000000'))
        for day in (36,72):
            for index in range(12):
                for field in ('cutoff','snapshot','origin'):
                    for offset in offsets:
                        fixture=cutoff_fixture(day);rows,_selection,snapshots,origin,_law,_protocol=fixture;row=rows[index]
                        if field=='origin':
                            state=json.loads(row['state_json']);state['simulation']['origin']=origin.isoformat().replace('+00:00',offset);row['state_json']=json.dumps(state)
                        elif field=='cutoff':row['cutoff']=row['cutoff'].replace('+00:00',offset)
                        else:snapshots[row['id']]['cutoff']=snapshots[row['id']]['cutoff'].replace('+00:00',offset)
                        frozen=copy.deepcopy(fixture)
                        with self.assertRaises(d.Data03Error):self.admit(fixture,day)
                        self.assertEqual(fixture,frozen)

    def test_actual_receipt_invalid_last_member_stops_before_guard_and_export(self):
        import sys
        from contracts.domain.protocol import LAW_REF,NOF1_REF
        for day in (36,72):
            rows,selection,snapshots,_origin,_law,_protocol=cutoff_fixture(day)
            for row in rows:
                state=json.loads(row['state_json']);state['simulation'].update(law=LAW_REF,law_version=LAW_REF['id'],protocol=NOF1_REF)
                row['state_json']=json.dumps(state)
            guard=mock.Mock();export=mock.Mock()
            class DB:
                def execute(self,query,*_args):
                    if query=='PRAGMA query_only=ON':return None
                    if query=='PRAGMA query_only':return SimpleNamespace(fetchone=lambda:(1,))
                    if query.startswith('SELECT id,owner_id,'):return rows
                    raise AssertionError('unexpected downstream query')
            @contextlib.contextmanager
            def transaction(*,write):
                self.assertFalse(write);yield DB()
            modules={'services.foundation.nof1':SimpleNamespace(guard=guard),
                     'services.foundation.protocol':SimpleNamespace(export_histories=export)}
            for invalid in ('naive_snapshot','fractional_DB','fractional_snapshot','fractional_origin'):
                original_rows=copy.deepcopy(rows);original_snapshots=copy.deepcopy(snapshots)
                if invalid=='naive_snapshot':snapshots[rows[-1]['id']]['cutoff']=snapshots[rows[-1]['id']]['cutoff'].replace('+00:00','')
                elif invalid=='fractional_DB':rows[-1]['cutoff']=rows[-1]['cutoff'].replace('+00:00','+00:00:00.000001')
                elif invalid=='fractional_snapshot':snapshots[rows[-1]['id']]['cutoff']=snapshots[rows[-1]['id']]['cutoff'].replace('+00:00','-00:00:00,000001')
                else:
                    state=json.loads(rows[-1]['state_json']);state['simulation']['origin']=state['simulation']['origin'].replace('+00:00','+00:00:00.000001');rows[-1]['state_json']=json.dumps(state)
                with mock.patch.dict(sys.modules,modules),self.assertRaises(d.Data03Error):
                    d.receipt(SimpleNamespace(transaction=transaction),'owner',selection,snapshots,day)
                guard.assert_not_called();export.assert_not_called()
                rows[:]=original_rows;snapshots.clear();snapshots.update(original_snapshots)

    def test_source_tripwires_reject_science_app_Store_SQLite_network_and_process(self):
        import importlib
        import socket
        for name in ('numpy','scipy','pymc','pandas','arviz','statsmodels','xarray','services.foundation.app','services.foundation.store','sqlite3'):
            with self.assertRaises(AssertionError):importlib.import_module(name)
        with self.assertRaises(AssertionError):subprocess.Popen(['forbidden'])
        with self.assertRaises(AssertionError):socket.create_connection(('forbidden',1))


if __name__=='__main__':unittest.main()
