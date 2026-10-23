"""Scalar schema4 controls. No fitting, scientific imports or app-data claim."""
import ast
import copy
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import unittest

from contracts.domain.analysis import canonical, sha, FIXED_SUPPORT_REF, reference
from contracts.domain.nof1_app import (CONFIG_REFS, CONFIGS, NInput, NResult,
    NSubmission, make_input, readiness, execution_binding, validate_result)
from contracts.domain.nof1_config import CONFIG_REFS as PROPOSAL_REFS, configuration
from contracts.domain.protocol import NOF1_REF
from contracts.domain.protocol_analysis import ProtocolHistory, ReducedHeader


def scalar_fixture(patient='N-PATIENT-A', **kwargs):
    # Reuse only the two stdlib/scalar fixture definitions from the qualified
    # reader tests. Their module imports NumPy, so do not import that module.
    source=Path('tests/methods/test_nof1_data.py').read_text(encoding='utf-8')
    definitions=[n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef)
        and n.name in ('fixture','parsed')]
    namespace=dict(ORIGIN=datetime(2026,1,1,12,tzinfo=timezone.utc),timedelta=timedelta,
        sha=sha,FIXED_SUPPORT_REF=FIXED_SUPPORT_REF,NOF1_REF=NOF1_REF,
        ProtocolHistory=ProtocolHistory,ReducedHeader=ReducedHeader)
    exec(compile(ast.Module(body=definitions,type_ignores=[]),'<scalar-N-fixture>','exec'),namespace)
    return namespace['fixture'](patient,**kwargs)


def product(*,target='N-PATIENT-B',purpose='N1',histories=None):
    histories=histories or [scalar_fixture('N-PATIENT-A'),scalar_fixture('N-PATIENT-B')]
    return make_input(histories,purpose=purpose,attempt_id='analysis-structural-n',
        owner_id='alice',cohort_id='explicit-panel',generation_id='generation-structural',
        run=reference('structural-N-run',{'generation':'structural-only'}),
        target_id=target,patient_versions={h.patient_id:1 for h in histories},fit_seed=9157)


class NAppContract(unittest.TestCase):
    def test_schema4_separate_from_unchanged_nonexecutable_proposals(self):
        p=product()
        self.assertEqual(p.schema_version,'4.0.0')
        for purpose in ('N0','N1'):
            self.assertFalse(configuration(purpose)['executable'])
            self.assertNotEqual(CONFIG_REFS[purpose],PROPOSAL_REFS[purpose])
            self.assertEqual(CONFIGS[purpose]['settings'],configuration(purpose))

    def test_target_is_explicit_nonfirst_member_and_seed_bound(self):
        p=product()
        self.assertEqual(p.target_id,'N-PATIENT-B')
        value=p.model_dump(mode='json');value['target_id']='N-PATIENT-A'
        with self.assertRaisesRegex(ValueError,'target/run/cutoff/seed'):
            NInput.model_validate_json(canonical(value))
        with self.assertRaises(ValueError):product(target='not-a-member')

    def test_same_data_for_N0_N1_but_distinct_configuration(self):
        a,b=product(purpose='N0'),product(purpose='N1')
        self.assertEqual(a.histories,b.histories)
        self.assertEqual(a.history_sha256,b.history_sha256)
        self.assertNotEqual(a.request.configuration,b.request.configuration)
        self.assertNotEqual(a.request.context.seed.process,b.request.context.seed.process)

    def test_all_member_hashes_order_and_cutoff_are_validated(self):
        p=product().model_dump(mode='json')
        for mutate in (lambda v:v['cohort'][0].update(history_sha256='0'*64),
                lambda v:v['cohort'][0].update(provenance_sha256='0'*64),
                lambda v:v['histories'].reverse(),
                lambda v:v['histories'][0].update(cutoff='2026-02-07T12:00:00Z')):
            value=copy.deepcopy(p);mutate(value)
            with self.assertRaises(ValueError):NInput.model_validate_json(canonical(value))

    def test_arm_gate_belongs_to_target_sparse_peer_remains_valid(self):
        sparse=scalar_fixture('N-PATIENT-A',arms=('MED_A',)*4)
        p=product(histories=[sparse,scalar_fixture('N-PATIENT-B')])
        self.assertEqual(readiness(p.histories,p.target_id)['status'],'eligible')
        self.assertEqual(readiness(p.histories,'N-PATIENT-A')['status'],'inconclusive')

    def test_relative_review_not_origin_day_and_early_is_unavailable(self):
        delayed=scalar_fixture(start=7)
        self.assertEqual(readiness([delayed],delayed.patient_id)['review_day'],36)
        early=scalar_fixture(review=27)
        self.assertEqual(readiness([early],early.patient_id)['status'],'unavailable')
        with self.assertRaises(ValueError):product(histories=[delayed,scalar_fixture('N-PATIENT-B',review=27)])

    def test_unknown_duplicate_or_missing_exposure_rejected(self):
        for mutate in ('unknown','duplicate','missing'):
            h=scalar_fixture().model_dump(mode='python')
            r=next(r for r in h['records'] if r['kind']=='delivery' and r['option']=='MED_A')
            if mutate=='unknown':r.update(stage='delivered',adherence=None)
            if mutate=='duplicate':
                extra=copy.deepcopy(r);extra.update(record_id='duplicate-exposure',lineage_id='duplicate-exposure')
                h['records'].append(extra)
            if mutate=='missing':h['records'].remove(r)
            h['provenance']=[{k:r[k] for k in ReducedHeader.model_fields} for r in h['records']]
            with self.assertRaises(ValueError):
                parsed=ProtocolHistory.model_validate(h);readiness([parsed],parsed.patient_id)

    def test_submission_rejects_wrong_configuration_or_unselected_target(self):
        p=product();value=dict(purpose='N1',target_id=p.target_id,cohort_id=p.cohort_id,
            patient_versions={m.patient_id:m.patient_version for m in p.cohort},
            cutoff=p.cutoff.isoformat(),configuration=CONFIG_REFS['N1'])
        self.assertEqual(NSubmission.model_validate_json(canonical(value)).target_id,p.target_id)
        value['configuration']=PROPOSAL_REFS['N1']
        with self.assertRaises(ValueError):NSubmission.model_validate_json(canonical(value))

    def test_host_binding_preserves_exact_source_image_and_input(self):
        p=product();host=dict(source_commit='a'*40,learner_image='sha256:'+'b'*64)
        binding=execution_binding(p,host)
        self.assertEqual(binding['input_sha256'],sha(p.model_dump(mode='json')))
        self.assertEqual(binding['source_commit'],host['source_commit'])
        with self.assertRaises(ValueError):execution_binding(p,dict(host,learner_image='latest'))

    def test_closed_boundary_cannot_be_admitted_as_schema4(self):
        from contracts.domain.protocol_request import make_boundary_input, require_executable
        p=product();closed=make_boundary_input(p.histories,'N1','boundary',p.run.model_dump(),
            p.request.context.seed.model_dump())
        with self.assertRaises(ValueError):require_executable(closed)
        with self.assertRaises(ValueError):NInput.model_validate_json(closed.model_dump_json())

    def test_no_scientific_modules_loaded(self):
        self.assertFalse({'numpy','pymc','pytensor','arviz','arviz_stats','scipy','statsmodels'}.intersection(sys.modules))


if __name__=='__main__':unittest.main()
