"""Exact returned files only; root-authorized MCP output-root exception."""
import hashlib,json,shutil
from pathlib import Path

source=Path('C:/Users/erics/Documents/Projects/REMission/artifacts/playwright-mcp')
out=Path('artifacts/p2/browser-final-75fc');out.mkdir(parents=True,exist_ok=False)
names=['page-2026-10-22T14-50-34-621Z.yml','page-2026-10-22T14-52-44-937Z.yml','page-2026-10-22T14-52-46-034Z.yml',
 'page-2026-10-22T14-53-55-236Z.yml','page-2026-10-22T14-53-56-357Z.yml','page-2026-10-22T15-03-23-519Z.yml',
 'page-2026-10-22T15-07-30-236Z.yml','console-2026-10-22T14-50-34-494Z.log','console-2026-10-22T15-07-30-143Z.log',
 'p2-sol-9b73-02-before-authorization.yml','p2-sol-9b73-03-start-desktop.png','p2-sol-9b73-03-start.yml',
 'p2-sol-9b73-04-washout-desktop.png','p2-sol-9b73-05-washout-narrow.png','p2-sol-9b73-05-washout.yml',
 'p2-sol-9b73-06-complete-timeline.png','p2-sol-9b73-06-complete.yml','p2-sol-9b73-07-history-reload.yml',
 'p2-sol-75fc-01-start.yml','p2-sol-75fc-01-start-desktop.png','p2-sol-75fc-02-washout-narrow.png','p2-sol-75fc-02-washout.yml',
 'p2-sol-75fc-03-complete-desktop.png','p2-sol-75fc-03-complete.yml','p2-sol-75fc-04-history-later.yml',
 'p2-sol-75fc-05-hold-stale.yml','p2-sol-75fc-05-hold-narrow.png','p2-sol-75fc-console-errors.txt','p2-sol-75fc-network.txt']
rows=[]
for name in names:
    a=source/name;b=out/name
    shutil.copyfile(a,b);raw=a.read_bytes();assert raw==b.read_bytes()
    rows.append(dict(original_path=str(a),own_copy=str(b),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
(out/'original-copy-bindings.json').write_text(json.dumps(rows,indent=2)+'\n')
shutil.copyfile(__file__,out/'helper.py')
print(json.dumps(dict(exact_returned_files_copied=len(rows),no_unrelated_enumeration=True,originals_preserved=True)))
