"""Read/copy only an exact official-MCP-returned file under the scoped exception."""
import hashlib,json,shutil,sys
from pathlib import Path
original=Path(sys.argv[1]).resolve()
allowed=Path('C:/Users/erics/Documents/Projects/REMission/artifacts/playwright-mcp').resolve()
assert original.is_relative_to(allowed) and original.is_file()
root=Path('artifacts/cohort/browser-r1');root.mkdir(exist_ok=True)
destination=root/original.name
assert not destination.exists()
shutil.copyfile(original,destination)
raw=original.read_bytes();copy=destination.read_bytes();assert raw==copy
index=root/'artifact-bindings.json'
records=json.loads(index.read_text()) if index.exists() else []
records.append(dict(original=str(original),copy=str(destination.resolve()),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),copy_sha256=hashlib.sha256(copy).hexdigest()))
index.write_text(json.dumps(records,indent=2)+'\n')
print(json.dumps(records[-1]))
