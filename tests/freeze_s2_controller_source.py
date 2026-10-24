"""Freeze public SOURCE artifacts only, called inside the active source guards."""
import ast
import hashlib
import json
from contracts.domain.analysis import reference
from contracts.domain.support_s2_controller import (CONFIGURATION,CONFIG_REF,ControllerCommand,SavedScalar,
    QualificationPacket,InteractiveSupportQualification,UntrustedInteractiveInvocation,AuthorizationBasis,InteractiveStageCompletion)


SOURCE_PATHS=['contracts/domain/support_s2_controller.py',*['services/foundation/'+name+'.py' for name in
    ('app','store','workflow','protocol','simulation','support_s2_controller','support_s2_authority','support_s2_invocation','support_s2_prediction')],
    'tests/run_s2_controller_source.py','tests/test_s2_controller_source.py','tests/freeze_s2_controller_source.py',
    *['web/src/'+name for name in ('main.tsx','types.ts','SimulationPanel.tsx','SupportPanel.tsx')]]


def freeze(root,result):
    output=root/'artifacts/s2-controller/source'
    def save(name,value):
        (output/name).write_text(json.dumps(value,sort_keys=True,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    schema={model.__name__:model.model_json_schema() for model in (ControllerCommand,SavedScalar,QualificationPacket,
        InteractiveSupportQualification,UntrustedInteractiveInvocation,AuthorizationBasis,InteractiveStageCompletion)}
    save('controller-schema.json',dict(scope='SOURCE_ONLY',schemas=schema,reference=reference('poc-s2-controller-schema-v1',schema)))
    save('controller-config.json',dict(configuration=CONFIGURATION,reference=CONFIG_REF))
    closure=[]
    for path in SOURCE_PATHS:
        raw=root.joinpath(path).read_bytes();canonical=raw.replace(b'\r\n',b'\n')
        closure.append(dict(path=path,checkout_bytes=len(raw),checkout_sha256=hashlib.sha256(raw).hexdigest(),
            git_bytes=len(canonical),git_sha256=hashlib.sha256(canonical).hexdigest(),
            git_blob=hashlib.sha1(b'blob '+str(len(canonical)).encode()+b'\0'+canonical).hexdigest()))
    save('source-closure.json',dict(scope='public Git SOURCE; no installed-image byte qualification',files=closure))
    save('checks.json',dict(scope='guarded SOURCE AST/contracts/inert I/O only',tests=result.testsRun,
        failures=len(result.failures),errors=len(result.errors),skipped=len(result.skipped),
        actual_app=False,actual_SQLite=False,actual_science=False,actual_browser=False,runtime_GO=False,
        retained_numerics=dict(passed=17,failed=1,rerun=False,sealed_operation=False)))
    # Reproducible AST inventory supplements the exact Git reverse-patch proof.
    def functions(tree,prefix=''):
        found={}
        for node in getattr(tree,'body',[]):
            if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)):
                name=prefix+node.name
                if not isinstance(node,ast.ClassDef):found[name]=ast.dump(node,include_attributes=False)
                found.update(functions(node,name+'.'))
        return found
    inventory=[]
    for name in ('app','store','workflow','protocol','simulation','support_s2_prediction'):
        base=functions(ast.parse(output.joinpath('base-'+name+'.py').read_text()))
        candidate=functions(ast.parse(root.joinpath('services/foundation/'+name+'.py').read_text()))
        inventory.append(dict(path='services/foundation/'+name+'.py',
            unchanged=[key for key in base if base[key]==candidate.get(key)],
            changed=[key for key in base if base[key]!=candidate.get(key)],added=sorted(candidate.keys()-base.keys())))
    save('function-inverses.json',dict(scope='AST identity and declared changed functions; see focused inverse controls and Git reverse-patch proof',files=inventory))
