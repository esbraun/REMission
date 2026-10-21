"""Source preservation and bounded independent finite checks; no project imports.

This is author arithmetic evidence, not a generator, evaluator, filter, calibration
or stochastic pilot. Production must use qualified numerical libraries.
"""
import base64
from fractions import Fraction as F
import hashlib
import itertools
import json
import math
from pathlib import Path
import statistics
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
BASE = 'ec18cb4020ba239710a3fd615e365d5cd72b4d80'
ORIGINAL = '01ffab3a3f55cf4c228648ab28a934aed9f30ec6'
PACKAGE = 'docs/implementation/evidence/G1-CLEARANCE-BURDEN-PLAN-20261021/'

def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)

def write(name, value):
    (HERE/name).write_text(json.dumps(value, indent=2, ensure_ascii=True)+'\n', encoding='utf-8', newline='\n')

assert git('rev-parse','--show-toplevel').decode().strip().replace('\\','/') == str(ROOT).replace('\\','/')
assert git('merge-base','HEAD',BASE).decode().strip() == BASE

original_manifest = json.loads(git('show',ORIGINAL+':'+PACKAGE+'artifact-manifest.json'))
source_inventory = json.loads(git('show',ORIGINAL+':'+PACKAGE+'source-identities.json'))
preserve = []
seen = set()
def preserve_blob(blob, label, tree_blob=None):
    if blob in seen:
        return
    seen.add(blob)
    raw = git('cat-file','blob',blob)
    assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest() == blob
    written = subprocess.check_output(['git','hash-object','-w','--stdin'], input=raw, cwd=ROOT).decode().strip()
    assert written == blob and git('cat-file','blob',written) == raw
    preserve.append({'label':label,'git_blob':blob,'tree_blob':tree_blob,'bytes':len(raw),
                     'sha256':hashlib.sha256(raw).hexdigest(),
                     'base64':base64.b64encode(raw).decode()})

for item in original_manifest['artifacts']:
    tree_blob=git('rev-parse',ORIGINAL+':'+item['path']).decode().strip()
    preserve_blob(item['raw_git_blob'],item['path']+' declared raw',tree_blob)
    if tree_blob != item['raw_git_blob']:
        preserve_blob(tree_blob,item['path']+' committed tree')
for label,blob in {
    'original artifact manifest':'092b1d2d9f758b50b834a939a9513440980e045c',
    'complete rejection':'aea263401b22357bf254716fe6581811ad902123',
    'review source checks':'293906eefc01ef6028b7295ab9324eade36eb55b',
    'review artifact manifest':'216d5cdf0cf5d5531a1ec23122af3361fa014389',
    'review probe source':'695c95447f01182b92a8d8aeb8fbf540fadf760c',
    'review failures/truncations':'b3d0f0fb96b5cf9c4ca6c1ea1fd911542915e746',
    'review raw whitespace warnings':'3bdb434111517a3b046a59c6ffad588dd603575a',
    'review finalization source':'43ac263f5922711d3044063580720b6fb6d02a8f',
    'accepted LIVE-HOLD-R1 plan':'e6d39d6a0bce37a554cd768e14ee0916edf5da5c',
}.items():
    preserve_blob(blob,label)
write('preserved-inputs.json',{'encoding':'base64 of exact raw Git blob bytes; no newline normalization',
                               'original_head':ORIGINAL,'base':BASE,'items':preserve})

sources=[]
for item in source_inventory:
    raw=git('show',item['base']+':'+item['path'])
    blob=git('rev-parse',item['base']+':'+item['path']).decode().strip()
    assert blob==item['git_blob'] and hashlib.sha256(raw).hexdigest()==item['sha256']
    sources.append(item)
