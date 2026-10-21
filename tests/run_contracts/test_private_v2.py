"""Inherited private admission barriers using wire fixtures, never production evidence."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from fixtures import ROOT, artifact, full_key, load, setup
from observed_v2_fixtures import build, ref
from contracts.dgp.calibration import calibration_request
from contracts.runs.common import Authority, canonical, sha256
from contracts.runs.observed_v2 import ExportAuthorityV2
from contracts.runs.private_v2 import AuthorityV2, RunManifestV2, verify_run_v2, verify_result_v2


class PrivateV2Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        old = setup(self.root)
        registries = {name: artifact(self.root, 'fixture-' + name, 'configuration/' + name + '.json', dict(kind='wire_fixture_registry', id=name), 'configuration')
                      for name in ['source_registry', 'transformation_registry']}
        self.f = build(self.root, cell_id='S23.MAR_20.n60',
                       registry=ref(registries['source_registry']['id'], digest=registries['source_registry']['sha256']),
                       transform=ref(registries['transformation_registry']['id'], digest=registries['transformation_registry']['sha256']))
        data = old['run'].model_dump(mode='json')
        data.update(schema_version='2.0.0', contract_version='2.0.0', run_id=self.f['manifest']['run_id'],
                    producer=self.f['manifest']['producer'], source_commit=self.f['manifest']['source_commit'],
                    runtime=self.f['manifest']['runtime'], bindings=self.f['manifest']['bindings'],
                    cutoff=self.f['manifest']['cutoff'], created_at=self.f['manifest']['created_at'])
        unit = data['units'][0]
        unit.update(id='unit', cell_id='S23.MAR_20.n60', preset='evaluation')
        unit['cohorts'][0]['id'] = 'cohort'
        configuration = dict(id='evaluation-config', version='2.0.0', repetitions=1,
                             cohorts=[dict(id='cohort', role='historical', patients_per_replicate=60)])
        config = artifact(self.root, configuration['id'], 'configuration/evaluation.json', configuration, 'configuration')
        unit['evaluation_configuration'] = ref(config['id'], digest=config['sha256'])
        data['inputs'].append(config)
        plan = artifact(self.root, 'OBS-REP-02', 'configuration/representation.md',
                        (ROOT / 'docs/implementation/g1-observed-representation-proposal-r1-20261021.md').read_bytes(), 'configuration', 'text/markdown')
        data['inputs'].append(plan)
        for name in ['source_registry', 'transformation_registry']:
            config = registries[name]
            data[name] = ref(config['id'], digest=config['sha256'])
            data['inputs'].append(config)
        data['schedule_inputs'] = []
        for patient in unit['cohorts'][0]['patients']:
            schedule = self.f['schedule'].model_dump(mode='json')
            if patient['id'] != 'SYN-02':
                schedule.update(id='schedule-' + patient['id'], patient_id=patient['id'], partition_id='partition-' + patient['id'])
            config = artifact(self.root, schedule['id'], 'configuration/' + schedule['id'] + '.json', schedule, 'configuration')
            data['inputs'].append(config)
            data['schedule_inputs'].append(config)
        data['sources'] = list({canonical(r.source.model_dump(exclude={'raw_sha256'})): r.source.model_dump(exclude={'raw_sha256'}) for r in self.f['history'].records}.values())
        self.data = data
        self.bind_run()

    def tearDown(self):
        self.tmp.cleanup()

    def bind_run(self):
        self.data['input_sha256'] = sha256(canonical(self.data['inputs']))
        self.run_raw = canonical(self.data)
        self.run = RunManifestV2.model_validate_json(self.run_raw)
        self.authority = load(AuthorityV2, dict(contract_version='2.0.0', run_id=self.run.run_id, producer=self.data['producer'],
                    manifest_sha256=sha256(self.run_raw), source_commit=self.data['source_commit'], runtime=self.data['runtime'],
                    bindings=self.data['bindings'], producer_qualification=None, allow_contract_fixture=True))

    def result(self):
        return dict(schema_version='2.0.0', synthetic=True, kind='generator_run_result', contract_version='2.0.0', run_id=self.run.run_id,
                    run_manifest=ref(self.run.run_id, digest=sha256(self.run_raw)), producer=self.data['producer'], execution='contract_fixture',
                    source_commit=self.data['source_commit'], runtime=self.data['runtime'], bindings=self.data['bindings'], status='failed',
                    reason='Hand-authored qualification wire fixture only; no producer execution', observed_exports=[], private_truth=[],
                    seed_ledger=None, calibration=[], reports=[], completion_receipts=[])

    def verify(self, value, **kwargs):
        raw = canonical(value)
        return verify_result_v2(raw, self.root, self.run, self.authority, sha256(raw), export_authorities={}, **kwargs)

    def calibration(self, *, solved=True):
        evaluator = self.authority.model_dump(mode='json')
        evaluator.pop('bindings'); evaluator.pop('contract_version'); evaluator.pop('producer_qualification')
        evaluator['producer'] = dict(id='independent-wire-evaluator', version='1.0.0', role='contract_fixture')
        evaluator = load(Authority, evaluator)
        sample = artifact(self.root, 'sample', 'calibration/sample.json', dict(fixture=True, executed=False), 'calibration')
        seeds = artifact(self.root, 'calibration-seeds', 'calibration/seeds.json', dict(fixture=True, executed=False), 'seed_ledger')
        binding = dict(schema_version='1.1.0', synthetic=True, **calibration_request(cell_id='S23.MAR_20.n60', dgp=self.run.bindings.dgp),
                       status='solved' if solved else 'inconclusive', calibration_sample_sha256=sample['sha256'], seed_key_sha256=seeds['sha256'],
                       sample_size=200000, achieved=.8 if solved else None, achieved_mcse=.00001 if solved else None,
                       coefficient=0.0 if solved else None, iterations=1 if solved else 0, frozen_before='development_and_confirmation')
        value = dict(schema_version='1.0.0', synthetic=True, kind='calibration_artifact', contract_version='1.0.0', run_id=self.run.run_id,
                     producer=evaluator.producer.model_dump(mode='json'), execution='contract_fixture', source_commit=self.data['source_commit'],
                     runtime=self.data['runtime'], binding=binding, sample=sample, seeds=seeds, source_reference=None, source_pilot=None, comparator_pilots=[])
        item = artifact(self.root, 'calibration', 'calibration/artifact.json', value, 'calibration')
        return item, {item['id']: (evaluator, item['sha256'])}

    def test_exact_predeclared_evaluation_roster_and_schedule_positive_and_reject(self):
        parsed, schedules = verify_run_v2(self.run_raw, self.root, self.authority)
        self.assertEqual(parsed, self.run)
        self.assertEqual(len(schedules), 60)
        # A resealed uploaded configuration still cannot change accepted roster.
        config = next(a for a in self.data['inputs'] if a['id'] == 'evaluation-config')
        changed = json.loads((self.root / config['path']).read_bytes())
        changed['cohorts'][0]['patients_per_replicate'] = 59
        replacement = artifact(self.root, config['id'], config['path'], changed, 'configuration')
        self.data['inputs'] = [replacement if a['id'] == config['id'] else a for a in self.data['inputs']]
        self.data['units'][0]['evaluation_configuration']['sha256'] = replacement['sha256']
        self.bind_run()
        with self.assertRaisesRegex(ValueError, 'evaluation cohort/replicate roster'):
            verify_run_v2(self.run_raw, self.root, self.authority)

    def test_failed_result_retained_and_execution_run_ref_truth_roster_rejected(self):
        value = self.result()
        self.assertEqual(self.verify(value)[0].status, 'failed')
        for change in [dict(execution='engine_run'), dict(run_manifest=ref('different-run', digest=sha256(self.run_raw)))]:
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.verify({**value, **change})
        truth = dict(schema_version='1.0.0', synthetic=True, kind='simulator_truth', access='evaluator_only', patient_id='SYN-02', day=0,
                     latent_states={}, structural_parameters=[], counterfactuals=[])
        value['private_truth'] = [artifact(self.root, 'truth', 'truth/patient.json', truth, 'private_truth')]
        self.verify(value)
        truth['patient_id'] = 'outside-run'
        value['private_truth'] = [artifact(self.root, 'truth', 'truth/patient.json', truth, 'private_truth')]
        with self.assertRaisesRegex(ValueError, 'private truth patient outside'):
            self.verify(value)
        truth['patient_id'] = 'SYN-02'; truth['unexpected_privilege'] = True
        value['private_truth'] = [artifact(self.root, 'truth', 'truth/patient.json', truth, 'private_truth')]
        with self.assertRaises(ValueError):
            self.verify(value)

    def test_calibration_requires_trusted_digest_solved_target_and_fixture_authority(self):
        value = self.result()
        item, policies = self.calibration()
        value['calibration'] = [item]
        # Positive is qualification of wire bindings only, never engine evidence.
        self.verify(value, calibration_policies=policies)
        with self.assertRaisesRegex(ValueError, 'separately trusted'):
            self.verify(value)
        with self.assertRaisesRegex(ValueError, 'substitute self-declared'):
            self.verify(value, calibration_policies={item['id']: (policies[item['id']][0], 'f' * 64)})
        denied = policies[item['id']][0].model_copy(update={'allow_contract_fixture': False})
        with self.assertRaisesRegex(ValueError, 'fixture'):
            self.verify(value, calibration_policies={item['id']: (denied, item['sha256'])})
        item, policies = self.calibration(solved=False); value['calibration'] = [item]
        with self.assertRaisesRegex(ValueError, 'unresolved calibration'):
            self.verify(value, calibration_policies=policies)
        item, policies = self.calibration()
        data = json.loads((self.root / item['path']).read_bytes()); data['binding']['target'] = .7; data['binding']['achieved'] = .7
        item = artifact(self.root, item['id'], item['path'], data, 'calibration'); value['calibration'] = [item]
        with self.assertRaisesRegex(ValueError, 'target/purpose/cell/version'):
            self.verify(value, calibration_policies={item['id']: (policies[item['id']][0], item['sha256'])})

    def test_registered_cell_export_requires_solved_calibration_full_keys_and_receipts(self):
        verify_run_v2(self.run_raw, self.root, self.authority)
        manifest = deepcopy(self.f['manifest'])
        partition = manifest['partitions'][0]
        keys = {}
        for binding in partition['records']:
            i = binding['identity']
            key = full_key(patient=i['patient_id'], scenario=i['cell_id'], namespace=i['namespace'], phase=i['phase'],
                           protocol=i['protocol'], replicate=i['replicate'], time_index=i['time_index'], process=i['process'], stream=i['substream'])
            binding['seed_key_sha256'] = key['key_sha256']; keys[key['key_sha256']] = key
        coverage = deepcopy(self.f['coverage'])
        run_ref = ref(self.run.run_id, digest=sha256(self.run_raw))
        coverage['run_manifest'] = run_ref
        partition['coverage'] = artifact(self.root, 'coverage', partition['coverage']['path'], coverage, 'configuration')
        manifest['run_manifest'] = run_ref
        export = artifact(self.root, manifest['id'], 'exports/v2.json', manifest, 'observed_manifest')
        public = deepcopy(self.f['authority'])
        public.update(manifest_sha256=sha256(self.run_raw), export_sha256=export['sha256'])
        public['partitions'][0].update(coverage_sha256=partition['coverage']['sha256'],
                                     record_key_hashes={b['record_id']: b['seed_key_sha256'] for b in partition['records']})
        public = load(ExportAuthorityV2, public)
        ledger = dict(schema_version='2.0.0', synthetic=True, kind='seed_ledger', contract_version='2.0.0', run_id=self.run.run_id, keys=list(keys.values()))
        value = self.result()
        value.update(status='partial', observed_exports=[export], seed_ledger=artifact(self.root, 'seed-ledger-v2', 'seeds/v2.json', ledger, 'seed_ledger'),
                     completion_receipts=partition['completion_receipts'])
        def admit(value, **kwargs):
            raw = canonical(value)
            return verify_result_v2(raw, self.root, self.run, self.authority, sha256(raw), export_authorities={export['id']: public}, **kwargs)
        with self.assertRaisesRegex(ValueError, 'registered calibrated cell'):
            admit(value)
        item, policies = self.calibration(); value['calibration'] = [item]
        self.assertEqual(len(admit(value, calibration_policies=policies)[1]), 1)
        bad = deepcopy(value); bad['completion_receipts'] = []
        with self.assertRaisesRegex(ValueError, 'completion receipts differ'):
            admit(bad, calibration_policies=policies)
        bad = deepcopy(value); bad['completion_receipts'] *= 2
        with self.assertRaisesRegex(ValueError, 'duplicate result completion receipt'):
            admit(bad, calibration_policies=policies)
        bad = deepcopy(value); bad['status'] = 'complete'; bad['reason'] = None
        with self.assertRaisesRegex(ValueError, 'complete qualified exports'):
            admit(bad, calibration_policies=policies)
        bad = deepcopy(value); other = deepcopy(ledger); other['keys'][0] = full_key(patient='outside-run', scenario=self.run.units[0].cell_id)
        bad['seed_ledger'] = artifact(self.root, 'wrong-seeds', 'seeds/wrong.json', other, 'seed_ledger')
        with self.assertRaisesRegex(ValueError, 'seed patient outside'):
            admit(bad, calibration_policies=policies)


if __name__ == '__main__':
    unittest.main()
