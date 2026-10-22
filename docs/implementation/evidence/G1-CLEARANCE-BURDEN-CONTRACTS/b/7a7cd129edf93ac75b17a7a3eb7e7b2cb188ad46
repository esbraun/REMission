"""Preserve the author log's raw recursive-warning bytes before envelope repair."""
import base64,json,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[4]
path=HERE/'whitespace-check.txt';destination=HERE/'whitespace-log-recovery.json'
if destination.exists():
    assert not path.exists()
else:
    items=[]
    rel=path.relative_to(ROOT).as_posix()
    for label,raw in [('working',path.read_bytes()),('WIP',subprocess.check_output(['git','show','796b726716557727d57fb5f2d19b37d3fc0ade98:'+rel],cwd=ROOT))]:
        blob=subprocess.check_output(['git','hash-object','-w','--stdin'],input=raw,cwd=ROOT).decode().strip()
        assert subprocess.check_output(['git','cat-file','blob',blob],cwd=ROOT)==raw
        items.append({'label':label,'raw_git_blob':blob,'bytes':len(raw),'base64':base64.b64encode(raw).decode()})
    destination.write_text(json.dumps({'encoding':'base64 of exact failed raw-log bytes','items':items},indent=2)+'\n',encoding='utf-8',newline='\n')
    assert path.resolve().parent==HERE.resolve()
    path.unlink()
