"""Real-wire regression cases for the independent ceb5 review's two P2 findings."""
from copy import deepcopy
from datetime import timedelta
from pathlib import Path
import tempfile
import unittest

from observed_v2_fixtures import build, canonical, ORIGIN
from contracts.runs.admission_v2 import validate_partition_record, verify_export_v2
from contracts.runs.observed_v2 import ExportAuthorityV2

FIXTURE_SOURCE = Path(__file__).with_name('observed_v2_fixtures.py')
NEEDLE = '    cutoff = cutoff or ORIGIN + timedelta(days=1, hours=10)'


def variant(root, *, extra='', replace=None, **kwargs):
    source = FIXTURE_SOURCE.read_text(encoding='utf-8')
    if replace:
        for before, after in replace:
            assert before in source
            source = source.replace(before, after)
    assert source.count(NEEDLE) == 1
    source = source.replace(NEEDLE, extra + NEEDLE)
    namespace = {}
    exec(compile(source, 'independently-mutated-wire-fixture', 'exec'), namespace)
    return namespace['build'](root, **kwargs)


def admit(fixture, root):
    return verify_export_v2(fixture['raw'], root, ExportAuthorityV2.model_validate_json(canonical(fixture['authority'])))


def report_extra(day, *, version='2.0.0', available_day=None, missing=False):
    return ("    add('daily_report', ORIGIN+timedelta(days=" + str(day) + ",hours=7), version='" + version + "', process='diary_report', "
            "substream='extra-report', recorded_at=(ORIGIN+timedelta(days=" + str(day) + ",hours=8,minutes=1)).isoformat(), "
            "available_at=(ORIGIN+timedelta(days=" + str(available_day if available_day is not None else day) + ",hours=8,minutes=1)).isoformat(), "
            "sleep_quality=" + ('None' if missing else '6.0') + ", function=" + ('None' if missing else '5.0') + ", adverse_symptoms=[], "
            "diary_sleep_minutes=" + ('None' if missing else '400.0') + ", goals=[], burden=None, missingness='" + ('missing' if missing else 'observed') + "')\n")


def review_extra(run='run_id', partition='partition_id', day=2):
    return ("    add('hold_review_evidence', ORIGIN+timedelta(days=" + str(day) + "), version='2.0.0', process='hold_review', substream='standalone', "
            "run_id=" + run + ", partition_id=" + partition + ", hold_episode_id='episode', evidence_type='review', rule=ref('wire-review-rule'), "
            "requirement=ref('wire-review-requirement'), actor_id='sim-owner', actor_role='simulated_clinician', origin='simulation', "
            "ownership_ref=exact_ref(patient).model_dump(), assessed_at=(ORIGIN+timedelta(days=" + str(day) + ")).isoformat(), facts_refs=[], "
            "finding='wire-only later review', review_result='pending', follow_up_refs=[])\n")


