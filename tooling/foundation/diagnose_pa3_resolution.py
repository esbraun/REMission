"""Read-only deterministic diagnosis of frozen failed Q16 prefit points."""
import argparse
import json
from pathlib import Path
from capture import run


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--deployment',type=Path,required=True)
    parser.add_argument('--evidence',type=Path,required=True);args=parser.parse_args()
    deployment=json.loads(args.deployment.read_text())
    code="""import json
from pathlib import Path
from methods.visit.borrowing import marginal
points=json.loads(Path('/frozen/prefit/points.json').read_text())
manifest=json.loads(Path('/frozen/prefit/frozen-manifest.json').read_text())
result=[]
for point in points:
    if point['accepted']:continue
    last=point['looks'][-1]
    values={str(q):marginal(point['theta'],q) for q in (16,32,64,128)}
    bounds={q:abs(g-last['mean'])+manifest['z']*last['paired_se'] for q,g in values.items()}
    result.append(dict(index=point['index'],values=values,reference_mean=last['mean'],reference_se=last['paired_se'],upper_error_bounds=bounds,epsilon=min(manifest['epsilon_per_study'])))
print(json.dumps(result))
"""
    result,metadata=run(['docker','run','--name',deployment['prefix']+'-resolution-diagnosis',
        '--network','none','--cpus','2','--memory','2g','--read-only','--cap-drop','ALL',
        '--security-opt','no-new-privileges','--tmpfs','/tmp:rw,nosuid,size=256m',
        '--mount','type=volume,src='+deployment['volumes']['bridge-output']+',dst=/frozen,readonly',
        '--entrypoint','python',deployment['images']['bridge'],'-c',code],args.evidence/'commands')
    if result.returncode:raise RuntimeError(metadata)
    values=json.loads(result.stdout)
    (args.evidence/'resolution-diagnosis.json').write_text(json.dumps(values,indent=2)+'\n')
    print(json.dumps(values,indent=2))


if __name__=='__main__':main()
