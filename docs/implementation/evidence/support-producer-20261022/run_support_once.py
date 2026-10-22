"""Public-only offline WCLS attempts; no generator, evaluator, Store or jobs.

Use only after independent source/role qualification and exact invocation
authorization. UNIT fixtures cannot qualify a production run. Each S1 cutoff
gets exactly one build_features/fit attempt; abstentions and failures persist.
"""
import time
IMPORT_STARTED=time.perf_counter()
import argparse
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import resource
import traceback

from contracts.domain.protocol_analysis import ProtocolHistory
from contracts.runs.common import canonical, sha256
from contracts.runs.support_research import SupportResearchIndex, SupportRuntime, read_artifact
from methods.support.data import PublicHistory, build_features
from methods.support.wcls import CONFIGURATION, SETTINGS, fit

IMPORT_SECONDS=time.perf_counter()-IMPORT_STARTED


def _write(root,name,value):
    raw=canonical(value);target=root/name
    if target.is_symlink():raise ValueError('symlink_result_denied')
    with target.open('xb') as handle:handle.write(raw)
    return dict(path=name,sha256=sha256(raw),bytes=len(raw))


def _summary(histories):
    reports=[r for h in histories for r in h.records if r.kind=='daily_report']
    observed=[r.sleep_quality for r in reports if r.missingness=='observed']
    links=[r for h in histories for r in h.records if r.kind=='support_outcome_link']
    decisions=[r for h in histories for r in h.records if r.kind=='support_decision']
    return dict(report_count=len(reports),observed_report_count=len(observed),
        reporting_rate=len(observed)/len(reports) if reports else None,
        observed_mean_quality=sum(observed)/len(observed) if observed else None,
        burden={stage:sum(b.value for r in links for b in r.burden if b.type==stage and b.status=='observed')
                for stage in ('offered_prompt_count','delivered_prompt_count')},
        decision_count=len(decisions),availability={state:sum(r.availability==state for r in decisions)
                for state in ('randomized','deterministic','unavailable')})


def run(manifest,output_root,*,runtime):
    started=datetime.now(timezone.utc);tick=time.perf_counter();manifest=Path(manifest)
    raw=manifest.read_bytes();index=SupportResearchIndex.model_validate_json(raw)
    runtime=SupportRuntime.model_validate_json(canonical(runtime))
    root=manifest.parent;output_root=Path(output_root).resolve()
    if output_root.exists() and any(output_root.iterdir()):raise ValueError('fresh_attempt_output_required_no_success_retries')
    output_root.mkdir(parents=True,exist_ok=True)
    attempts=[];failed=False
    for day in (14,42,84):
        attempt_tick=time.perf_counter();load_tick=attempt_tick;inputs=[];histories={'S0':[],'S1':[]}
        # No full audit, assignment seed, private recipe or generator import is
        # needed by this role. Raw hashes bind the exact copied public inputs.
        for trajectory in index.trajectories:
            artifact=trajectory.projections[str(day)];data=read_artifact(root,artifact)
            public=ProtocolHistory.model_validate_json(data)
            if public.patient_id!=trajectory.member_id or public.origin!=index.origin or public.cutoff!=index.origin+timedelta(days=day):
                raise ValueError('wrong_member_origin_or_cutoff_in_public_projection')
            histories[trajectory.mode].append(public)
            inputs.append(dict(mode=trajectory.mode,member_id=trajectory.member_id,paired_member_id=trajectory.paired_member_id,
                artifact=artifact.model_dump(mode='json')))
        loaded=time.perf_counter();seed='fit/wcls-unused-provenance/'+index.run_id+'/day-'+str(day)
        record=dict(day=day,simulated_days=day,manifest_sha256=sha256(raw),inputs=inputs,
            configuration=CONFIGURATION,settings=SETTINGS,source_commit=index.source_commit,runtime=runtime.model_dump(mode='json'),
            generator_runtime=index.runtime.model_dump(mode='json'),
            provenance_seed=seed,seed_used=False,summary={mode:_summary(values) for mode,values in histories.items()},
            stage_wall_seconds=dict(load_and_validate=loaded-load_tick))
        try:
            features=build_features([PublicHistory(h.patient_id,h.origin,h.cutoff,tuple(h.records)) for h in histories['S1']])
            featured=time.perf_counter()
            result=fit(features,provenance_seed=seed) # Exactly one actual call.
            fitted=time.perf_counter()
            record.update(result=asdict(result),feature_history_sha256=features.history_sha256,
                feature_rows=len(features.rows),observed_rows=len(features.observed),excluded=features.excluded)
            record['stage_wall_seconds'].update(build_features=featured-loaded,fit=fitted-featured)
        except Exception as error:
            # Keep the failed attempt without manufacturing a coefficient or
            # changing seeds/settings. The command returns nonzero afterwards.
            failed=True;record.update(result=dict(status='failed',reasons=[str(error)]),traceback=traceback.format_exc())
        record['stage_wall_seconds']['before_publication']=time.perf_counter()-attempt_tick
        record['peak_rss_kib']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        record['publication_at']=datetime.now(timezone.utc).isoformat()
        published=time.perf_counter();artifact=_write(output_root,f'day-{day}.json',record)
        attempts.append(dict(day=day,result=record['result']['status'],artifact=artifact,
            publication_wall_seconds=time.perf_counter()-published,total_wall_seconds=time.perf_counter()-attempt_tick))
    return _write(output_root,'results.json',dict(version='poc-support-offline-attempts-v1',manifest_sha256=sha256(raw),
        source_commit=index.source_commit,runner_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        started_at=started.isoformat(),ended_at=datetime.now(timezone.utc).isoformat(),cold_import_wall_seconds=IMPORT_SECONDS,
        total_wall_seconds=time.perf_counter()-tick,peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        attempts=attempts,status='failed' if failed else 'attempts_completed',
        limitation='One development panel; no accuracy, confirmation, policy value, clinical benefit or production p95 claim')),(1 if failed else 0)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest',type=Path,required=True);parser.add_argument('--output-root',type=Path,required=True)
    parser.add_argument('--runtime',type=Path,required=True)
    args=parser.parse_args();artifact,code=run(args.manifest,args.output_root,runtime=json.loads(args.runtime.read_bytes()))
    print(json.dumps(artifact,sort_keys=True));raise SystemExit(code)
