"""Author verification only: no production generation, enrollment, fit or server."""
import hashlib,json,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4]
OUT=Path(__file__).resolve().parent
SOURCE="b17bf991b910c2c28da6979aab5a04650a4baa66"
RUNTIME="sha256:ce346feace2ae607ebd574e1bb681d594c9b676c06b56f8ba8d50b858a577faa"
results=[]
def run(name,args):
    print("START "+name,flush=True);start=time.monotonic()
    result=subprocess.run(args,cwd=ROOT,capture_output=True)
    (OUT/(name+".stdout")).write_bytes(result.stdout)
    (OUT/(name+".stderr")).write_bytes(result.stderr)
    value=dict(name=name,command=args,exit_code=result.returncode,seconds=time.monotonic()-start,
        stdout_sha256=hashlib.sha256(result.stdout).hexdigest(),stderr_sha256=hashlib.sha256(result.stderr).hexdigest())
    results.append(value);(OUT/"checks.json").write_text(json.dumps(dict(source=SOURCE,runtime=RUNTIME,checks=results),indent=2)+"\n")
    print("DONE "+name+" exit="+str(result.returncode),flush=True)
    return result
assert subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()==SOURCE
base=["docker","run","--rm","--network","none","--mount","type=bind,source="+str(ROOT)+",target=/app,readonly",
    "-e","RESEARCH_TEST_IMAGE="+RUNTIME,"-e","RESEARCH_TEST_SOURCE="+SOURCE,RUNTIME,"python"]
for name,folder,pattern in [
    ("research-16","tests/run_contracts","test_research_producer.py"),
    ("canonical-v1-12","tests/run_contracts","test_interfaces.py"),
    ("canonical-v2-20","tests/run_contracts","test_*v2*.py"),
    ("cohort-store","tests/integration/replay","test_cohort_service.py"),
    ("foundation-replay","tests/integration/replay","test_foundation.py"),
    ("restricted-law","tests/generator","test_restricted.py")]:
    run(name,base+["-m","unittest","discover","-s",folder,"-p",pattern,"-v"])
for module in ("contracts.runs.export","contracts.runs.export_v2"):
    run(module.replace(".","-"),base+["-m",module,"--check"])
for role in ("generator","service","learner"):
    run("build-"+role,["docker","build","--network","none","-f","tooling/foundation/"+role+".Dockerfile","-t","remission-research-prod-sol-"+role+":20261022","."])
    inspected=run("image-"+role,["docker","image","inspect","remission-research-prod-sol-"+role+":20261022"])
    if inspected.returncode:continue
    image=json.loads(inspected.stdout)[0]["Id"]
    module={"generator":"services.generator.research","service":"services.foundation.research_enrollment","learner":"services.learner.worker"}[role]
    code="""import hashlib,importlib,json,os,platform,sys
from pathlib import Path
import numpy
role=sys.argv[1];importlib.import_module(sys.argv[2]);denied={}
if role!='generator':
 for name in ('services.generator.research','contracts.runs.private','contracts.dgp.parameters','services.evaluator'):
  try:importlib.import_module(name);denied[name]=False
  except ModuleNotFoundError:denied[name]=True
 assert all(denied.values()),denied
files={str(p.relative_to('/app')):hashlib.sha256(p.read_bytes()).hexdigest() for base in ('/app/contracts','/app/services','/app/methods') for p in Path(base).rglob('*') if p.is_file() and p.suffix in ('.py','.json')}
print(json.dumps(dict(role=role,uid=os.getuid(),python=platform.python_version(),numpy=numpy.__version__,denied=denied,files=files),sort_keys=True))
"""
    run("inventory-"+role,["docker","run","--rm","--network","none","--read-only","--cap-drop","ALL","--security-opt","no-new-privileges",image,"python","-c",code,role,module])
print("FINAL "+str(len(results))+" commands, "+str(sum(r['exit_code']!=0 for r in results))+" failures",flush=True)
