"""P1 recursive isolation, strict purpose identities and admission negatives."""
import copy
import json
import sqlite3
import tempfile
from datetime import timedelta
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tooling/foundation'))
from protocol_fixtures import ORIGIN,PATIENT,full_history,history,perturb_forbidden,snapshot_history,typed
from contracts.domain.analysis import canonical,reference,sha
from contracts.domain.borrowing import parse_input,parse_result
from contracts.domain.protocol import RECORD_ADAPTER_V21,SupportDecisionV21
from contracts.domain.protocol_request import (BOUNDARY_CONFIG_REF,EXECUTABLE_CONFIGURATIONS,IDENTITIES,
    N_PRIOR_REF,ProtocolInput,ProtocolResult,WCLS_PRIOR_REF,make_boundary_input,require_executable)
from services.foundation.protocol import project_protocol
from analysis_dispatcher import require_dispatchable


def reduced(family='support',recursive=True):
    full=full_history(family=family,recursive=recursive)
    return project_protocol(full,ORIGIN+timedelta(days=2),family=family,origin=ORIGIN)


def product(purpose='S1-WCLS'):
    family=IDENTITIES[purpose]['family'];h=reduced(family,recursive=family=='support')
    run=reference('p1-boundary-run','schema-and-isolation-only; not a numerical run')
    seed=dict(namespace='fit',protocol=h.protocol.id,scenario=run['id'],replicate=0,patient=PATIENT,time_index=2,
        process='wcls-unused-provenance' if purpose=='S1-WCLS' else purpose+'-fit')
    return make_boundary_input([h],purpose,'analysis-p1-boundary',run,seed)


