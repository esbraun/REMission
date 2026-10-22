"""LIGHT-only ownership/lineage/wire tests; no fit or model compilation."""
import copy
import json
from pathlib import Path
import sqlite3
import unittest

from contracts.domain.analysis import AnalysisHistory, canonical, sha
from contracts.domain.borrowing import parse_input, parse_result, SourceBundle
from contracts.domain.cohort import (CohortHistory, CohortResult, make_cohort_input,
    require_executable, COHORT_CONFIG_REF)
from contracts.domain.borrow_runtime import coordinate_layout, cohort_coordinate_layout
from services.foundation.analysis import export_cohort, prepare_cohort, AnalysisError
from services.foundation.store import instant
from services.foundation.workflow import record_header, SUPPORT

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT/'tests/integration/replay/fixtures'


def histories():
    """Renamed existing observed fixture for contract controls, never fit evidence."""
    original = json.loads((FIXTURES/'pa3-legacy-v0-input.json').read_bytes())['history']
    result = []
    for i in range(12):
        value = copy.deepcopy(original)
        patient = f'COHORT-{i:02}'
        value['patient_id'] = patient
        for r in [*value['records'], *value['provenance']]:
            r['patient_id'] = patient
            for key in ('record_id', 'lineage_id', 'supersedes', 'duplicate_of', 'assignment_id'):
                if r.get(key) is not None:
                    r[key] = patient+'-'+r[key]
        result.append(AnalysisHistory.model_validate_json(canonical(value)))
    return result