for path in ('contracts/domain/temporal.py','contracts/domain/common.py','contracts/domain/boundaries.py',
             'contracts/domain/export.py','contracts/runs/export.py','contracts/runs/bindings-v2.json',
             'contracts/domain/temporal-v2.json','docs/spec/08-gates-and-release.md','plan.md'):
    raw=git('show',BASE+':'+path)
    sources.append({'path':path,'base':BASE,'git_blob':git('rev-parse',BASE+':'+path).decode().strip(),
                    'git_bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})
write('source-identities.json',sources)

cells=json.loads(git('show',BASE+':contracts/dgp/scenarios-v1.json'))['cells']
assert len(cells)==82 and len({(c['family'],c['variant']) for c in cells})==73
assert len({c['family'] for c in cells})==32
bindings=[]
for c in cells:
    layer='analytic' if c['target'] in ('constant_fixture','randomized_tree','observational_tree') else ('system' if c['target'] in ('system','lineage') else 'longitudinal')
    bindings.append({'cell_id':c['id'],'patients':c['patients'],'original_overrides':c['overrides'],
                     'applicability':layer,'review_law':'SIM-REVIEW-01/1.0.0-r1',
                     'concern_script':'CONCERN-EMPTY-01','missing_concern_status':'unknown_through_horizon',
                     'regimen_ack':'REGIMEN-ACK-01','regimen_change_enabled':c['overrides'].get('regimen_change_enabled',0),
                     'burden_law':'SIM-BURDEN-01/1.0.0-r1','report_status_law':'REPORT-STATUS-01/1.0.0-r1',
                     'supplemental_fixtures_are_not_production_overrides':True})
write('cell-law-bindings.json',{'catalog_binding':'1.1.0','dgp':'1.3.0','ordered_cells':bindings})

script_entries=[]
specs=[('CLR-MIXED-01','fixture_concern',7,'fever-1','fever',[(8,'unknown'),(9,'satisfied')]),
       ('CLR-CONCERN-01','fixture_concern',7,'concern-1','clinician_concern',[(8,'unknown'),(9,'satisfied')]),
       ('CLR-RECURRENCE-01','fixture_concern',7,'concern-1','clinician_concern',[(8,'satisfied')]),
       ('CLR-RECURRENCE-01','fixture_concern',9,'concern-2','clinician_concern',[(9,'unknown'),(10,'satisfied')]),
       ('CLR-CF-ABSENT-01','adverse',7,'bernoulli','adverse_symptom',[(8,'satisfied')])]
specs += [('CLR-ACUTE-01','fixture_concern',7,r+'-1',r,[(8,'satisfied')]) for r in ('fever','confusion','fall')]
for script,process,day,sub,reason,entries in specs:
    for date,status in entries:
        script_entries.append({'script_id':script,'patient_slot':'fixture-patient',
                               'occurrence_key':[process,day,sub],'assessment_local_day':date,
                               'reason':reason,'status':status})
write('review-scripts.json',{'empty_production_script':'CONCERN-EMPTY-01','unlisted_status':'unknown',
                            'regimen_rule':{'id':'REGIMEN-ACK-01','first_ack_local_date':'actual_change_date+1',
                                            'required':'exact current registered schedule and explicit supersession chain'},
                            'fixture_entries':script_entries})

def r_exact(n,q):
    if q==0:
        return None
    return sum(F(math.comb(n,m),m)*q**m*(1-q)**(n-m) for m in range(1,n+1))/(1-(1-q)**n)

# Exactly enumerate five equally likely microstates: three undefined, 0, 4.
rows=[]
for micro in itertools.product((None,None,None,0,4),repeat=3):
    defined=[v for v in micro if v is not None]
    m=len(defined)
    rows.append({'M':m,'category4':None if not m else F(sum(v==4 for v in defined),m),
                 'score':None if not m else F(sum(defined),m)})
assert len(rows)==125
positive=[r for r in rows if r['M']]
q=F(2,5); n=3; rr=r_exact(n,q)
exact={}
for name,v in [('category4',F(1,4)),('score',F(4))]:
    mean=sum(row[name] for row in positive)/len(positive)
    var=sum((row[name]-mean)**2 for row in positive)/len(positive)
    assert var==v*rr
    exact[name]={'mean':str(mean),'variance':str(var),'formula_variance':str(v*rr)}
assert F(len(rows)-len(positive),len(rows))==(1-q)**n
assert r_exact(3,F(1))==F(1,3)
assert r_exact(3,F(0)) is None
assert r_exact(1,F(1,1000))==1
assert r_exact(3,F(1,100))>r_exact(3,F(1,10))>r_exact(3,F(1,2))

def cp(c,n,alpha):
    """Bounded finite binomial inversion for this evidence, not production code."""
    def total(p,start,end):
        if p==0:
            return float(start<=0<=end)
        if p==1:
            return float(start<=n<=end)
        lp,lm=math.log(p),math.log1p(-p)
        return sum(math.exp(math.lgamma(n+1)-math.lgamma(k+1)-math.lgamma(n-k+1)+k*lp+(n-k)*lm)
                   for k in range(start,end+1))
    def solve(start,end,increasing):
        lo,hi=0.,1.
        for _ in range(70):
            mid=(lo+hi)/2
            greater=total(mid,start,end)>alpha/2
            if greater==increasing: hi=mid
            else: lo=mid
        return (lo+hi)/2
    return (0. if c==0 else solve(c,n,True),1. if c==n else solve(0,c,False))

def r_float(n,q):
    if q==1: return 1/n
    return sum(math.comb(n,m)*q**m*(1-q)**(n-m)/m for m in range(1,n+1))/(-math.expm1(n*math.log1p(-q)))

def ratio_sd_gradient(p,n,name):
    q=sum(p[1:]); theta=[x/q for x in p[1:]]
    r=r_float(n,q);rho=1-(1-q)**n
    rp=(sum(math.comb(n,m)*q**m*(1-q)**(n-m)*(m/q-(n-m)/(1-q))/m for m in range(1,n+1))-r*n*(1-q)**(n-1))/rho
    if name=='category4':
        v=theta[4]*(1-theta[4]); dv=[0,0,0,0,1-2*theta[4]]
    else:
        mu=sum(k*t for k,t in enumerate(theta));v=sum(k*k*t for k,t in enumerate(theta))-mu*mu
        dv=[k*k-2*mu*k for k in range(5)]
    s=math.sqrt(v*r)
    grad=[0.]
    for l in range(5):
        grad.append((v*rp+r*sum(dv[k]*((k==l)-theta[k])/q for k in range(5)))/(2*s))
    return s,grad

gradient_checks=[]
interior=[.2,.1,.2,.2,.2,.1]
for name in ('category4','score'):
    s,g=ratio_sd_gradient(interior,3,name)
    for idx in range(6):
        plus=interior.copy();minus=interior.copy();plus[idx]+=1e-6;minus[idx]-=1e-6
        numerical=(ratio_sd_gradient(plus,3,name)[0]-ratio_sd_gradient(minus,3,name)[0])/2e-6
        assert abs(numerical-g[idx])<1e-7
    gradient_checks.append({'component':name,'analytic_gradient':g,'central_difference_max_tolerance':1e-7,'passed':True})

# This is the entire deterministic table, including every undefined trial.
trials=rows*8;J=len(trials);Jplus=sum(t['M']>0 for t in trials);rho=Jplus/J
assert (J,Jplus,J-Jplus)==(1000,784,216)
empty_category_trials=sum(t['M']>0 and t['category4']==0 for t in trials)
assert empty_category_trials==296
T=J*3; Mtot=sum(t['M'] for t in trials)
qbox=cp(Mtot,T,.05/6);theta_box=cp(Mtot//2,Mtot,.05/6)
assert qbox[0]<.4<qbox[1] and theta_box[0]<.5<theta_box[1]
zero_sample_box=cp(0,3,.05/6)
assert zero_sample_box[0]==0 and zero_sample_box[1]>0
assert rr != 1/(n*q)
pilot_arithmetic={}
p=[.6,.2,0.,0.,0.,.2]
for name in ('category4','score'):
    ys=[float(t[name]) for t in trials if t['M']]
    mean=statistics.mean(ys);s=statistics.stdev(ys)
    h=[0. if not t['M'] else ((float(t[name])-mean)**2-s*s)/(2*s*rho) for t in trials]
    u=statistics.stdev(h)/math.sqrt(J); lemp=s-1.645*u
    if name=='category4':
        l,u0=theta_box;vlower=min(l*(1-l),u0*(1-u0))*r_float(3,qbox[1])
    else:
        vlower=16*theta_box[0]**2*r_float(3,qbox[1])
    san,grad=ratio_sd_gradient(p,3,name)
    va=(sum(p[k]*grad[k]**2 for k in range(6))-sum(p[k]*grad[k] for k in range(6))**2)/T
    ua=math.sqrt(max(0.,va))
    assert abs(s-san)<=1.96*(u+ua)
    binding=min(lemp,math.sqrt(vlower))
    assert binding>0
    pilot_arithmetic[name]={'conditional_mean':mean,'conditional_sample_SD':s,'empirical_SD_MCSE':u,
                            'empirical_lower':lemp,'analytic_SD':san,'analytic_SD_MCSE':ua,
                            'analytic_variance_lower':vlower,'positive_binding_arithmetic':binding,
                            'undefined_rows_retained':J-Jplus,
                            'claim':'finite table arithmetic only; not an independent stochastic pilot or accepted binding'}

availability=[(F(1,4),1,1),(F(1,4),2,3),(F(1,2),4,4)]
mass=sum(w for w,l,y in availability if l<=3)
conditioned=sum(w*y for w,l,y in availability if l<=3)/mass
unconditioned=sum(w*y for w,l,y in availability)
assert mass==F(1,2) and conditioned==2 and unconditioned==3
assert F(1,4)!=F(1,2) # pooled ratio 1/(1+3) vs average of 1/1 and 0/3
write('finite-checks.json',{'scope':'finite source/analytic checks, no production or stochastic engine',
                           'enumeration':{'microstates':125,'q':str(q),'r_3':str(rr),'undefined_probability':'27/125','moments':exact},
                           'deterministic_1000_row_table':{'J':J,'Jplus':Jplus,'undefined':216,'defined_but_category4_empty_trials':empty_category_trials,'q_CP_box':qbox,'theta_CP_box':theta_box,'components':pilot_arithmetic},
                           'sampled_zero_control':{'count':0,'n':3,'CP_interval':zero_sample_box,'status':'not_structural_zero'},
                           'inverse_denominator_fault':{'exact_r':str(rr),'wrong_inverse_mean':str(1/(n*q))},
                           'gradient_checks':gradient_checks,
                           'availability':{'normalizer':str(mass),'correct_mean':str(conditioned),'omitted_gate_mean':str(unconditioned),'structural_zero_rule':'no mass on eligible state => undefined; no sampled mass alone => unresolved'},
                           'batch_ratio_fault':{'correct':'1/4','fault_average_ratios':'1/2'},
                           'cell_count':82,'variant_count':73,'family_count':32,
                           'preserved_objects':len(preserve),'verified_sources':len(sources)})
print(json.dumps({'root':str(ROOT),'preserved_objects':len(preserve),'verified_sources':len(sources),
                  'r_3':str(rr),'undefined_rows':216,'positive_bindings':{k:v['positive_binding_arithmetic'] for k,v in pilot_arithmetic.items()},
                  'claim':'finite author arithmetic only; independent review required'},indent=2))
