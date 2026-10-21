"""Add rejected2a review/repair checkpoint without rewriting raw history."""
import copy
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[5]
PREFIX=Path(__file__).resolve().parent.relative_to(ROOT).as_posix()


def main():
    path=ROOT/'docs/implementation/g0-task-test-ledger-20261020.json';data=json.loads(path.read_text())
    if 'prior_interface_assignment_2a' in data:raise SystemExit('already reconciled; preserve the prior checkpoint')
    data['prior_interface_assignment_2a']=copy.deepcopy(data['current_assignment'])
    review=dict(reviewed_head='2a7726be23864cf9c933295f1d33da3d6fbedd1b',reviewed_base='69e6ae9dc5bf85ddbf39976d2ce4ce70bce1ea1e',disposition='changes_requested',path=PREFIX+'/independent-review-2a.md',blob='bb708c7e9bffea3ff997fd0eafba05303b6f94fd',evidence_manifest_path=PREFIX+'/independent-evidence-manifest-2a.json',evidence_manifest_blob='a732313d5a0b1957ca5c724691728db3d709a489',findings=['P1 own authenticated symptom pilot and separate ISI accuracy','P1 IID batch/pooled precision and trusted resolved investigation','P2 event-time/nested-uncertainty consistency'])
    data['current_assignment'].update(status='needs_review',evidence=[PREFIX+'/verification.md'],prior_reviews=[review],blocker='All three author repairs awaiting refreshed exact-head independent review; no merge acceptance')
    interpretation=dict(path=PREFIX+'/iid-policy-interpretation.md',blob='aede75810ca4ff2178b5f4126d0f80f050366618',status='root_accepted_conservative_engineering_interpretation',claim_limit='Both IID inequalities and externally trusted resolved investigation for every IID admission; no ratio threshold or statistical acceptance')
    data['accepted_probability_plan']['iid_admission_interpretation']=interpretation
    for item in data['execution_evidence']:
        if item.get('record_kind')=='current_author_interface_candidate':item['record_kind']='historical_author_interface_candidate_checkpoint'
    data['execution_evidence'].extend([dict(task_id='G1-GENERATOR',record_kind='historical_rejected_candidate',status='changes_requested',reviewed_head=review['reviewed_head'],reviewed_base=review['reviewed_base'],evidence=review['path'],claim_limit='All17 runner checks passed on rejected2a; independent adverse probes established three missing admission checks'),dict(task_id='G1-GENERATOR',record_kind='current_author_interface_candidate',status='needs_review_after_precision_repair',evidence=PREFIX+'/verification.md',claim_limit='Pure contract/IO validation and repair only; actual independent producer execution/throughput/statistical acceptance remain pending')])
    generator=next(t for t in data['tasks'] if t['id']=='G1-GENERATOR');generator.update(interface_candidate_status='needs_review_after_precision_repair',interface_evidence=[PREFIX+'/verification.md'],prior_interface_reviews=[review])
    path.write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8',newline='\n')
    prefix='# Current shared-interface precision repair (2026-10-21)\n\nIndependent review rejected2a7726b despite17/17 runner checks: unauthenticated symptom pilot/accuracy, unchecked IID dispersion admission, and inconsistent event-time/nested uncertainty fields. The complete raw report, evidence and original mutation outputs remain byte-exact in [repair evidence](evidence/G1-GENERATOR-INTERFACES-20261021/repair/verification.md). The current bounded repair recomputes separate symptom pilot evidence, checks its ISI epsilon, requires both IID precision inequalities plus out-of-band trusted investigation, and crosschecks every returned event time and symptom uncertainty. Refreshed exact-head review is pending; previous author passes below are historical. G0/foundation remain accepted; G1 and synthetic engineering running, all producer/throughput/statistical/human/clinical acceptance deferred. All635 rows/mappings/dependencies remain unchanged.\n\n'
    for name in ('launch-status-20261020.md','library-qualification.md'):
        target=ROOT/'docs/implementation'/name;target.write_text(prefix+target.read_text(),encoding='utf-8',newline='\n')


if __name__=='__main__':main()
