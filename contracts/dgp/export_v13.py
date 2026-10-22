"""Additive explicit1.3 authoring products; never writes a legacy artifact."""
import argparse,json
from pathlib import Path
from .profile_v13 import encoded,reference_laws,reference_parameters,scenario_manifest,validate_parameters,validate_scenarios,VERSION

ROOT=Path(__file__).parent


def products():
    from .timing import timing_manifest as old_timing
    from .profile_v13 import profile_bindings,PROCESSES
    bindings=profile_bindings();timing=old_timing()
    timing.update(version=VERSION,wire_schema_version='2.1.0',temporal_contract=bindings['temporal'],
        temporal_source='contracts/domain/temporal-v2.1.json',profile=bindings)
    timing['local_clocks'].update(report_completion_publication='08:01',burden_status_sweep='08:02',burden_link_sweep='08:03',
        safety_events_and_schedule='09:00_a',synthetic_eligibility_assessment='09:00_b',
        episode_review='09:00_c',current_admission_and_readiness='09:00_d',assignment='09:00_e')
    timing['pain']['source']['version']=VERSION
    timing['process_keys'].update({k:dict(namespace=n,process=p,substream=s) for k,(n,p,s) in PROCESSES.items()})
    timing['reporting_parent']='new immediate publicR source; one sharedR/shared delay; latent probability remains private'
    return {'parameters-v1.3.json':validate_parameters(reference_parameters()),
        'scenarios-v1.3.json':validate_scenarios(scenario_manifest()),'timing-v1.3.json':timing,'laws-v1.3.json':reference_laws()}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--check',action='store_true');a=parser.parse_args()
    for name,value in products().items():
        path=ROOT/name;raw=encoded(value)
        if a.check:
            if not path.is_file() or path.read_bytes()!=raw:raise SystemExit('DGP1.3 drift: '+name)
        else:path.write_bytes(raw)
    print('PASS: additive DGP1.3 parameter/catalog/time/law products; no calibration qualification')


if __name__=='__main__':main()
