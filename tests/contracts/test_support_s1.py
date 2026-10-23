"""Changed S1 scalar contracts, adapter identity and closed old branches."""
import ast
import copy
from dataclasses import make_dataclass
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tooling/foundation'))
from support_s1_fixtures import product,abstention,HOST,completed_gate_fixture
from contracts.domain.analysis import canonical,sha
from contracts.domain.borrowing import parse_input,parse_result
from contracts.domain.support_s1 import (S1Input,S1Result,S1Submission,CONFIG_REF,OFFLINE_SETTINGS,OFFLINE_REF,
    S1_ESTIMAND,WCLS_PRIOR_REF,LAW_REF,SUPPORT_REF,
    feature_history_sha,validate_result,execution_binding,validate_summary)
from contracts.domain.protocol_request import require_executable
from services.learner.support_s1_worker import feature_histories
from analysis_dispatcher import require_dispatchable,worker_module


class S1Contracts(unittest.TestCase):
    def test_new_discriminator_and_file_adapter_preserve_exact_active_values(self):
        p=product();self.assertIsInstance(parse_input(p.model_dump_json()),S1Input)
        require_executable(p);require_dispatchable(p.model_dump(mode='json'))
        self.assertEqual(worker_module(p.model_dump()),'services.learner.support_s1_worker')
        public=make_dataclass('PublicHistory','patient_id origin cutoff records'.split())
        actual=feature_histories(p,public)
        self.assertEqual([tuple(h.records) for h in p.histories],[h.records for h in actual])
        expected=sha([dict(patient_id=h.patient_id,origin=h.origin.isoformat(),
            records=[r.model_dump(mode='json') for r in sorted(h.records,key=lambda r:r.record_id)]) for h in actual])
        self.assertEqual(feature_history_sha(p),expected)
        self.assertNotEqual(expected,p.history_sha256)

    def test_offline_settings_are_identical_without_importing_estimator(self):
        tree=ast.parse(Path('methods/support/wcls.py').read_text())
        expression=next(n.value for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='SETTINGS' for t in n.targets))
        # Only the literal dict expression is evaluated; no module or numerical code.
        actual=eval(compile(ast.Expression(expression),'<offline-settings-only>','eval'),{'__builtins__':{},'dict':dict})
        self.assertEqual(OFFLINE_SETTINGS,actual);self.assertFalse(actual['production_activation'])

    def test_schema2_all_purposes_stay_closed(self):
        sys.path.insert(0,str(Path(__file__).resolve().parent))
        from test_protocol_boundary import product as boundary
        for purpose in ('N0','N1','S1-WCLS','S2-refresh'):
            old=boundary(purpose)
            with self.assertRaises(ValueError):require_executable(old)
            with self.assertRaises(ValueError):require_dispatchable(old.model_dump(mode='json'))
            changed=old.model_dump(mode='json');changed['request']['configuration']=CONFIG_REF
            with self.assertRaises(ValueError):parse_input(canonical(changed))
        self.assertEqual(worker_module({'kind':'poc_visit_input'}),'services.learner.analysis_worker')

    def test_wrong_mode_cutoff_configuration_family_member_and_future_record_reject(self):
        original=product().model_dump(mode='json')
        for change in ('mode','cutoff','configuration','family','member','future'):
            value=copy.deepcopy(original)
            if change=='mode':value['mode']='S0'
            elif change=='cutoff':value['cutoff_day']=42
            elif change=='configuration':value['configuration']['sha256']='0'*64
            elif change=='family':value['histories'][0]['family']='nof1_med'
            elif change=='member':value['cohort'][0]['patient_id']='foreign'
            else:value['histories'][0]['records'][0]['available_at']=value['cutoff']
            value['history_sha256']=sha(value['histories'])
            with self.subTest(change=change),self.assertRaises(ValueError):S1Input.model_validate_json(canonical(value))
        for mode,cut in [('S0',14),('S1',13)]:
            with self.assertRaises(ValueError):S1Submission.model_validate_json(canonical(dict(archive_id='archive',mode=mode,cutoff_day=cut,configuration=CONFIG_REF)))

    def test_abstained_failed_and_consumed_host_feature_identities_are_distinct(self):
        p=product();result=abstention(p);trusted=execution_binding(p,HOST)
        self.assertIsInstance(parse_result(result.model_dump_json()),S1Result)
        validate_result(result,p,trusted)
        for status in ('abstained','failed'):
            self.assertIsNone(abstention(p,status=status).output)
        for change in ('consumed','host','feature','run','archive','owner','version'):
            value=result.model_dump(mode='json')
            if change=='consumed':value['consumed_record_ids']=value['consumed_record_ids'][1:]
            elif change=='host':value['diagnostics']['execution']['learner_image']='sha256:'+'0'*64
            elif change=='feature':value['feature_history_sha256']='0'*64
            elif change=='run':value['archive']['run_id']='foreign'
            elif change=='archive':value['archive']['archive_id']='foreign'
            elif change=='owner':value['archive']['owner_id']='bob'
            else:value['cohort'][-1]['patient_version']=2
            with self.subTest(change=change),self.assertRaises(ValueError):
                validate_result(S1Result.model_validate_json(canonical(value)),p,trusted)
        value=result.model_dump(mode='json');value.update(status='completed',reason=None)
        with self.assertRaises(ValueError):S1Result.model_validate_json(canonical(value))

    def test_low_cluster_rank_and_withheld_sensitivity_are_scalar_acceptance_gates(self):
        # Hand-authored scalar gate envelope, never an actual estimate or result.
        from types import SimpleNamespace
        fixture=self.summary_fixture();diagnostic=fixture.diagnostics;output=fixture.output
        validate_summary(fixture)
        for change in ('clusters','rank','sensitivity','covariance'):
            altered=copy.deepcopy(diagnostic)
            if change=='clusters':altered['wcls']['counts']['participants']=7
            elif change=='rank':altered['wcls']['singular_values'][-1]=0.
            elif change=='sensitivity':altered['wcls']['sensitivity_reason']=None
            else:altered['wcls']['covariance'][-1][-1]=2.
            with self.subTest(change=change),self.assertRaises(ValueError):
                validate_summary(SimpleNamespace(diagnostics=altered,feature_history_sha256='0'*64,output=output))

    def summary_fixture(self):
        from types import SimpleNamespace
        value=completed_gate_fixture(product())
        return SimpleNamespace(diagnostics=value['diagnostics'],feature_history_sha256=value['feature_history_sha256'],
            output=SimpleNamespace(**dict(value['output'],interval=tuple(value['output']['interval']))))

    def test_completed_interval_must_match_declared_t_inference(self):
        value=completed_gate_fixture(product())
        self.assertEqual(S1Result.model_validate_json(canonical(value)).status,'completed')
        for change in ('zero-width','wrong-critical','asymmetric','wrong-df'):
            altered=copy.deepcopy(value)
            interval={'zero-width':[.25,.25],'wrong-critical':[-1.71,2.21],
                'asymmetric':[-1.950985160082949,2.3]}.get(change)
            if interval is not None:
                altered['output']['interval']=interval;altered['diagnostics']['wcls']['interval']=interval
            else:
                altered['output']['df']=10;altered['diagnostics']['wcls']['df']=10
                altered['diagnostics']['wcls']['counts']['participants']=11
            with self.subTest(change=change),self.assertRaises(ValueError):
                S1Result.model_validate_json(canonical(altered))

    def test_sensitivity_range_must_equal_the_nine_finite_point_cells(self):
        fixture=self.summary_fixture();w=fixture.diagnostics['wcls']
        cells=[dict(delta0=a,delta1=b,shift=.1*(b-a),estimate=.25+.1*(b-a))
            for a in (-.5,0.,.5) for b in (-.5,0.,.5)]
        w.update(sensitivity_status='available',sensitivity_reason=None,sensitivity=cells,
            sensitivity_range=[.15,.35])
        validate_summary(fixture)
        for interval in ([-999.,999.],[.25,.25],[.15,float('nan')],None):
            w['sensitivity_range']=interval
            with self.subTest(interval=interval),self.assertRaisesRegex(ValueError,'sensitivity range'):
                validate_summary(fixture)
        value=completed_gate_fixture(product());value['diagnostics']=copy.deepcopy(fixture.diagnostics)
        value['diagnostics']['wcls']['sensitivity_range']=[999.,999.]
        with self.assertRaisesRegex(ValueError,'sensitivity range'):
            S1Result.model_validate_json(canonical(value))
        w.update(sensitivity_status='unavailable',sensitivity_reason='missing-only context malformed',
            sensitivity=[],sensitivity_range=[.15,.35])
        with self.assertRaisesRegex(ValueError,'sensitivity range'):
            validate_summary(fixture)

    def test_existing_visit_completion_still_requires_mcmc_and_rollout_diagnostics(self):
        from services.foundation.analysis import ingest,AnalysisError
        # Ingestion rejects this typed visit envelope before touching the Store.
        import tempfile
        from contracts.domain.analysis import CONFIG_REF as VISIT_CONFIG,ESTIMAND_REF
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)
            value=dict(schema_version='1.0.0',synthetic=True,kind='poc_visit_result',attempt_id='visit-fixture',
                input_sha256='a'*64,history_sha256='b'*64,cutoff='2026-01-15T12:00:00Z',
                configuration=VISIT_CONFIG,estimand=ESTIMAND_REF,status='completed',reason=None,
                effect=dict(mean=0.,sd=1.,lower=-2.,upper=2.,unit='ISI_points',kind='conditional_expected_assignment_contrast'),
                diagnostics={},artifacts=[],limitations=['Structural invalid completion only'])
            (path/'result.json').write_text(canonical(value))
            with self.assertRaisesRegex(AnalysisError,'computational diagnostics'):
                ingest(None,'visit-fixture','unused',path)


if __name__=='__main__':unittest.main()