class ProtocolBoundaryTests(unittest.TestCase):
    def test_recursive_forbidden_full_audit_perturbations_do_not_change_hstar(self):
        for family in ['nof1_med','support']:
            full=full_history(family=family,recursive=family=='support')
            changed=perturb_forbidden(full,isi=family=='support')
            self.assertNotEqual(sha(full.model_dump(mode='json')),sha(changed.model_dump(mode='json')))
            before=project_protocol(full,ORIGIN+timedelta(days=2),family=family,origin=ORIGIN)
            after=project_protocol(changed,ORIGIN+timedelta(days=2),family=family,origin=ORIGIN)
            self.assertEqual(before,after)
            text=canonical(before.model_dump(mode='json'))
            for forbidden in ['"function"','"diary_sleep_minutes"','"raw_sha256"','"payload_sha256"','"source"','"seed"','"simulation"']:
                self.assertNotIn(forbidden,text)
            self.assertEqual(any(r.kind=='isi' for r in before.records),family=='nof1_med')
        # N explicitly retains scheduled ISI; changing it must change N H*.
        full=full_history(family='nof1_med',recursive=False)
        self.assertNotEqual(project_protocol(full,ORIGIN+timedelta(days=2),family='nof1_med',origin=ORIGIN),
            project_protocol(perturb_forbidden(full,isi=True),ORIGIN+timedelta(days=2),family='nof1_med',origin=ORIGIN))

    def test_exact_hash_owner_temporal_and_stale_lineage_negatives(self):
        full=full_history();values=[r.model_dump(mode='json') for r in full.records]
        # A changed full report without legitimately refreshed exact audit refs
        # cannot be laundered by the reducer even when its allowed quality agrees.
        changed=copy.deepcopy(values)
        report=next(r for r in changed if r['kind']=='daily_report' and r['record_id'].endswith('-1'))
        report['function']=1.
        with self.assertRaises(ValueError):project_protocol(history(changed),ORIGIN+timedelta(days=2),family='support',origin=ORIGIN)
        foreign=copy.deepcopy(values);foreign[0]['patient_id']='foreign-owner-patient'
        with self.assertRaises(ValueError):history(foreign)
        late=copy.deepcopy(values)
        report=next(r for r in late if r['kind']=='daily_report' and r['record_id'].endswith('-1'))
        report['available_at']=(ORIGIN+timedelta(days=1)).isoformat()
        late_history=history(late)
        with self.assertRaises(ValueError):project_protocol(late_history,ORIGIN+timedelta(days=2),family='support',origin=ORIGIN)
        # A correction makes a saved exact dependency stale; never redirect it.
        old=next(r for r in values if r['kind']=='daily_report' and r['record_id'].endswith('-1'))
        correction=copy.deepcopy(old);correction.update(record_id='quality-correction',revision=2,supersedes=old['record_id'],record_status='corrected',
            recorded_at=(ORIGIN+timedelta(days=1,minutes=1)).isoformat(),available_at=(ORIGIN+timedelta(days=1,minutes=1)).isoformat())
        with self.assertRaises(ValueError):project_protocol(history([*values,correction]),ORIGIN+timedelta(days=2),family='support',origin=ORIGIN)

    def test_snapshot_approval_consent_background_and_freeze_refs(self):
        full=snapshot_history()
        projected=project_protocol(full,ORIGIN+timedelta(days=2),family='nof1_med',origin=ORIGIN)
        self.assertTrue(any(r.kind=='protocol_snapshot' for r in projected.records))
        for kind,field,value in [('consent','consent_status','missing'),('approval','expected_patient_version',2),('assignment','option','behavioral_escalate')]:
            changed=[r.model_dump(mode='json') for r in full.records]
            record=next(r for r in changed if r['kind']==kind)
            record[field]=value
            with self.assertRaises(ValueError):project_protocol(history(changed),ORIGIN+timedelta(days=2),family='nof1_med',origin=ORIGIN)

    def test_support_clinical_intersection_policy_and_canonical_mrt_probability(self):
        base=next(r for r in full_history().records if r.kind=='support_decision').model_dump(mode='json')
        eligible=[dict(action=a,status='eligible',reasons=[]) for a in ['support_prompt','no_prompt']]
        randomized=base|dict(mode='mrt',availability='randomized',unavailable_reasons=[],eligibility=eligible,
            probabilities=dict(support_prompt=.5,no_prompt=.5),assignment_id='assignment-support')
        self.assertEqual(typed(randomized).probabilities['support_prompt'],.5)
        fixed=randomized|dict(mode='fixed',availability='deterministic',probabilities=dict(support_prompt=0.,no_prompt=1.),
            policy_constraint=dict(allowed_actions=['no_prompt'],reason='fixed_no_prompt',snapshot_ref=dict(record_id='exact-frozen-snapshot',payload_sha256='a'*64)))
        self.assertEqual(typed(fixed).eligibility[0].status,'eligible')
        excluded=[dict(action=a,status='excluded',reasons=['hold']) for a in ['support_prompt','no_prompt']]
        self.assertEqual(typed(fixed|dict(mode='paused',availability='unavailable',eligibility=excluded,
            probabilities=dict(support_prompt=0.,no_prompt=0.),assignment_id=None,unavailable_reasons=['hold'])).availability,'unavailable')
        for changed in [randomized|dict(probabilities=dict(support_prompt=.2,no_prompt=.8)),
                        fixed|dict(policy_constraint=randomized['policy_constraint']),
                        fixed|dict(eligibility=excluded),fixed|dict(availability='randomized')]:
            with self.assertRaises(ValueError):typed(changed)

    def test_2_1_only_dispatch_unknown_versions_and_cross_version_lineage(self):
        from services.foundation.workflow import history as stored_history
        from services.learner.export_observed import admit
        record=next(r for r in full_history().records if r.kind=='support_decision').model_dump(mode='json')
        with sqlite3.connect(':memory:') as db:
            db.execute('CREATE TABLE events(patient_id TEXT,payload TEXT,available_at TEXT,phase INTEGER,id TEXT)')
            db.execute('INSERT INTO events VALUES(?,?,?,?,?)',(PATIENT,canonical(record),record['available_at'],0,record['record_id']))
            parsed=stored_history(db,PATIENT)
            self.assertEqual(parsed.schema_version,'2.1.0')
            with tempfile.TemporaryDirectory() as directory:
                source=Path(directory)/'source.json';destination=Path(directory)/'observed.json'
                source.write_text(canonical(parsed.model_dump(mode='json')))
                admit(source,destination)
                self.assertEqual(json.loads(destination.read_bytes())['schema_version'],'2.1.0')
            bad=copy.deepcopy(record);bad['schema_version']='2.2.0'
            db.execute('UPDATE events SET payload=?',(canonical(bad),))
            with self.assertRaises(ValueError):stored_history(db,PATIENT)
        old=copy.deepcopy(record);old['schema_version']='2.0.0';old.pop('policy_constraint')
        new=copy.deepcopy(record);new.update(record_id='support-v21-correction',supersedes=old['record_id'],revision=2,record_status='corrected',
            recorded_at=(ORIGIN+timedelta(days=1,seconds=1)).isoformat(),available_at=(ORIGIN+timedelta(days=1,seconds=1)).isoformat())
        with self.assertRaisesRegex(ValueError,'cross-version'):history([old,new])

    def test_closed_purposes_real_prior_sentinel_and_no_execution(self):
        self.assertEqual(EXECUTABLE_CONFIGURATIONS,frozenset())
        self.assertEqual(WCLS_PRIOR_REF['sha256'],'2efff2396d02f530b39b72750f8b229df3ae265926b42b90e2a4fc06ef134143')
        self.assertEqual(BOUNDARY_CONFIG_REF['sha256'],'cf73292c14620e979ba1dc24182a838537e88bf115a18e2b8aab4f3be5c78024')
        for purpose in IDENTITIES:
            value=product(purpose);raw=canonical(value.model_dump(mode='json'))
            self.assertEqual(parse_input(raw),value)
            for guard in [require_executable,lambda v:require_dispatchable(v.model_dump(mode='json'))]:
                with self.assertRaisesRegex(ValueError,'not executable'):guard(value)
            wrong=value.model_dump(mode='json');wrong['request']['backend']='statsmodels' if purpose!='S1-WCLS' else 'pymc'
            with self.assertRaises(ValueError):ProtocolInput.model_validate_json(canonical(wrong))
            wrong=value.model_dump(mode='json');wrong['request']['context']['prior']=N_PRIOR_REF if purpose=='S1-WCLS' else WCLS_PRIOR_REF
            with self.assertRaises(ValueError):ProtocolInput.model_validate_json(canonical(wrong))
            wrong=value.model_dump(mode='json');wrong['request']['context']['seed']['namespace']='assignment'
            with self.assertRaises(ValueError):ProtocolInput.model_validate_json(canonical(wrong))
            wrong=value.model_dump(mode='json');wrong['request']['configuration']['sha256']='f'*64
            with self.assertRaises(ValueError):ProtocolInput.model_validate_json(canonical(wrong))
        self.assertEqual(product('N0').history_sha256,product('N1').history_sha256)

    def test_nonexecutable_result_cannot_fabricate_fit_or_reuse_isi(self):
        for purpose in IDENTITIES:
            value=product(purpose);context=value.request.context
            result=dict(schema_version='2.0.0',synthetic=True,kind='poc_protocol_result',purpose=purpose,
                attempt_id=value.attempt_id,input_sha256=sha(value.model_dump(mode='json')),history_sha256=value.history_sha256,
                cohort=[m.model_dump() for m in value.cohort],cutoff=value.cutoff.isoformat(),run=value.run.model_dump(),protocol=context.protocol.model_dump(),
                configuration=BOUNDARY_CONFIG_REF,model=context.model.model_dump(),prior=context.prior.model_dump(),estimand=context.estimand.model_dump(),
                status='failed',reason='P1 schema fixture is not executable',consumed_record_ids=[],diagnostics={},artifacts=[],output=None)
            parsed=parse_result(canonical(result))
            with self.assertRaisesRegex(ValueError,'not executable'):require_executable(parsed)
            for update in [dict(status='completed',reason=None),dict(output={'kind':'wcls_excursion_inference','unit':'ISI_points','coefficient':0.})]:
                with self.assertRaises(ValueError):ProtocolResult.model_validate_json(canonical(result|update))


if __name__=='__main__':unittest.main()
