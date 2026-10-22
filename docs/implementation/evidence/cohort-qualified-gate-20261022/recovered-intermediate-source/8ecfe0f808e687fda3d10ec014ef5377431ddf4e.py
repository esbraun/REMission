"""Scientific admission controls; public genuine input, no fitting evidence."""
import copy
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
import unittest
import uuid

from contracts.domain.analysis import canonical, sha
from contracts.domain.borrowing import SourceBundle
from contracts.domain.cohort import (CohortHistory, CohortInput, CohortResult,
    make_cohort_input, require_executable)

ROOT=Path(__file__).resolve().parents[2]
PUBLIC_INPUT=ROOT/'tests/integration/replay/fixtures/cohort-qualified-day14-input.json'


def qualified_input():
    return CohortInput.model_validate_json(PUBLIC_INPUT.read_bytes())


def changed_cohort(mutate):
    """Rehash all scientific bindings so negatives test admission, not parsing."""
    value=qualified_input().cohort.model_dump(mode='json')
    mutate(value)
    for member,history in zip(value['manifest']['members'],value['histories'],strict=True):
        member['history_sha256']=sha(history)
        member['provenance_sha256']=sha(history['provenance'])
    value['manifest_sha256']=sha(value['manifest'])
    cohort=CohortHistory.model_validate_json(canonical(value))
    return make_cohort_input(cohort,'analysis-'+uuid.uuid4().hex)


def failure_result(product):
    """Explicit no-fit envelope, used only with isolated structural test rows."""
    manifest=product.cohort.manifest
    return CohortResult.model_validate(dict(schema_version='3.0.0',synthetic=True,
        kind='poc_visit_cohort_result',attempt_id=product.attempt_id,
        input_sha256=sha(product.model_dump(mode='json')),cohort_sha256=product.cohort_sha256,
        manifest=manifest,manifest_sha256=product.cohort.manifest_sha256,
        source_set_sha256=product.source_set_sha256,configuration=product.request.configuration,
        estimand=product.request.context.estimand,status='failed',reason='STRUCTURAL-NO-FIT',
        patients=[dict(patient_id=m.patient_id,history_sha256=m.history_sha256,status='failed',
            reason='STRUCTURAL-NO-FIT',effect=None,diagnostics={}) for m in manifest.members],
        diagnostics={},artifacts=[],limitations=['Structural control; no fit ran.']))


class ScientificQualificationControls(unittest.TestCase):
    def test_public_source_and_ordinary_independent_attempts(self):
        raw=PUBLIC_INPUT.read_bytes()
        self.assertEqual(__import__('hashlib').sha256(raw).hexdigest(),
            '0be1e829af83456980639e7c93553f30abfda13925d8cd40733665423b29c044')
        original=qualified_input()
        require_executable(original)
        products=[make_cohort_input(original.cohort,'analysis-'+uuid.uuid4().hex) for _ in range(2)]
        for product in products:require_executable(product)
        self.assertNotEqual(products[0].attempt_id,products[1].attempt_id)
        self.assertNotEqual(products[0].numerical_seeds,products[1].numerical_seeds)
        self.assertNotEqual(sha(products[0].model_dump(mode='json')),sha(products[1].model_dump(mode='json')))
        self.assertEqual(products[0].cohort,original.cohort)

    def test_fully_rehashed_scientific_mutations_remain_unqualified(self):
        def provenance(value):
            history=value['histories'][0]
            for record in (history['records'][0],history['provenance'][0]):
                record['recorded_at']=record['available_at']='2026-01-01T11:59:01Z'
        def day42(value):
            value['manifest']['cutoff']='2026-02-12T12:00:00Z'
            for history in value['histories']:
                history['cutoff']=value['manifest']['cutoff']
                origin=datetime.fromisoformat(history['origin'].replace('Z','+00:00'))
                # Explicit synthetic contract control only: extend the complete
                # clock/grid, so a valid typed day42 input reaches qualification.
                examples={kind:next(r for r in reversed(history['records']) if r['kind']==kind)
                    for kind in ('daily_report','delivery','isi')}
                for day in range(15,43):
                    for kind in ('daily_report','delivery',*(['isi'] if day%14==0 else [])):
                        record=copy.deepcopy(examples[kind])
                        event=origin+timedelta(days=day,minutes=-1) if kind!='delivery' else origin+timedelta(days=day-1,hours=8)
                        record.update(record_id=record['record_id']+'-control-'+str(day),
                            lineage_id=record['lineage_id']+'-control-'+str(day),
                            event_at=event.isoformat(),recorded_at=event.isoformat(),available_at=event.isoformat())
                        if kind=='daily_report':record.update(sleep_quality=None,missingness='missing')
                        if kind=='isi':
                            end=origin+timedelta(days=day,hours=-1)
                            record.update(recall_end=end.isoformat(),recall_start=(end-timedelta(days=14)).isoformat())
                        history['records'].append(record)
                        history['provenance'].append({k:v for k,v in record.items() if k in history['provenance'][0]})
        def interactive(value):
            value['manifest'].update(scope='interactive',research_run_id=None,research_execution=None)
        changes=dict(observation=lambda v:v['histories'][0]['records'][0].update(total=19),
            provenance=provenance,version=lambda v:v['manifest']['members'][0].update(patient_version=20),
            wrong_run=lambda v:v['manifest'].update(research_run_id='unqualified-run'),
            wrong_cohort=lambda v:v['manifest'].update(cohort_id='unqualified-cohort'),
            wrong_owner=lambda v:v['manifest'].update(owner_id='other'),
            wrong_panel=lambda v:v['manifest'].update(panel_id='other'),
            fixture=lambda v:v['manifest'].update(research_execution='contract_fixture'),
            interactive=interactive,day42=day42)
        for name,mutate in changes.items():
            with self.subTest(name=name):
                product=changed_cohort(mutate)
                with self.assertRaises(ValueError):require_executable(product)

    def test_v1_sources_and_invalid_copies_do_not_enter_tuple(self):
        product=qualified_input()
        source=SourceBundle.model_validate_json((ROOT/'services/foundation/studies/source-7c97862d.json').read_bytes())
        borrowed=make_cohort_input(product.cohort,'analysis-'+uuid.uuid4().hex,source)
        with self.assertRaises(ValueError):require_executable(borrowed)
        for changed in [product.model_copy(update={'cohort_sha256':'0'*64}),
                product.model_copy(update={'source_set_sha256':'0'*64}),
                product.model_copy(update={'sources':source})]:
            with self.assertRaises(ValueError):require_executable(changed)
        forged=copy.deepcopy(product)
        forged.cohort.histories[0].records[0].total=19
        with self.assertRaises(ValueError):require_executable(forged)

    def test_result_or_caller_lookalike_cannot_satisfy_input_predicate(self):
        product=qualified_input()
        for envelope in [failure_result(product),product.model_dump(mode='json'),
                SimpleNamespace(cohort=product.cohort,cohort_sha256=product.cohort_sha256),None]:
            with self.assertRaisesRegex(ValueError,'typed original input'):require_executable(envelope)


if __name__=='__main__':unittest.main()
