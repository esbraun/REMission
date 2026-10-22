"""Metadata tracing must not touch tensor values or publish incomplete lines."""
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tooling/foundation'))
from pa3_monitor import MetadataTrace,metadata


class ValuesForbidden:
    shape=(2,3)
    dtype='float64'
    nbytes=48
    def __array__(self,*args,**kwargs):raise AssertionError('no tensor conversion')
    def __iter__(self):raise AssertionError('no tensor iteration')
    def __getitem__(self,key):raise AssertionError('no tensor indexing')


class MonitorControlTests(unittest.TestCase):
    def make_trace(self,root,byte_cap,event_cap):
        import time
        trace=MetadataTrace.__new__(MetadataTrace)
        trace.output=root;trace.policy=dict(trace_byte_cap=byte_cap,trace_event_cap=event_cap,default_optimizer_sha256='test',default_linker='NumbaLinker')
        trace.events=0;trace.bytes=0;trace.truncated=False;trace.callback_seconds=0.;trace.point=0;trace.started=time.monotonic()
        trace.inventory_complete=True;trace.finished=False;trace.default_optimizer={}
        return trace

    def test_properties_only_no_tensor_values(self):
        self.assertEqual(metadata(ValuesForbidden()),dict(type='ValuesForbidden',shape=[2,3],dtype='float64',bytes=48))

    def test_event_cap_keeps_complete_lines_and_disables_localization(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);trace=self.make_trace(root,4096,1)
            node=SimpleNamespace(op=object());thunk=SimpleNamespace(inputs=[[ValuesForbidden()]],outputs=[[ValuesForbidden()]])
            trace.pre(None,0,node,thunk);trace.post(None,0,node,thunk)
            lines=(root/'operation-trace.jsonl').read_bytes().splitlines()
            self.assertEqual(len(lines),1);self.assertEqual(json.loads(lines[0])['kind'],'before')
            state=json.loads((root/'trace-status.json').read_bytes())
            self.assertTrue(state['truncated']);self.assertFalse(state['localization_allowed']);self.assertFalse(state['finished'])
            self.assertLessEqual((root/'operation-trace.jsonl').stat().st_size,4096)

    def test_byte_cap_cannot_leave_partial_json(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);trace=self.make_trace(root,8,10)
            trace.pre(None,0,SimpleNamespace(op=object()),SimpleNamespace(inputs=[],outputs=[]))
            self.assertFalse((root/'operation-trace.jsonl').exists())
            self.assertTrue(json.loads((root/'trace-status.json').read_bytes())['truncated'])


if __name__=='__main__':unittest.main()
