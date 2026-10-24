"""Meaningful fixed-driver invariants, with process/app/Store imports blocked."""
import ast
import copy
from datetime import datetime,timedelta,timezone
import json
from pathlib import Path
import subprocess
import tempfile
import time
from types import SimpleNamespace
from unittest import mock
import unittest

import n_data03_driver as d
import n_data03 as op

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


if __name__=='__main__':unittest.main()
