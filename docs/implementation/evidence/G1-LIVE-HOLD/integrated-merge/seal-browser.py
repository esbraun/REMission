"""Seal only this worker's current-turn official MCP events and returned files."""
import hashlib,json,re
from pathlib import Path
OUT=Path(__file__).parent/'browser';OUT.mkdir(parents=True,exist_ok=True)
LOG=Path('C:/Users/erics/.codex/sessions/2026/10/21/rollout-2026-10-21T15-36-15-01a1609b-a634-7c53-be7c-15edc1685bf6.jsonl')
TURN='01a16154-1612-76c3-863d-ec2b17bbd321'
rows=[];raw_lines=[];failures=[]
for line in LOG.read_bytes().splitlines(keepends=True):
    x=json.loads(line);p=x.get('payload',{});i=p.get('item',{})
    if p.get('turn_id')!=TURN or p.get('type')!='item_completed':continue
    if i.get('type')=='McpToolCall' and i.get('server')=='playwright':
        raw_lines.append(line);rows.append(dict(timestamp=x['timestamp'],**i))
    if i.get('type')=='CommandExecution' and i.get('cwd','').endswith('g1lh-iv-261021') and (i.get('exit_code') or any(s in str(i.get('aggregated_output','')) for s in ['Traceback','fatal:','IO error'])):
        failures.append(x)
    if i.get('type')=='McpToolCall' and i.get('server')=='codex_app' and i.get('tool')=='read_thread' and i.get('status')=='failed':
        failures.append(x)
assert len(rows)>50
(OUT/'mcp-events-exact.jsonl').write_bytes(b''.join(raw_lines))
(OUT/'mcp-raw-complete.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(OUT/'read-command-negative-events.json').write_text(json.dumps(failures,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
primary=Path('C:/Users/erics/Documents/Projects/REMission');mapping={}
for row in rows:
    for content in row.get('result',{}).get('content',[]):
        for name in re.findall(r'artifacts[\\/][A-Za-z0-9_.\\/-]+\.(?:png|yml|log)',content.get('text','')):
            rel=re.sub(r'[\\/]+','/',name);p=(primary/rel).resolve();assert p.is_relative_to(primary/'artifacts')
            if str(p) in mapping:continue
            raw=p.read_bytes();target=OUT/'generated'/p.name;target.parent.mkdir(exist_ok=True)
            if target.exists():assert target.read_bytes()==raw
            target.write_bytes(raw);mapping[str(p)]=dict(tool_returned_path=rel,path=target.relative_to(OUT).as_posix(),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
value=dict(scope='Only tool-returned own official MCP artifacts; original current-turn event lines copied verbatim; in-memory append accumulator did not persist and was recovered from exact own event records without fabricating results',records=len(rows),generated=list(mapping.values()),screenshots=sum(v['path'].endswith('.png') for v in mapping.values()),raw_sha256=hashlib.sha256((OUT/'mcp-raw-complete.json').read_bytes()).hexdigest(),raw_event_sha256=hashlib.sha256(b''.join(raw_lines)).hexdigest())
(OUT/'artifact-manifest.json').write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:v for k,v in value.items() if k!='generated'}))