class ObservedV2RepairTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_enclosing_run_partition_rejects_consistent_foreign_hold_chain_and_standalone_reviews(self):
        admit(build(self.root / 'positive', hold=True), self.root / 'positive')
        needle = 'run_id=run_id, partition_id=partition_id, hold_episode_id='
        self.assertEqual(FIXTURE_SOURCE.read_text(encoding='utf-8').count(needle), 2)
        for field in ['run', 'partition', 'both']:
            target = self.root / field
            replacement = "run_id=" + ("'foreign-run'" if field in ['run', 'both'] else 'run_id')
            replacement += ", partition_id=" + ("'foreign-partition'" if field in ['partition', 'both'] else 'partition_id') + ', hold_episode_id='
            wire = variant(target, replace=[(needle, replacement)], hold=True)
            with self.subTest(chain=field), self.assertRaisesRegex(ValueError, 'embedded record run/partition'):
                admit(wire, target)
        # Even an unreferenced review is checked. Hash-consistent stale/admin
        # records cannot escape the containing boundary by avoiding a bundle.
        for run, partition in [('run_id', 'partition_id'), ("'foreign-run'", 'partition_id'), ('run_id', "'foreign-partition'")]:
            target = self.root / ('review-' + str(len(list(self.root.iterdir()))))
            wire = variant(target, extra=review_extra(run, partition), cutoff=ORIGIN + timedelta(days=3))
            if run == 'run_id' and partition == 'partition_id':
                admit(wire, target)
            else:
                with self.assertRaisesRegex(ValueError, 'embedded record run/partition'):
                    admit(wire, target)

    def test_generation_horizon_rejects_new_reports_v1_v2_missing_and_equivalent_observations(self):
        cutoff = ORIGIN + timedelta(days=88, hours=10)
        for version, missing in [('2.0.0', False), ('1.0.0', False), ('2.0.0', True)]:
            target = self.root / (version + str(missing))
            wire = variant(target, extra=report_extra(85, version=version, missing=missing), cutoff=cutoff)
            with self.subTest(version=version, missing=missing), self.assertRaisesRegex(ValueError, 'generated event outside'):
                admit(wire, target)
        for kind, extra in {
            'pain': "    add('observation', ORIGIN+timedelta(days=85,hours=8), identifier='out-of-horizon-pain', measure=dict(concept='pain', value=1.0, unit='dimensionless', observed_at=(ORIGIN+timedelta(days=85,hours=8)).isoformat(), available_at=(ORIGIN+timedelta(days=85,hours=8)).isoformat()), lab_reference_context=None)\n",
            'state': "    snapshot('out-of-horizon-state', ORIGIN+timedelta(days=85,hours=9))\n",
            'early': report_extra(-15),
        }.items():
            target = self.root / kind
            wire = variant(target, extra=extra, cutoff=cutoff)
            with self.subTest(kind=kind), self.assertRaisesRegex(ValueError, 'generated event outside'):
                admit(wire, target)

    def test_delayed_day84_report_correction_and_later_administrative_review_remain_valid(self):
        target = self.root / 'late'
        extra = report_extra(84, available_day=87).replace("    add(", "    delayed = add(", 1)
        extra += "    add('daily_report', delayed.event_at, version='2.0.0', process='diary_report', substream='extra-report', revision=2, supersedes=delayed.record_id, lineage_id=delayed.lineage_id, recorded_at=(ORIGIN+timedelta(days=88)).isoformat(), available_at=(ORIGIN+timedelta(days=89)).isoformat(), sleep_quality=7.0, function=5.0, adverse_symptoms=[], diary_sleep_minutes=500.0, goals=[], burden=None, missingness='observed')\n"
        wire = variant(target, extra=extra + review_extra(day=86), cutoff=ORIGIN + timedelta(days=90))
        _, partitions = admit(wire, target)
        report = next(r for r in partitions[0][1].records if r.kind == 'daily_report' and r.event_at == ORIGIN + timedelta(days=84, hours=7))
        self.assertEqual(report.available_at, ORIGIN + timedelta(days=87, hours=8, minutes=1))
        # The bound is local calendar time, not UTC date or arrival timestamp.
        schedule = wire['schedule'].model_copy(update={'timezone': 'America/Los_Angeles'})
        data = report.model_dump(mode='json')
        from contracts.domain.observed_v2 import RECORD_ADAPTER_V2
        data.update(event_at=(ORIGIN + timedelta(days=85, hours=6, minutes=59)).isoformat(), recorded_at=(ORIGIN + timedelta(days=85, hours=8)).isoformat())
        local_day84 = RECORD_ADAPTER_V2.validate_json(canonical(data))
        self.assertEqual(validate_partition_record(local_day84, schedule, 'obs2-fixture-run', 'obs2-partition'), 84)
        data['event_at'] = (ORIGIN + timedelta(days=85, hours=8)).isoformat()
        with self.assertRaisesRegex(ValueError, 'generated event outside'):
            validate_partition_record(RECORD_ADAPTER_V2.validate_json(canonical(data)), schedule, 'obs2-fixture-run', 'obs2-partition')

    def test_actual_private_result_rejects_day85_even_with_correct_full_seed_key(self):
        from test_private_v2 import PrivateV2Tests
        from fixtures import artifact, full_key, load
        from contracts.runs.common import sha256
        from contracts.runs.observed_v2 import ObservedExportV2
        from contracts.runs.private_v2 import SeedLedgerV2, validate_record_keys, verify_result_v2
        helper = PrivateV2Tests()
        helper.setUp()
        try:
            cutoff = ORIGIN + timedelta(days=88, hours=10)
            helper.data.update(cutoff=cutoff.isoformat(), created_at=cutoff.isoformat())
            helper.bind_run()
            item, policies = helper.calibration()
            for day in [84, 85]:
                wire = variant(helper.root, extra=report_extra(day, available_day=87), cutoff=cutoff, cell_id='S23.MAR_20.n60',
                               registry=helper.data['source_registry'], transform=helper.data['transformation_registry'])
                manifest = deepcopy(wire['manifest']); partition = manifest['partitions'][0]
                keys = {}
                for binding in partition['records']:
                    i = binding['identity']
                    key = full_key(patient=i['patient_id'], scenario=i['cell_id'], namespace=i['namespace'], phase=i['phase'],
                                   protocol=i['protocol'], replicate=i['replicate'], time_index=i['time_index'], process=i['process'], stream=i['substream'])
                    binding['seed_key_sha256'] = key['key_sha256']; keys[key['key_sha256']] = key
                run_ref = dict(id=helper.run.run_id, version='2.0.0', sha256=sha256(helper.run_raw))
                coverage = deepcopy(wire['coverage']); coverage['run_manifest'] = run_ref
                partition['coverage'] = artifact(helper.root, 'coverage', partition['coverage']['path'], coverage, 'configuration')
                manifest['run_manifest'] = run_ref
                export = artifact(helper.root, manifest['id'], 'exports/repair-v2.json', manifest, 'observed_manifest')
                public = deepcopy(wire['authority'])
                public.update(manifest_sha256=sha256(helper.run_raw), export_sha256=export['sha256'])
                public['partitions'][0].update(coverage_sha256=partition['coverage']['sha256'], record_key_hashes={b['record_id']: b['seed_key_sha256'] for b in partition['records']})
                ledger = dict(schema_version='2.0.0', synthetic=True, kind='seed_ledger', contract_version='2.0.0', run_id=helper.run.run_id, keys=list(keys.values()))
                value = helper.result()
                value.update(status='partial', observed_exports=[export], seed_ledger=artifact(helper.root, 'repair-seeds', 'seeds/repair.json', ledger, 'seed_ledger'),
                             calibration=[item], completion_receipts=partition['completion_receipts'])
                raw = canonical(value)
                authority = load(ExportAuthorityV2, public)
                def result():
                    return verify_result_v2(raw, helper.root, helper.run, helper.authority, sha256(raw), export_authorities={export['id']: authority}, calibration_policies=policies)
                def private_keys():
                    return validate_record_keys(helper.run, load(ObservedExportV2, manifest).partitions[0], wire['history'], load(SeedLedgerV2, ledger), wire['schedule'])
                if day == 84:
                    self.assertEqual(len(result()[1]), 1)
                    self.assertTrue(private_keys())
                else:
                    with self.assertRaisesRegex(ValueError, 'generated event outside'):
                        result()
                    with self.assertRaisesRegex(ValueError, 'generated event outside'):
                        private_keys()
        finally:
            helper.tearDown()

    def test_complete_85_decision_wire_keeps_day85_undefined_administrative_endpoint(self):
        wire = build(self.root, complete=True)
        manifest, partitions = admit(wire, self.root)
        self.assertEqual(manifest.status, 'complete')
        history = partitions[0][1]
        decisions = sorted((r for r in history.records if r.kind == 'support_decision'), key=lambda r: r.decision_index)
        self.assertEqual([r.decision_index for r in decisions], list(range(85)))
        final = wire['links'][84]
        self.assertEqual(final.assessment_at, ORIGIN + timedelta(days=85, hours=7))
        self.assertEqual(final.reward.status, 'undefined')
        self.assertEqual(final.reward.reason, 'outside_generated_horizon')
        self.assertIsNone(final.reward.report_ref)
        self.assertEqual(len([r for r in history.records if r.kind == 'daily_report']), 84)
        self.assertTrue(all(r.event_at < ORIGIN + timedelta(days=85) for r in history.records if r.kind == 'daily_report'))
        self.assertEqual(len(wire['manifest']['partitions'][0]['stage_ledgers']), 170)


if __name__ == '__main__':
    unittest.main()
