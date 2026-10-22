"""One full-model graph per copied process; never a sampler or alternate target."""
import argparse
import gc
import hashlib
import json
from pathlib import Path
import resource
import time


def publish(path,value):
    temporary=path.with_suffix('.partial')
    temporary.write_text(json.dumps(value,sort_keys=True,allow_nan=False)+'\n')
    temporary.replace(path)


def run(input_root,output,phase,seconds,coordinates=None,monitor_policy=None,reference=None):
    started=time.monotonic();output.mkdir(parents=True,exist_ok=True)
    def marker(stage,**extra):
        memory={}
        for name in ('memory.current','memory.peak'):
            path=Path('/sys/fs/cgroup')/name
            if path.exists():memory[name]=int(path.read_text())
        event=dict(phase=phase,stage=stage,elapsed_seconds=time.monotonic()-started,
            memory=memory,peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,**extra)
        with (output/(phase+'-events.jsonl')).open('a') as stream:
            stream.write(json.dumps(event,sort_keys=True,allow_nan=False)+'\n');stream.flush()
        print(json.dumps(event,sort_keys=True),flush=True)
        if time.monotonic()-started>=seconds:raise TimeoutError('phase deadline; no qualification')
    marker('before-imports')
    import copy
    import numpy as np
    from scipy.stats import norm,halfnorm
    from contracts.domain.analysis import AnalysisInput,sha
    from contracts.domain.borrowing import SourceBundle,BORROW_CONFIG,BORROW_CONFIG_REF,APPROVED_BUNDLES
    from methods.visit.model import build,inputs
    from methods.visit.borrow_model import build_joint
    from methods.visit.borrowing import marginal
    marker('after-imports')
    product=AnalysisInput.model_validate_json((input_root/'input.json').read_bytes())
    sources=SourceBundle.model_validate_json((input_root/'sources.json').read_bytes())
    if sha(sources.model_dump(mode='json'))!=APPROVED_BUNDLES[sources.bundle_id]:raise ValueError('unapproved source bytes')
    frozen=json.loads((input_root/'points.json').read_bytes())
    if product.history_sha256!=frozen['history_sha256'] or BORROW_CONFIG_REF!=frozen['configuration']:raise ValueError('frozen identity mismatch')
    data=inputs(product.history)
    points=[{key:np.asarray(value,dtype='float64') for key,value in row.items()} for row in frozen['guided_points']]
    binding=dict(history_sha256=product.history_sha256,cutoff=product.history.cutoff.isoformat(),
        configuration=BORROW_CONFIG_REF,source_set_sha256=sources.source_set_sha256,
        input_files={name:hashlib.sha256((input_root/name).read_bytes()).hexdigest() for name in ('input.json','points.json','sources.json')})
    marker('input-verified',binding=binding)
    trace=None
    if monitor_policy is not None:
        if phase!='guided-gradient' or reference is None:raise ValueError('monitor is guided-gradient diagnosis only')
        from pa3_monitor import MetadataTrace
        policy=json.loads(monitor_policy.read_bytes())
        if binding['input_files']!=policy['input_files']:raise ValueError('monitor input freeze mismatch')
        if hashlib.sha256(reference.read_bytes()).hexdigest()!=policy['guided_reference_sha256']:raise ValueError('monitor FD reference hash mismatch')
        trace=MetadataTrace(output,policy)
    if phase!='coordinates':
        if trace and hashlib.sha256(coordinates.read_bytes()).hexdigest()!=policy['coordinates_sha256']:raise ValueError('monitor coordinate map hash mismatch')
        converted=json.loads(coordinates.read_bytes())
        if converted['binding']!=binding:raise ValueError('coordinate/input binding mismatch')
        originals=[{key:np.asarray(value,dtype='float64') for key,value in row.items()} for row in converted['original_points']]
    guided=phase in ('coordinates','guided-logp','guided-gradient')
    marker('before-model-construction')
    if phase=='local-logp':model=build(data,guide=False)
    else:
        if phase=='changed-logp':
            sources=copy.deepcopy(sources);sources.studies[0].__dict__['d']+=.7
        model=build_joint(data,sources,BORROW_CONFIG,guide=guided)
    marker('after-model-construction')
    result=dict(phase=phase,binding=binding,status='not-qualified')
    if phase=='coordinates':
        marker('before-coordinate-jacobian-compile')
        fn=model.compile_fn(model.replace_rvs_by_values([model['prior_normal_coordinates'],model['guide_log_jacobian']]),inputs=model.value_vars,on_unused_input='ignore')
        marker('after-coordinate-jacobian-compile')
        originals=[];jacobians=[]
        expected={v.name for v in model.value_vars}
        for point in points:
            if set(point)!=expected:raise ValueError('frozen guide coordinate names mismatch')
            u,jac=fn(point)
            original={key:value for key,value in point.items() if key!='guide_innovation'}
            original.update(mu_b=19+5*u[0],b_raw=u[1],population_beta=4*u[2:4],beta_raw=u[4:6],a=u[6],innovation=u[7:])
            originals.append({k:np.asarray(v).tolist() for k,v in original.items()});jacobians.append(float(jac))
        del fn;gc.collect()
        result.update(original_points=originals,log_jacobians=jacobians,
            mapping='mu_b=19+5u0;b_raw=u1;population_beta=4u[2:4];beta_raw=u[4:6];a=u6;innovation=u[7:]; density correction log(80)+guide_log_jacobian')
    else:
        selected=points if guided else originals
        if phase=='local-logp':selected=[{k:v for k,v in point.items() if k not in ('source_bias','source_tau_log__')} for point in selected]
        names=[v.name for v in model.value_vars]
        if any(set(point)!=set(names) for point in selected):raise ValueError('model coordinate names mismatch')
        gradient=phase.endswith('gradient')
        marker('before-gradient-compile' if gradient else 'before-logp-compile')
        begin=time.monotonic();fn=model.compile_dlogp(**({'mode':trace.mode} if trace else {})) if gradient else model.compile_logp()
        result['compile_seconds']=time.monotonic()-begin
        marker('after-gradient-compile' if gradient else 'after-logp-compile')
        if trace:trace.inventory(fn);marker('optimized-inventory-saved')
        values=[];differences=[];timings=[]
        for index,point in enumerate(selected):
            marker('before-point',index=index)
            if trace:trace.point=index
            begin=time.perf_counter();value=fn(point)
            if trace:timings.append(time.perf_counter()-begin);trace.status()
            if not np.isfinite(value).all():raise ValueError('nonfinite full-model evaluation')
            values.append(np.asarray(value).tolist())
            if not gradient:
                # Independent coordinate finite differences, in exactly the
                # value-variable ordering used by this model's autodiff.
                finite=[]
                for name in names:
                    for cell in np.ndindex(point[name].shape):
                        left=copy.deepcopy(point);right=copy.deepcopy(point)
                        left[name][cell]-=1e-5;right[name][cell]+=1e-5
                        finite.append(float((fn(right)-fn(left))/(2e-5)))
                differences.append(finite)
            for _ in range(0 if trace else 20):
                begin=time.perf_counter();fn(point);timings.append(time.perf_counter()-begin)
            marker('after-point',index=index)
        del fn;gc.collect()
        result.update(values=values,value_variable_order=names,median_seconds=float(np.median(timings)),p95_seconds=float(np.quantile(timings,.95)))
        if not gradient:result['coordinate_finite_difference']=differences
        if trace:
            baseline=json.loads(reference.read_bytes())
            if baseline['binding']!=binding or baseline['value_variable_order']!=names:raise ValueError('FD coordinate identity mismatch')
            for actual,finite in zip(values,baseline['coordinate_finite_difference'],strict=True):
                if len(actual)!=47 or len(actual)!=len(finite):raise ValueError('all47 frozen gradient coordinates required')
                for a,b in zip(actual,finite,strict=True):
                    if abs(a-b)>1e-5+1e-4*abs(b):raise ValueError('equal-coordinate gradient FD gate unmet')
            trace.finished=True
            result.update(trace=trace.status(),independent_fd=dict(passed=True,points=3,coordinates_per_point=47,
                absolute_tolerance=1e-5,relative_tolerance=1e-4,reference_sha256=policy['guided_reference_sha256']),
                diagnostic_only='MonitorMode linker; ordinary NumbaLinker runtime and full-target acceptance remain unqualified')
        if phase=='original-logp':
            expected=[];negative=[]
            for point in originals:
                theta=dict(mu_b=float(point['mu_b']),beta_c=float(point['population_beta'][0]),beta_e=float(point['population_beta'][1]),
                    sd_b=float(np.exp(point['sd_b_log__'])),sd_beta_c=float(np.exp(point['sd_beta_log__'][0])),sd_beta_e=float(np.exp(point['sd_beta_log__'][1])),
                    p=float(1/(1+np.exp(-point['p_adherence_logodds__']))),rho=float(1.9/(1+np.exp(-point['rho_interval__']))-.95),
                    sigma_e=float(np.exp(point['sigma_e_log__'])),sigma_isi=float(np.exp(point['sigma_isi_log__'])),a=float(point['a']))
                g=marginal(theta,64);tau=float(np.exp(point['source_tau_log__']));bias=point['source_bias']
                terms=[float(np.logaddexp(np.log(.5)+norm.logpdf(s.d,g+b,np.sqrt(s.se*s.se+tau*tau)),np.log(.5)+norm.logpdf(s.d,0,np.sqrt(s.se*s.se+100)))) for s,b in zip(sources.studies,bias)]
                priors=float(norm.logpdf(bias,0,.5).sum()+halfnorm.logpdf(tau,scale=1)+np.log(tau))
                reversed_terms=[float(np.logaddexp(np.log(.5)+norm.logpdf(-s.d,g+b,np.sqrt(s.se*s.se+tau*tau)),np.log(.5)+norm.logpdf(-s.d,0,np.sqrt(s.se*s.se+100)))) for s,b in zip(sources.studies,bias)]
                expected.append(sum(terms)+priors)
                negative.append(dict(doubled=2*sum(terms)+priors,omitted=terms[0]+priors,reversed=sum(reversed_terms)+priors))
            result.update(independent_source_and_prior_logp=expected,negative_control_logp=negative)
    marker('before-terminal-publication')
    result.update(status='evaluated',elapsed_seconds=time.monotonic()-started)
    publish(output/(phase+'.json'),result)
    marker('published')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--input',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--phase',choices=['coordinates','guided-logp','guided-gradient','original-logp','original-gradient','local-logp','changed-logp'],required=True)
    parser.add_argument('--seconds',type=float,required=True);parser.add_argument('--coordinates',type=Path)
    parser.add_argument('--monitor-policy',type=Path);parser.add_argument('--reference',type=Path);args=parser.parse_args()
    run(args.input,args.output,args.phase,args.seconds,args.coordinates,args.monitor_policy,args.reference)