def database():
    db = sqlite3.connect(':memory:')
    db.row_factory = sqlite3.Row
    db.executescript('CREATE TABLE patients(id TEXT,owner_id TEXT,version INTEGER,state_json TEXT,cutoff TEXT);'
        'CREATE TABLE events(id TEXT,patient_id TEXT,payload TEXT,available_at TEXT,phase INTEGER);'
        'CREATE TABLE state_changes(id TEXT PRIMARY KEY,patient_id TEXT,actor_id TEXT,created_at TEXT,payload TEXT);')
    for h in histories():
        db.execute('INSERT INTO patients VALUES(?,?,?,?,?)', (h.patient_id, 'owner-a', 3,
            canonical(dict(simulation=dict(law_version='poc-longitudinal-v1', panel_id='panel-a'))), h.cutoff.isoformat()))
        for r in h.records:
            record = record_header(r.record_id, h.patient_id, r.event_at)
            record.update(r.model_dump(mode='json'))
            if r.kind != 'assignment':
                record['source'].update(id='poc-longitudinal-v1', adapter='simulation')
            if r.kind == 'isi':
                total = record.pop('total')
                record['items'] = [total//7+int(i < total%7) for i in range(7)]
            elif r.kind == 'daily_report':
                observed = r.sleep_quality is not None
                record.update(function=7. if observed else None, diary_sleep_minutes=400. if observed else None,
                    adverse_symptoms=[], goals=[], burden=0. if observed else None)
            elif r.kind == 'assignment':
                record.update(decision_id='decision-test', approval_id='approval-test', component=None,
                    probability=None, seed=None, support_policy=SUPPORT, patient_blinded=False,
                    clinician_blinded=False, clinician_override=None, override_reason=None)
            db.execute('INSERT INTO events VALUES(?,?,?,?,?)',
                (r.record_id, h.patient_id, canonical(record), r.available_at.isoformat(), 3))
    return db


def export(db):
    return export_cohort(db, 'owner-a', {h.patient_id:3 for h in reversed(histories())},
        histories()[0].cutoff.isoformat(), cohort_id='cohort-a')


class CohortContracts(unittest.TestCase):
    def setUp(self):
        self.db = database()
        self.addCleanup(self.db.close)

    def test_actual_owned_export_binds_all_histories_and_does_not_write(self):
        before = self.db.total_changes
        cohort = export(self.db)
        self.assertEqual(self.db.total_changes, before)
        self.assertEqual([m.patient_id for m in cohort.manifest.members], [h.patient_id for h in histories()])
        self.assertEqual(len({h.patient_id for h in cohort.histories}), 12)
        self.assertEqual(cohort.manifest.owner_id, 'owner-a')
        self.assertEqual(cohort.manifest_sha256, sha(cohort.manifest.model_dump(mode='json')))
        self.assertNotIn('function', cohort.model_dump_json())
        self.assertNotIn('diary_sleep_minutes', cohort.model_dump_json())
        self.assertNotIn('seed', cohort.model_dump_json())
        product = prepare_cohort(self.db, 'owner-a', {h.patient_id:3 for h in histories()},
            histories()[0].cutoff.isoformat(), cohort_id='cohort-a')
        self.assertEqual(product.cohort_sha256, sha(cohort.model_dump(mode='json')))
        self.assertEqual(parse_input(product.model_dump_json()), product)
        self.assertEqual(product.request.configuration.model_dump(), COHORT_CONFIG_REF)
        self.assertNotEqual(product.numerical_seeds.nuts, make_cohort_input(cohort, 'another-attempt').numerical_seeds.nuts)
        with self.assertRaisesRegex(ValueError, 'qualification'):
            require_executable(product)

    def test_owner_version_panel_reached_and_run_rejections(self):
        for statement in ["UPDATE patients SET owner_id='other' WHERE id='COHORT-00'",
                "UPDATE patients SET version=4 WHERE id='COHORT-00'",
                "UPDATE patients SET cutoff='2026-01-02T12:00:00Z' WHERE id='COHORT-00'",
                "UPDATE patients SET state_json='{\"simulation\":{\"law_version\":\"poc-longitudinal-v1\",\"panel_id\":\"other\"}}' WHERE id='COHORT-00'",
                "UPDATE patients SET state_json='{\"simulation\":{\"law_version\":\"poc-longitudinal-v1\",\"panel_id\":\"panel-a\",\"research_run_id\":\"run-a\"}}' WHERE id='COHORT-00'"]:
            with self.subTest(statement=statement):
                self.db.execute('SAVEPOINT negative_control')
                self.db.execute(statement)
                with self.assertRaises(AnalysisError):
                    export(self.db)
                self.db.execute('ROLLBACK TO negative_control')
                self.db.execute('RELEASE negative_control')
        with self.assertRaisesRegex(AnalysisError, 'Registered research-run'):
            export_cohort(self.db, 'owner-a', {h.patient_id:3 for h in histories()},
                histories()[0].cutoff.isoformat(), cohort_id='cohort-a', research_run_id='caller-string')

    def test_member_nested_future_duplicate_and_manifest_tamper_rejected(self):
        product = make_cohort_input(export(self.db), 'attempt-a').model_dump(mode='json')
        for mutate in [lambda v:v['cohort']['histories'][0]['records'][0].update(function=7.),
                lambda v:v['cohort']['histories'][0]['provenance'][0].update(available_at='2099-01-01T00:00:00Z'),
                lambda v:v['cohort']['histories'].__setitem__(1, copy.deepcopy(v['cohort']['histories'][0])),
                lambda v:v['cohort']['manifest']['members'][0].update(patient_version=99),
                lambda v:v.update(source_set_sha256='0'*64),
                lambda v:v['request']['context']['seed'].update(patient='COHORT-00')]:
            value = copy.deepcopy(product)
            mutate(value)
            with self.assertRaises(ValueError):
                parse_input(canonical(value))
        value = export(self.db).model_dump(mode='json')
        # Rehashing alone cannot make a cross-patient repeated provenance ID valid.
        value['histories'][1]['provenance'][0]['record_id'] = value['histories'][0]['provenance'][0]['record_id']
        with self.assertRaises(ValueError):
            CohortHistory.model_validate_json(canonical(value))

    def test_exact_approved_sources_and_legacy_bytes_still_parse(self):
        source = SourceBundle.model_validate_json((ROOT/'services/foundation/studies/source-7c97862d.json').read_bytes())
        product = make_cohort_input(export(self.db), 'attempt-b', source)
        self.assertEqual(parse_input(product.model_dump_json()), product)
        self.assertEqual(len(product.sources.studies), 2)
        self.assertEqual(product.source_set_sha256, source.source_set_sha256)
        for name, parser in [('input', parse_input), ('result', parse_result)]:
            raw = (FIXTURES/f'pa3-legacy-v0-{name}.json').read_bytes()
            self.assertEqual(json.loads(raw), parser(raw).model_dump(mode='json'))
        old = coordinate_layout(histories()[0])
        new = cohort_coordinate_layout(export(self.db), borrowed=True)
        self.assertEqual(old[6]['shape'], [35])
        self.assertEqual(new['layout'][6]['shape'], [376])
        self.assertEqual([r['name'] for r in new['layout'][-2:]], ['source_bias', 'source_tau_log__'])

    def test_abstention_cannot_publish_patient_interval(self):
        cohort = export(self.db)
        value = dict(schema_version='3.0.0', synthetic=True, kind='poc_visit_cohort_result',
            attempt_id='attempt-a', input_sha256='0'*64, cohort_sha256=sha(cohort.model_dump(mode='json')),
            manifest=cohort.manifest.model_dump(mode='json'), manifest_sha256=cohort.manifest_sha256,
            source_set_sha256=None, configuration=COHORT_CONFIG_REF,
            estimand=make_cohort_input(cohort, 'attempt-a').request.context.estimand.model_dump(),
            status='abstained', reason='qualification-unavailable', diagnostics={}, artifacts=[], limitations=[],
            patients=[dict(patient_id=m.patient_id, history_sha256=m.history_sha256, status='abstained',
                reason='qualification-unavailable', effect=None, diagnostics={}) for m in cohort.manifest.members])
        self.assertEqual(parse_result(canonical(value)).status, 'abstained')
        value['patients'][0].update(status='completed', reason=None, effect=dict(mean=0., sd=1., lower=-2., upper=2.,
            unit='ISI_points', kind='conditional_expected_assignment_contrast'))
        with self.assertRaisesRegex(ValueError, 'unaccepted joint fit'):
            CohortResult.model_validate_json(canonical(value))


if __name__ == '__main__':
    unittest.main()
