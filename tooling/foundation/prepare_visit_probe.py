"""Privileged offline producer. Publish only H*; never copy this tool to learner."""
import argparse
from datetime import timedelta
from pathlib import Path
from contracts.domain.analysis import make_input,project_history,canonical
from contracts.domain.boundaries import ObservedHistory
from services.generator.restricted import generate,START
from services.foundation.workflow import record_header,SUPPORT


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--attempt-id',default='analysis-probe-day14');parser.add_argument('--fit-replicate',type=int,default=731521);args=parser.parse_args()
    patient='POC-V0-PROBE'
    assignment=dict(**record_header('probe-assignment',patient,START),kind='assignment',decision_id='probe-decision',approval_id='probe-approval',
        option='behavioral_continue',experimental=False,component=None,probability=None,seed=None,support_policy=SUPPORT,
        patient_blinded=False,clinician_blinded=False,clinician_override=None,override_reason=None)
    observed=generate(dict(seed=20261021,index=0,patient_id=patient,through_day=14,actions=[dict(day=0,option='behavioral_continue',assignment_id='probe-assignment')]))
    history=ObservedHistory.model_validate_json(canonical(dict(schema_version='1.0.0',synthetic=True,kind='observed_history',patient_id=patient,
        records=[assignment,*[entry['record'] for entry in observed['records']]])))
    public=make_input(project_history(history.project(START+timedelta(days=14))),args.attempt_id,args.fit_replicate)
    args.output.write_text(canonical(public.model_dump(mode='json'))+'\n',encoding='utf-8')
    print(canonical(dict(status='public-Hstar-published',attempt_id=public.attempt_id,history_sha256=public.history_sha256)))


if __name__=='__main__':main()
