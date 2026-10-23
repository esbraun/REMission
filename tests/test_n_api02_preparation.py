"""Host source-only checks: scientific payload is parsed, never imported/run."""
import ast
import hashlib
import importlib.util
from pathlib import Path
import subprocess
import unittest
from types import SimpleNamespace
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('draft',ROOT/'tooling/foundation/n_api02_draft.py')
draft=importlib.util.module_from_spec(spec);spec.loader.exec_module(draft)

class DraftControls(unittest.TestCase):
    def test_unknown_created_cid_stops_without_start_or_cleanup_guess(self):
        payload='UNIT_NOT_EXECUTED';image='sha256:'+'a'*64;config=dict(Id=image,User='10002:10002',WorkingDir='/app',Entrypoint=None,Cmd=['original'])
        plan=dict(learner_image=image,payload_sha256=hashlib.sha256(payload.encode()).hexdigest(),qualified_image_config=config)
        class StopUnconfirmed(RuntimeError):pass
        calls=[]
        def call(argv,label,deadline):
            calls.append(label)
            if label=='image':return __import__('json').dumps(config)
            if label=='absence':return ''
            if label=='create':return 'UNKNOWN'
            raise AssertionError('no later command permitted')
        def require(value):raise ValueError('not literalCID')
        life=SimpleNamespace(require_cid=require,StopUnconfirmed=StopUnconfirmed,stop_owned=lambda cid:(_ for _ in ()).throw(AssertionError('no guessed cleanup')))
        with self.assertRaises(StopUnconfirmed):draft._controller_body(plan,payload,ROOT,life,call)
        self.assertEqual(calls,['image','absence','create'])

    def test_payload_change_fails_before_any_image_or_native_command(self):
        with self.assertRaisesRegex(ValueError,'payload changed'):
            draft._controller_body(dict(payload_sha256='0'*64),'UNIT_NOT_EXECUTED',ROOT,None,
                lambda *a:(_ for _ in ()).throw(AssertionError('command forbidden')))

    def test_pending_dependency_cannot_reach_child_creation(self):
        value=draft.inspect_draft(ROOT/'docs/implementation/poc-n-api02.draft.json')
        with patch.object(subprocess,'Popen',side_effect=AssertionError('native child denied')):
            with self.assertRaisesRegex(RuntimeError,'DRAFT'):draft.execute_draft(value)
            with self.assertRaisesRegex(ValueError,'unavailable'):draft.proposed_argv(None,'never run')
        self.assertIsNone(value['accepted_image_evidence']);self.assertFalse(value['executable_final_spec'])

    def test_planned_container_has_no_mounts_network_or_root_write(self):
        argv=draft.proposed_argv('sha256:'+'a'*64,'UNIT_PAYLOAD_NOT_EXECUTED')
        self.assertNotIn('--mount',argv);self.assertNotIn('-v',argv);self.assertNotIn('-p',argv)
        for key,value in [('--network','none'),('--user','10002:10002'),('--cpus','2'),('--pids-limit','64'),('--memory','2g'),('--memory-swap','2g')]:
            self.assertEqual(argv[argv.index(key)+1],value)
        self.assertIn('--read-only',argv);self.assertEqual(argv[-5:],['python','-I','-B','-c','UNIT_PAYLOAD_NOT_EXECUTED'])

    def test_payload_ast_has_no_fit_or_store_call_and_no_host_top_level_science(self):
        text=(ROOT/'tooling/foundation/n_api02_unit.py').read_text(encoding='utf-8');tree=ast.parse(text)
        self.assertEqual([n.name for n in tree.body if isinstance(n,ast.FunctionDef)],['main'])
        self.assertFalse(any(isinstance(n,(ast.Import,ast.ImportFrom)) for n in tree.body))
        calls=[n for n in ast.walk(tree) if isinstance(n,ast.Call)]
        forbidden={'sample','build','run','fit','Store','Popen','system','exec','eval'}
        self.assertFalse(any((n.func.id if isinstance(n.func,ast.Name) else n.func.attr if isinstance(n.func,ast.Attribute) else '') in forbidden for n in calls))
        compile(tree,'UNIT_PAYLOAD_AST_ONLY','exec')

if __name__=='__main__':unittest.main()
