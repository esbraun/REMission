"""One-time additive accepted-foundation and interface checkpoint reconciliation."""
import copy
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[4]
OUT=Path(__file__).resolve().parent
BASE='69e6ae9dc5bf85ddbf39976d2ce4ce70bce1ea1e'
PREFIX=OUT.relative_to(ROOT).as_posix()
RAW={
 'foundation-final-ready-review.md':'fbbf95f62dd5d2a2d016caabcd5c22f58bf94268',
 'foundation-final-evidence-manifest.json':'369c9fc71a32117c161dbf4423e4bac193d45a84',
 'probability-plan-ready-review.md':'c68541474c6e63b8f1cf9902c0d8c2b41def100e'}


def main():
    for name,blob in RAW.items():
        (OUT/name).write_bytes(subprocess.check_output(['git','cat-file','blob',blob],cwd=ROOT))
    ledger=ROOT/'docs/implementation/g0-task-test-ledger-20261020.json'
    d=json.loads(ledger.read_text(encoding='utf-8'))
    if 'accepted_foundation_assignment' in d:raise SystemExit('already reconciled; do not rewrite history')
    d['prior_foundation_assignment']=copy.deepcopy(d['current_assignment'])
    foundation=copy.deepcopy(d['current_assignment'])
    foundation.update(status='accepted_engineering_scope_only',review_disposition='ready_to_ship',candidate_commit='3179f3d2fcc7c9f285129b0272e868d413ced089',reviewed_head='3179f3d2fcc7c9f285129b0272e868d413ced089',reviewed_base='8ca67682505d78accc855e92cbfbb6692edf8316',merge_commit=BASE,pr_url='https://github.com/esbraun/REMission/pull/16',blocker=None,
        accepted_review=dict(path=PREFIX+'/foundation-final-ready-review.md',blob=RAW['foundation-final-ready-review.md'],evidence_manifest_path=PREFIX+'/foundation-final-evidence-manifest.json',evidence_manifest_blob=RAW['foundation-final-evidence-manifest.json']),claim_limit='Root accepted complete bounded G1 foundation engineering only; G1 generator/statistical/human/clinical remain pending')
    d['accepted_foundation_assignment']=foundation
    current=dict(id='G1-GENERATOR',package_id='G1-GENERATOR-INTERFACES',owner_thread='/root/g0_closure_sol',app_thread_id='01a15f0f-b7cd-73f3-86cb-af5f08360615',agent_model='gpt-6.1-sol',reasoning_effort='high',effective_model='Explicit assignment observed; no independent model introspection',effort_escalation_reason=None,worktree_path=ROOT.as_posix(),task_branch='launch/g1-generator-interfaces-20261021',base_commit=BASE,review_target_base=BASE,integration_target='main',status='needs_review',review_disposition='pending',candidate_commit=None,evidence=[PREFIX+'/verification.md'],claim_limit='Shared run/export/evaluator contracts and pure R1 qualification only; no producer/filter/calibration/truth execution or throughput/statistical acceptance')
    d['current_assignment']=current
    tasks={t['id']:t for t in d['tasks']}
    for key in ('status','review_disposition','candidate_commit','reviewed_head','reviewed_base','merge_commit','pr_url','accepted_review','blocker','claim_limit'):
        tasks['G1-FOUNDATION'][key]=copy.deepcopy(foundation[key])
    tasks['G1-GENERATOR'].update(status='running',interface_candidate_status='needs_review',owner_thread=current['owner_thread'],app_thread_id=current['app_thread_id'],agent_model='gpt-6.1-sol',reasoning_effort='high',base_commit=BASE,worktree_path=ROOT.as_posix(),task_branch=current['task_branch'],interface_evidence=current['evidence'],claim_limit=current['claim_limit'])
    d['execution_evidence'].append(dict(task_id='G1-FOUNDATION',record_kind='current_accepted_package',status='accepted_engineering_scope_only',review_disposition='ready_to_ship',reviewed_head=foundation['reviewed_head'],reviewed_base=foundation['reviewed_base'],merge_commit=BASE,evidence=PREFIX+'/foundation-final-ready-review.md',claim_limit=foundation['claim_limit']))
    d['execution_evidence'].append(dict(task_id='G1-GENERATOR',record_kind='current_author_interface_candidate',status='needs_review',evidence=PREFIX+'/verification.md',claim_limit=current['claim_limit']))
    d['accepted_probability_plan']=dict(status='root_accepted_plan_only',contract_id='ESTINT-PRECISION-01',contract_version='1.0.0-r1',reviewed_head='99fbcc31267284481fe8e4820530635eaecc7ce5',reviewed_base=BASE,root_accepted=True,path='docs/implementation/g1-estint-probability-precision-proposal-r1-20261021.md',blob='233d78d5f9233499e566c87ecf34d3d4f12e3785',accepted_critique=dict(path=PREFIX+'/probability-plan-ready-review.md',blob=RAW['probability-plan-ready-review.md'],disposition='ready_to_proceed'),original_proposal=dict(path='docs/implementation/g1-estint-probability-precision-proposal-20261021.md',blob='cc283ee4303b47863d54b76d576d301a8056da5a'),original_critique=dict(path='docs/implementation/g1-estint-probability-precision-critique-original-20261021.md',blob='3c8536df021ce221ac75ffca1f9ebf90ab7816f0'),claim_limit='Plan only; source interface candidate awaits independent review; actual producer independence and throughput unqualified')
    d['accepted_g1_plan']['source_dispatch']='Foundation accepted PR16; bounded shared interfaces now under independent review; generator/evaluator production source waits accepted interfaces'
    d['prior_runtime_checkpoint']=copy.deepcopy(d['runtime'])
    d['runtime'].update(observed_open_non_luna=2,observed_spawned=2,observed_total_including_root=3,inventory=['root orchestrator','G1 interface Sol/high 01a15f0f-b7cd-73f3-86cb-af5f08360615','retained independent critic Astra/medium 01a15f90-84f8-7b61-ae72-46eaec069201'],queued=['Exact-head/base independent interface review, then PR/merge only after ready_to_ship','Accepted-base generator/evaluator production ownership split follows interface acceptance','G2-G7 statistical/full integration and human/clinical deferred'],source_inventory_helper=dict(status='completed_archived_native_removal_root_verified',thread_id='01a15f97',worktree='C:/Users/erics/Documents/Projects/REMission-worktrees/g1-equation-inventory-luna-20261021',branch='launch/g1-equation-inventory-20261021',base=BASE,source_inventory_commit='4b27bb1cb92f51583fa236fbe394e09b53c4ccbf',claim='Locator-only canonical equation/output inventory, no source implementation or tests'),prior_active_schedule=dict(open_non_luna=2,children=3,total_including_root=4,luna='g1_equation_inventory_luna/high; source-only; completed and released before final checkpoint'),free_luna_runtime_slots=1)
    before=json.loads(subprocess.check_output(['git','show',BASE+':docs/implementation/g0-task-test-ledger-20261020.json'],cwd=ROOT))
    assert d['coverage']==before['coverage'] and d['coverage_counts']==before['coverage_counts']
    for task in d['tasks']:
        original=next(t for t in before['tasks'] if t['id']==task['id'])
        assert all(task[k]==original[k] for k in ('id','depends_on','test_ids','requirement_ids'))
    ledger.write_text(json.dumps(d,indent=2)+'\n',encoding='utf-8',newline='\n')


if __name__=='__main__':main()
