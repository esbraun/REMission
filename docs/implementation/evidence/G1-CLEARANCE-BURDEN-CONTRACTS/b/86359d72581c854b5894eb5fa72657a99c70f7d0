"""Finite planning illustration ONLY. Not proposed wire schema or application test.
This deliberately small algebra models immutable byte envelopes, chain identity,
active/closed continuity and strict time. It cannot qualify a service/producer.
"""
import base64, copy, hashlib, json
from pathlib import Path

def enc(x): return json.dumps(x,sort_keys=True,separators=(',',':')).encode('utf-8')
def h(x): return hashlib.sha256(x).hexdigest()
raw=[]
def add(version, time, op, **body):
    f=dict(schema=version,sequence=len(raw)+1,previous=h(raw[-1]) if raw else None,time=time,op=op,**body)
    raw.append(enc(f))
add('1.0.0',1,'baseline')
add('1.0.0',2,'open',episode='E1',generation=1)
add('1.0.0',3,'open',episode='E2',generation=1)
# Prior concern review deliberately represented separately from clearance.
add('1.0.0',4,'review',episode='E2',generation=1)
add('1.0.0',5,'clear',episode='E2',generation=1)
add('1.0.0',10,'open',episode='E3',generation=1)
old=tuple(raw);old_export=enc([json.loads(b) for b in old])
add('2.0.0',10,'cutover',prior_count=6,prior_head=h(old[-1]),closed={'E2':1},adopted=['E1'])
add('2.0.0',11,'open',episode='E2',generation=2)

def envelopes(bs):
    return [dict(schema=json.loads(b)['schema'],bytes=len(b),sha256=h(b),payload=base64.b64encode(b).decode()) for b in bs]

def verify(es, expected_count, expected_head):
    assert len(es)==expected_count,'trusted count'
    decoded=[]
    for e in es:
        b=base64.b64decode(e['payload'],validate=True)
        assert base64.b64encode(b).decode()==e['payload'],'base64'
        assert len(b)==e['bytes'] and h(b)==e['sha256'],'envelope'
        f=json.loads(b)
        assert enc(f)==b and f['schema']==e['schema'],'dispatch'
        assert f['sequence']==len(decoded)+1,'sequence'
        assert f['previous']==(h(decoded[-1]) if decoded else None),'predecessor'
        decoded.append(b)
    assert (h(decoded[-1]) if decoded else h(b''))==expected_head,'trusted head'
    return decoded

def fold(bs):
    active={};closed={};v2=False;reviews=set();policy={}
    for n,b in enumerate(bs,1):
        f=json.loads(b);op=f['op'];v=f['schema']
        assert not(v2 and v=='1.0.0'),'downgrade'
        if v=='2.0.0' and not v2:
            assert op=='cutover','missing cutover'
            assert f['prior_count']==n-1 and f['prior_head']==h(bs[n-2]),'cutover predecessor'
            assert f['closed']==closed,'closed state'
            assert set(f['adopted'])<=set(active),'adoption target'
            v2=True;reviews.clear();policy={e:('bound' if e in f['adopted'] else 'unsupported') for e in active}
            continue
        if op=='baseline': assert n==1,'baseline'
        elif op=='open':
            e=f['episode'];g=f['generation']
            assert e not in active and g==closed.get(e,0)+1,'recurrence'
            active[e]=g
        elif op=='review':
            assert active[f['episode']]==f['generation'],'review target'
            reviews.add((f['episode'],f['generation']))
        elif op=='clear':
            e=f['episode'];g=f['generation']
            assert active[e]==g and (e,g) in reviews,'clear review'
            closed[e]=g;del active[e]
        else: raise AssertionError('operation')
    return active,closed,policy

results=[]
def passed(name): results.append({'case':name,'result':'pass'})
full=envelopes(raw)
assert verify(full,len(raw),h(raw[-1]))==raw
assert tuple(base64.b64decode(x['payload']) for x in full[:6])==old
assert enc([json.loads(b) for b in old])==old_export
passed('original bytes and old export preserved')
assert fold(raw[:7])==({'E1':1,'E3':1},{'E2':1},{'E1':'bound','E3':'unsupported'})
passed('held/adopted/unadopted and closed map survive cutover')
assert fold(raw)[0]['E2']==2 and fold(raw)[1]['E2']==1
passed('closed generation then recurrence g2')
for k,count in [(9,5),(10,5),(10.5,7),(11,7),(12,8)]:
    selected=[b for b in raw if json.loads(b)['time']<k]
    assert len(selected)==count
    verify(envelopes(selected),count,h(selected[-1]))
passed('strict before/equal/after cutover and equal-time group')

def refuses(name,fn,reason):
    try:fn()
    except AssertionError as e:
        assert str(e)==reason,(name,str(e),reason)
        results.append({'case':name,'result':'expected refusal','stage':reason})
    else:raise AssertionError('accepted negative '+name)
refuses('suffix alone',lambda:verify(full[6:],len(raw),h(raw[-1])),'trusted count')
refuses('self-consistent truncated prefix',lambda:verify(full[:6],len(raw),h(raw[-1])),'trusted count')
rewritten=copy.deepcopy(full)
f=json.loads(old[1]);f['policy']=None
rewritten[1]=envelopes([enc(f)])[0]
refuses('rewritten old payload with rehashed envelope',lambda:verify(rewritten,len(raw),h(raw[-1])),'predecessor')
# Fold-specific faults use a locally rebuilt chain; byte auth is controlled separately.
def rechain(bs):
    out=[]
    for n,b in enumerate(bs,1):
        f=json.loads(b);f['sequence']=n;f['previous']=h(out[-1]) if out else None;out.append(enc(f))
    return out
bad=list(raw);f=json.loads(bad[6]);f['closed']={};bad[6]=enc(f);bad=rechain(bad)
verify(envelopes(bad),len(bad),h(bad[-1])) # explicit positive outer-binding control
refuses('forged closed-state transition reaches fold',lambda:fold(bad),'closed state')
bad=list(raw);f=json.loads(bad[7]);f['generation']=1;bad[7]=enc(f);bad=rechain(bad)
verify(envelopes(bad),len(bad),h(bad[-1]))
refuses('reset recurrence reaches fold',lambda:fold(bad),'recurrence')
assert fold(verify(full,len(raw),h(raw[-1])))[0]['E2']==2
passed('restored original positive control after faults')
output={'scope':'finite abstract planning algebra only; no application imports/runtime acceptance','cases':results,'not_exercised':['real 1.0 database upgrade','complete proposed schemas/rosters','tasks/HTTP/auth/committed closure','producer qualification','browser/process/crash behavior','clinical gates']}
Path(__file__).with_name('probe-results.json').write_text(json.dumps(output,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'finite_cases':len(results),'scope':output['scope']}))
