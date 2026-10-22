"""Capped metadata-only operation trace; diagnostic linker, unchanged optimizer."""
import hashlib
import json
from pathlib import Path
import time


def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)


def optimizer_identity(query):
    if isinstance(query,str):return dict(type='str',value=query)
    if query.subquery or query.extra_rewrites:raise ValueError('unfrozen optimizer subquery/extra rewrites')
    return dict(type=type(query).__name__,name=query.name,include=sorted(query.include),exclude=sorted(query.exclude),
        require=sorted(query.require),subquery={},position_cutoff=str(query.position_cutoff),extra_rewrites=[])


def metadata(value):
    # Read properties only. Never np.asarray/copy/reduce/index tensor values.
    result=dict(type=type(value).__name__)
    shape=getattr(value,'shape',None)
    if shape is not None:result['shape']=[int(v) for v in shape]
    dtype=getattr(value,'dtype',None)
    if dtype is not None:result['dtype']=str(dtype)
    nbytes=getattr(value,'nbytes',None)
    if nbytes is not None:result['bytes']=int(nbytes)
    return result


def type_metadata(variable):
    kind=variable.type
    return dict(type=type(kind).__module__+'.'+type(kind).__qualname__,dtype=getattr(kind,'dtype',None),
        shape=[int(v) if v is not None else None for v in kind.shape] if hasattr(kind,'shape') else None)


class MetadataTrace:
    def __init__(self,output,policy):
        from pytensor.compile.mode import get_default_mode
        from pytensor.compile.debug.monitormode import MonitorMode
        self.output=output;self.policy=policy;self.events=0;self.bytes=0;self.truncated=False
        self.callback_seconds=0.;self.point=None;self.started=time.monotonic();self.inventory_complete=False;self.finished=False
        default=get_default_mode();self.default_optimizer=optimizer_identity(default.provided_optimizer)
        digest=hashlib.sha256(canonical(self.default_optimizer).encode()).hexdigest()
        if digest!=policy['default_optimizer_sha256'] or type(default.linker).__name__!=policy['default_linker']:
            raise ValueError('default optimizer/linker differs from frozen diagnosis')
        # Pass the SAME query object, with no excluding/including calls. PyMC's
        # ordinary compile wrapper still applies its ordinary parameter rewrites.
        self.mode=MonitorMode(pre_func=self.pre,post_func=self.post,optimizer=default.provided_optimizer)
        self.status()

    def status(self):
        value=dict(events=self.events,bytes=self.bytes,event_cap=self.policy['trace_event_cap'],byte_cap=self.policy['trace_byte_cap'],
            truncated=self.truncated,inventory_complete=self.inventory_complete,finished=self.finished,callback_body_seconds=self.callback_seconds,
            default_optimizer=self.default_optimizer,default_optimizer_sha256=self.policy['default_optimizer_sha256'],
            ordinary_linker=self.policy['default_linker'],diagnostic_linker='MonitorMode WrapLinkerMany(OpWiseCLinker)',
            localization_allowed=not self.truncated and self.inventory_complete,
            limitation='Callback body time includes metadata/file writes; dispatch overhead is additional. Diagnostic-linker timings do not establish ordinary-linker production timeliness.')
        temporary=self.output/'trace-status.partial';temporary.write_text(canonical(value)+'\n');temporary.replace(self.output/'trace-status.json')
        return value

    def record(self,kind,index,node,thunk):
        started=time.perf_counter()
        if not self.truncated:
            memory={}
            for name in ('memory.current','memory.peak'):
                path=Path('/sys/fs/cgroup')/name
                if path.exists():memory[name]=int(path.read_text())
            value=dict(kind=kind,index=index,point=self.point,elapsed_seconds=time.monotonic()-self.started,
                operation=type(node.op).__module__+'.'+type(node.op).__qualname__,memory=memory,
                prior_callback_body_seconds=self.callback_seconds,
                inputs=[metadata(storage[0]) for storage in thunk.inputs])
            if kind=='after':value['outputs']=[metadata(storage[0]) for storage in thunk.outputs]
            encoded=(canonical(value)+'\n').encode()
            if self.events>=self.policy['trace_event_cap'] or self.bytes+len(encoded)>self.policy['trace_byte_cap']:
                self.truncated=True;self.status()
            else:
                with (self.output/'operation-trace.jsonl').open('ab') as stream:stream.write(encoded);stream.flush()
                self.bytes+=len(encoded);self.events+=1
        self.callback_seconds+=time.perf_counter()-started

    def pre(self,graph,index,node,thunk):self.record('before',index,node,thunk)
    def post(self,graph,index,node,thunk):self.record('after',index,node,thunk)

    def inventory(self,function):
        graph=function.f.maker.fgraph
        nodes=graph.toposort()
        if len(nodes)>self.policy['inventory_node_cap']:raise ValueError('inventory node cap; no evaluation')
        result=dict(nodes=[dict(index=i,operation=type(node.op).__module__+'.'+type(node.op).__qualname__,
            input_types=[type_metadata(v) for v in node.inputs],
            output_types=[type_metadata(v) for v in node.outputs]) for i,node in enumerate(nodes)],
            compiled_optimizer=optimizer_identity(function.f.maker.mode.provided_optimizer))
        encoded=(canonical(result)+'\n').encode()
        if len(encoded)>self.policy['inventory_byte_cap']:raise ValueError('inventory byte cap; no evaluation')
        (self.output/'optimized-inventory.json').write_bytes(encoded)
        self.inventory_complete=True;self.status()
