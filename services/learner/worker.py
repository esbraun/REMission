"""Foundation observed-export reader. No estimator/assignment engine is present."""
import json
from pathlib import Path
from contracts.domain.boundaries import ObservedHistory


def main():
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--product',choices=['observed','live-safety'],default='observed')
    parser.add_argument('--root',type=Path);parser.add_argument('--authority',type=Path)
    args=parser.parse_args()
    if args.product=='live-safety':
        if args.root is None or args.authority is None:
            parser.error('live-safety requires trusted dispatcher root and authority')
        from contracts.service.live_safety import TrustedLiveSafetyAuthority
        context=read_live_safety_export(args.root,TrustedLiveSafetyAuthority.model_validate_json(args.authority.read_bytes()))
        print(json.dumps(dict(status='live_safety_contract_validated',product='live-safety',version='1.0.0',
            patient_id=context.observed_projection.patient_id,independent_hold_status=context.independent_hold_status,statistical_engine='unavailable')))
        return
    raw=Path("/observed/history.json").read_bytes()
    version=json.loads(raw).get('schema_version')
    if version=='2.1.0':
        from contracts.domain.protocol import ObservedHistoryV21
        history=ObservedHistoryV21.model_validate_json(raw)
    elif version=='2.0.0':
        from contracts.domain.observed_v2 import ObservedHistoryV2
        history=ObservedHistoryV2.model_validate_json(raw)
    else:history=ObservedHistory.model_validate_json(raw)
    print(json.dumps({"status":"observed_contract_validated","patient_id":history.patient_id,"record_count":len(history.records),"statistical_engine":"unavailable"}))


def read_run_export(root: Path, authority):
    """Return strict cutoff projections only; no private run/seeds/truth import."""
    from contracts.runs.admission import read_admitted
    manifest,partitions=read_admitted(root,authority)
    return manifest,[projection for _,_,_,projection,_,_ in partitions]


def read_live_safety_export(root: Path,authority):
    from contracts.service.live_safety_admission import verify_live_safety
    return verify_live_safety((root/'manifest.json').read_bytes(),root,authority)


def dispatch_product(*,required_product,worker_capabilities,root,authority):
    """A live-required job cannot be dispatched to an observed-only reader."""
    if required_product!=('LIVE-SAFETY-EXPORT','1.0.0') or required_product not in worker_capabilities:
        raise ValueError('live_safety_worker_capability_required')
    if root is None or authority is None:
        raise ValueError('live_safety_product_and_authority_required')
    return read_live_safety_export(root,authority)


if __name__=='__main__':main()
