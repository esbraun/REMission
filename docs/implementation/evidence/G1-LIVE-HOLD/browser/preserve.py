from pathlib import Path
import hashlib,json,re,shutil

root=Path(__file__).parent
source=Path('C:/Users/erics/Documents/Projects/REMission/artifacts/playwright-mcp')
destination=root/'official-artifacts'
destination.mkdir(exist_ok=True)
entries=[]
for name in ['mcp-raw.json','mcp-raw-part2.json']:
    entries.extend(json.loads((root/name).read_bytes()))
references=set()
def content_blocks(value):
    if isinstance(value,list):
        for item in value:yield from content_blocks(item)
    elif isinstance(value,dict):
        if value.get('type')=='text':yield value['text']
        else:
            for item in value.values():yield from content_blocks(item)
for entry in entries:
    for content in content_blocks(entry['result']):
        references.update(re.findall(r'artifacts[\\/]playwright-mcp[\\/]([^\s)]+\.(?:png|yml))',content))
for name in sorted(references):
    if Path(name).name!=name:raise ValueError(name)
    shutil.copyfile(source/name,destination/name)
manifest={}
for path in sorted(root.rglob('*')):
    if path.is_file() and path.name!='manifest.json':
        raw=path.read_bytes();manifest[path.relative_to(root).as_posix()]=dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
(root/'manifest.json').write_text(json.dumps(dict(source_commit='1096d6da86048e7a53f98ed70abdd85f6f497aed',service_image='sha256:a5da282a1b4fe618fb07650f18a9533b86911cde2da928106c6da3211f1e6c8a',mcp_package_version=None,entries=len(entries),official_artifacts=len(references),files=manifest),indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(entries=len(entries),official_artifacts=len(references),files=len(manifest))))
