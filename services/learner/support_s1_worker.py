"""File-only S1 adapter. No visit/Bayesian modules, database or network API."""
import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import os
from pathlib import Path
import time

from contracts.domain.analysis import canonical, sha
from contracts.domain.support_s1 import (S1Input,S1Result,consumed_ids,execution_binding)


def feature_histories(product,public_history):
    """Exact active-record seam; parent product retains full reduced lineage."""
    return [public_history(h.patient_id,h.origin,h.cutoff,tuple(h.records)) for h in product.histories]


def publish(path,value):
    temporary=path.with_suffix('.partial')
    temporary.write_text(canonical(value)+'\n',encoding='utf-8')
    temporary.replace(path)


def run(source,out):
    started=time.monotonic();product=S1Input.model_validate_json(source.read_bytes())
    out.mkdir(parents=True,exist_ok=True)
    origin={k:os.environ[v] for k,v in dict(learner_image='REMISSION_LEARNER_IMAGE',
        source_commit='REMISSION_SOURCE_COMMIT').items()}
    binding=execution_binding(product,origin)
    base=dict(schema_version='3.0.0',synthetic=True,kind='poc_support_s1_result',purpose='S1-WCLS',
        attempt_id=product.attempt_id,input_sha256=sha(product.model_dump(mode='json')),
        history_sha256=product.history_sha256,feature_history_sha256=None,
        archive=product.archive.model_dump(mode='json'),cohort=[m.model_dump() for m in product.cohort],
        cutoff=product.cutoff.isoformat(),configuration=product.configuration.model_dump(),
        model=product.model.model_dump(),prior=product.prior.model_dump(),estimand=product.estimand.model_dump(),
        protocol=product.protocol.model_dump(),status='failed',reason='worker-incomplete',
        consumed_record_ids=consumed_ids(product),generated_at=datetime.now(timezone.utc).isoformat(),
        diagnostics=dict(execution=binding),artifacts=[],output=None,
        limitations=['Historical synthetic 12-member cohort excursion; no individual prediction, ISI benefit or policy recommendation.',
            'Known randomized .5/.5 probabilities; complete observed rewards under declared independent .1 MCAR.',
            'Participant-clustered 95% interval with G-1 degrees of freedom; minimum8clusters is an engineering gate.',
            'Nine R1 missing-reward sensitivity cells are assumption-driven point estimates only; no sensitivity interval or MNAR identification.'])
    def stage(name):publish(out/'progress.json',dict(attempt_id=product.attempt_id,
        input_sha256=base['input_sha256'],stage=name))
    try:
        stage('preparing');imports=time.monotonic()
        from methods.support.data import PublicHistory,build_features
        from methods.support.wcls import fit
        imported=time.monotonic();stage('fitting')
        data=build_features(feature_histories(product,PublicHistory));featured=time.monotonic()
        fitted=fit(data,provenance_seed=product.provenance_seed);finished=time.monotonic()
        base['feature_history_sha256']=data.history_sha256
        base['diagnostics'].update(wcls=asdict(fitted),feature_source_ids=sorted({s for r in data.rows for s in r.source_ids}),
            decision_ids=sorted(r.decision_id for r in data.rows),
            weighted_rank=sum(s>max(len(data.observed),6)*2.220446049250313e-16*max(fitted.singular_values)
                for s in fitted.singular_values) if fitted.singular_values else None,
            timings=dict(import_seconds=imported-imports,feature_seconds=featured-imported,
                estimator_seconds=finished-featured,worker_seconds=finished-started))
        if fitted.status=='estimated':
            base.update(status='completed',reason=None,output=dict(kind='wcls_excursion_inference',unit='quality_points',
                coefficient=fitted.estimate,standard_error=fitted.standard_error,interval=fitted.interval,df=fitted.df))
        else:base.update(status='abstained',reason='; '.join(fitted.reasons))
    except Exception as error:
        base.update(status='failed',reason=type(error).__name__+': '+str(error),output=None)
        base['diagnostics']['timings']=dict(worker_seconds=time.monotonic()-started)
    stage('diagnostics');base['generated_at']=datetime.now(timezone.utc).isoformat()
    # Validate gates before publishing either artifact. Validation errors remain
    # failed attempts via host supervision, never a completed result fallback.
    checked=S1Result.model_validate_json(canonical(base))
    diagnostics=checked.model_dump(mode='json')['diagnostics']
    publish(out/'wcls.json',diagnostics)
    import hashlib
    base['artifacts']=[dict(path='wcls.json',sha256=hashlib.sha256((out/'wcls.json').read_bytes()).hexdigest())]
    publish(out/'result.json',S1Result.model_validate_json(canonical(base)).model_dump(mode='json'))


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--input',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    run(args.input,args.output)


if __name__=='__main__':main()
