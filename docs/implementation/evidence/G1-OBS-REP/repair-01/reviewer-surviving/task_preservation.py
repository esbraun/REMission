import reproduce,json,subprocess,hashlib
reproduce.out=reproduce.out/'final-checks'
reproduce.run(['git','remote','-v'],reproduce.root/'.review-artifacts/https-clone')
base='6bc8bd998e8a0baaef9884998e740665fb5fd7b1';p='docs/implementation/g0-task-test-ledger-20261020.json'
a=json.loads(subprocess.check_output(['git','show',base+':'+p],cwd=reproduce.root));b=json.loads((reproduce.root/p).read_bytes())
assert a['coverage']==b['coverage'] and len(b['coverage'])==635
assert a['coverage_counts']==b['coverage_counts']
assert len(b['tasks'])>=len(a['tasks'])
for before,after in zip(a['tasks'],b['tasks']):
 for k in ['id','test_ids','requirement_ids','depends_on']:assert before[k]==after[k]
print('PASS exact 635 coverage and all original task/test/requirement/dependency fields')
(reproduce.out/'task-preservation.json').write_text(json.dumps({'base':base,'head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=reproduce.root).decode().strip(),'original_tasks':len(a['tasks']),'coverage':635,'result':'PASS'},indent=2))
